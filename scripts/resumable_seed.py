"""Resumable seeder for SomaFractalMemory

Features:
- Posts N memories to /memories with configurable concurrency
- Retries on network errors and 429 with exponential backoff
- Persists last successful index to a checkpoint file so it can resume after crashes
- Uses environment variable SOMA_API_TOKEN or a token file via SOMA_API_TOKEN_FILE

Usage examples:
    # basic: seed 1000 entries starting from 1
    python scripts/resumable_seed.py --total 1000

    # resume from checkpoint automatically
    python scripts/resumable_seed.py --total 1000 --concurrency 20

    # require OPA enforcement
    python scripts/resumable_seed.py --total 1000 --require-opa

    # run backup/restore validation after seeding
    python scripts/resumable_seed.py --total 1000 --backup-validate scripts/backup_restore.py

    # run in background and survive terminal disconnect (nohup)
    nohup python scripts/resumable_seed.py --total 1000 --concurrency 20 > seed.log 2>&1 &

Note: ensure the API token is securely provisioned to the script (prefer Kubernetes secrets, Vault, or a secure file; never hardcode or use default values).
"""

import argparse
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from prometheus_client import Counter, Histogram, start_http_server

SEED_REQUESTS = Counter("seed_requests_total", "Total seeder requests")
SEED_ERRORS = Counter("seed_errors_total", "Seeder errors")
SEED_OPA_DENIED = Counter("seed_opa_denied_total", "Seeder OPA denied responses")
SEED_RETRIES = Counter("seed_retries_total", "Seeder retry attempts")
SEED_LATENCY = Histogram("seed_request_latency_seconds", "Seeder request latency in seconds")


def load_token():
    # Support a token file path or env var
    token_file = os.getenv("SOMA_API_TOKEN_FILE")
    if token_file and Path(token_file).exists():
        token = Path(token_file).read_text(encoding="utf-8").strip()
        source = f"file: {token_file}"
    else:
        token = os.getenv("SOMA_API_TOKEN")
        source = "env: SOMA_API_TOKEN"
    if not token:
        raise RuntimeError("SOMA_API_TOKEN or SOMA_API_TOKEN_FILE must be set in the environment")
    # Check for insecure/default tokens
    if token in {"devtoken", "changeme-in-production", "soma", "default", ""}:
        print(
            f"ERROR: Insecure or default token loaded from {source}. Refusing to run.\n"
            "Provision a secure token using Kubernetes secrets, Vault, or a secure file."
        )
        sys.exit(2)
    return token


def atomic_write(path: Path, data: str):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(data, encoding="utf-8")
    tmp.replace(path)


class Seeder:
    def __init__(self, base, token, total, start, concurrency, checkpoint_file, timeout):
        self.base = base.rstrip("/")
        self.token = token
        self.total = total
        self.start = start
        self.concurrency = concurrency
        self.checkpoint_file = Path(checkpoint_file)
        self.timeout = timeout
        self.session = requests.Session()
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        # Optionally enable OPA debug header for troubleshooting
        if os.getenv("OPA_DEBUG") == "1":
            self.headers["X-OPA-Debug"] = "true"
        self.lock = threading.Lock()
        self._load_checkpoint()
        self.successes = 0

    def _load_checkpoint(self):
        if self.checkpoint_file.exists():
            try:
                data = json.loads(self.checkpoint_file.read_text(encoding="utf-8"))
                self.last_done = int(data.get("last_done", 0))
            except Exception:
                self.last_done = 0
        else:
            self.last_done = 0
        # Ensure we don't go backward
        if self.last_done >= self.start:
            self.next_idx = self.last_done + 1
        else:
            self.next_idx = self.start

    def _save_checkpoint(self, idx):
        data = {"last_done": idx, "timestamp": time.time()}
        try:
            atomic_write(self.checkpoint_file, json.dumps(data))
        except Exception as e:
            print("Warning: failed to write checkpoint:", e)

    def _store_one(self, i):
        url = f"{self.base}/memories"
        payload = {"coord": f"{i}.0,0.0", "memory_type": "episodic", "payload": {"i": i}}
        backoff = 0.5
        for attempt in range(1, 8):
            start = time.time()
            try:
                r = self.session.post(url, json=payload, headers=self.headers, timeout=self.timeout)
                SEED_REQUESTS.inc()
                SEED_LATENCY.observe(max(time.time() - start, 0.0))
                if r.status_code == 429:
                    wait = backoff * (2 ** (attempt - 1))
                    SEED_RETRIES.inc()
                    print(f"[{i}] 429 received, backing off {wait:.1f}s (attempt {attempt})")
                    time.sleep(wait)
                    continue
                if r.status_code == 403:
                    SEED_OPA_DENIED.inc()
                    print(f"[{i}] OPA DENIED (403): {r.text}")
                    return False, f"opa_denied:{r.text}"
                if 200 <= r.status_code < 300:
                    return True, r.text
                else:
                    SEED_ERRORS.inc()
                    print(f"[{i}] HTTP {r.status_code}: {r.text}")
                    if r.status_code >= 500:
                        SEED_RETRIES.inc()
                        time.sleep(backoff)
                        continue
                    return False, r.text
            except requests.RequestException as ex:
                SEED_ERRORS.inc()
                SEED_RETRIES.inc()
                wait = backoff * (2 ** (attempt - 1))
                print(f"[{i}] Request exception: {ex}. retrying in {wait:.1f}s (attempt {attempt})")
                time.sleep(wait)
        SEED_ERRORS.inc()
        return False, "max_retries_exceeded"

    def run(self):
        end_idx = self.total
        print(
            f"Seeding from {self.next_idx} to {end_idx} (total {self.total}), concurrency={self.concurrency}"
        )
        if self.next_idx > end_idx:
            print("Nothing to do — checkpoint indicates work already completed")
            return

        # We'll submit in a sliding window to bound memory usage
        idx = self.next_idx
        in_flight = {}
        with ThreadPoolExecutor(max_workers=self.concurrency) as ex:
            try:
                while idx <= end_idx or in_flight:
                    # submit until we hit concurrency limit
                    while idx <= end_idx and len(in_flight) < self.concurrency:
                        fut = ex.submit(self._store_one, idx)
                        in_flight[fut] = idx
                        idx += 1
                    # wait for any future to complete
                    done, _ = as_completed(in_flight).__next__(), None
                    # as_completed().__next__() gives one completed future
                    fut = done
                    i = in_flight.pop(fut)
                    ok, info = fut.result()
                    if ok:
                        with self.lock:
                            self._save_checkpoint(i)
                            self.last_done = i
                            self.successes += 1
                        if self.successes % 50 == 0:
                            print(f"Progress: {self.successes} successful writes (last id {i})")
                    else:
                        if isinstance(info, str) and info.startswith("opa_denied:"):
                            print(f"[AUDIT] Memory {i} blocked by OPA policy: {info[11:]}")
                        else:
                            print(f"Failed to store {i}: {info}")
                        # If a single item fails repeatedly, we continue — operator may inspect.
                print(f"Done. {self.successes} writes completed.")
            except KeyboardInterrupt:
                print(
                    "Interrupted by user — exiting. Checkpoint saved up to",
                    getattr(self, "last_done", 0),
                )


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--base", default=os.getenv("SOMA_API_BASE", "http://127.0.0.1:9595"), help="API base URL"
    )
    p.add_argument("--total", type=int, required=True, help="Total number of memories to write")
    p.add_argument("--start", type=int, default=1, help="Starting index (default 1)")
    p.add_argument("--concurrency", type=int, default=20, help="Number of concurrent workers")
    p.add_argument(
        "--checkpoint-file", default=".seed_checkpoint.json", help="Checkpoint file path"
    )
    p.add_argument("--timeout", type=float, default=10.0, help="HTTP timeout seconds per request")
    p.add_argument(
        "--require-opa",
        action="store_true",
        help="Fail if OPA is not enforced (any memory not blocked by OPA policy)",
    )
    p.add_argument(
        "--backup-validate",
        type=str,
        help="Path to backup/restore validation script to run after seeding",
    )
    args = p.parse_args()

    # Start Prometheus metrics server on port 8001
    start_http_server(8001)

    try:
        token = load_token()
    except Exception as e:
        print("Error loading token:", e)
        sys.exit(1)

    seeder = Seeder(
        base=args.base,
        token=token,
        total=args.total,
        start=args.start,
        concurrency=args.concurrency,
        checkpoint_file=args.checkpoint_file,
        timeout=args.timeout,
    )
    seeder.run()

    # OPA enforcement check
    if args.require_opa:
        if seeder.successes == 0:
            print("[OPA] No memories stored. OPA enforcement may be too strict or API is down.")
        elif seeder.successes > 0 and SEED_OPA_DENIED._value.get() == 0:
            print(
                "[OPA] WARNING: No OPA denied responses detected. OPA enforcement may not be active!"
            )
            sys.exit(3)
        else:
            print(
                f"[OPA] {SEED_OPA_DENIED._value.get()} OPA denied responses detected. Enforcement active."
            )

    # Backup/restore validation hook
    if args.backup_validate:
        print(f"[BACKUP] Running backup/restore validation: {args.backup_validate}")
        import subprocess

        result = subprocess.run(
            [sys.executable, args.backup_validate], capture_output=True, text=True
        )
        print("[BACKUP] Validation output:\n", result.stdout)
        if result.returncode != 0:
            print("[BACKUP] Validation failed!")
            sys.exit(result.returncode)
        else:
            print("[BACKUP] Validation succeeded.")


if __name__ == "__main__":
    main()
