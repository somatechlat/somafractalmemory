#!/usr/bin/env python3
"""Repo pruning scanner

Produces a CSV/JSON inventory of files with hashes, sizes, reference counts,
duplicate groups, and a short markdown pruning plan.

Usage: python docs/tools/scan_prune.py
"""

import csv
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXCLUDE_DIRS = {".git", ".venv", "__pycache__", "node_modules", ".pytest_cache"}
OUT_CSV = ROOT / "docs" / "prune-inventory.csv"
OUT_JSON = ROOT / "docs" / "prune-inventory.json"
OUT_MD = ROOT / "docs" / "repo-pruning-plan.md"


def is_binary_string(bytesdata: bytes) -> bool:
    # heuristic: if NUL byte present or many non-text bytes
    if b"\x00" in bytesdata:
        return True
    # try decode
    try:
        bytesdata.decode("utf-8")
        return False
    except Exception:
        return True


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_files():
    files = []
    for dirpath, _dirnames, filenames in os.walk(ROOT):
        # skip excluded dirs
        rel = os.path.relpath(dirpath, ROOT)
        parts = rel.split(os.sep)
        if any(p in EXCLUDE_DIRS for p in parts):
            continue
        for fn in filenames:
            p = Path(dirpath) / fn
            relp = os.path.relpath(p, ROOT)
            files.append(relp)
    return sorted(files)


def read_text_safe(path: Path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None


def build_inventory(files):
    inv = []
    hash_map = {}
    for rel in files:
        p = ROOT / rel
        try:
            stat = p.stat()
        except Exception:
            continue
        size = stat.st_size
        sha = sha256_of_file(p)
        with p.open("rb") as f:
            head = f.read(2048)
        is_binary = is_binary_string(head)
        text = None
        if not is_binary:
            text = read_text_safe(p)
        inv.append(
            {
                "path": rel,
                "size": size,
                "sha256": sha,
                "is_binary": is_binary,
                "text": text,
            }
        )
        hash_map.setdefault(sha, []).append(rel)
    # compute duplicates
    for item in inv:
        item["duplicate_group"] = None
        group = hash_map.get(item["sha256"], [])
        if len(group) > 1:
            item["duplicate_group"] = group
    return inv


def reference_counts(inv):
    # build a simple search index: search each file's text for occurrences of basenames
    paths = [item["path"] for item in inv]
    name_to_paths = {}
    for p in paths:
        name = os.path.basename(p)
        name_to_paths.setdefault(name, []).append(p)

    # prepare text lookup
    text_lookup = {}
    for item in inv:
        if item["is_binary"]:
            text_lookup[item["path"]] = None
        else:
            text_lookup[item["path"]] = item["text"] or ""

    # count references by searching for path or basename in other files
    for item in inv:
        target = item["path"]
        base = os.path.basename(target)
        count = 0
        refs = []
        for other in inv:
            if other["path"] == target:
                continue
            t = text_lookup.get(other["path"])
            if not t:
                continue
            if target in t or base in t:
                count += 1
                refs.append(other["path"])
        item["ref_count"] = count
        item["referenced_by"] = refs
    return inv


def score_and_recommend(inv):
    for item in inv:
        score = 0
        # low reference -> higher deletion candidacy
        if item["ref_count"] == 0:
            score += 50
        elif item["ref_count"] < 3:
            score += 20
        # large files increase review priority
        if item["size"] > 1_000_000:
            score += 30
        # duplicates are candidates
        if item["duplicate_group"]:
            score += 20
        # binary files less likely to be auto-deleted
        if item["is_binary"]:
            score -= 10
        item["risk_score"] = int(score)
        # recommended action
        if item["risk_score"] >= 70:
            action = "DELETE_CANDIDATE"
        elif item["risk_score"] >= 40:
            action = "REVIEW"
        else:
            action = "KEEP"
        item["recommended_action"] = action
    return inv


def write_outputs(inv):
    # write CSV
    keys = [
        "path",
        "size",
        "sha256",
        "is_binary",
        "ref_count",
        "referenced_by",
        "duplicate_group",
        "risk_score",
        "recommended_action",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(keys)
        for it in inv:
            w.writerow(
                [
                    (
                        it.get(k)
                        if k not in ("referenced_by", "duplicate_group")
                        else (";".join(it.get(k)) if it.get(k) else "")
                    )
                    for k in keys
                ]
            )
    # write JSON
    simple = []
    for it in inv:
        si = {k: it.get(k) for k in keys}
        simple.append(si)
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(simple, f, indent=2)

    # write markdown summary
    top_candidates = sorted(inv, key=lambda x: (-x["risk_score"], -x["size"]))[:50]
    with OUT_MD.open("w", encoding="utf-8") as f:
        f.write("# Repo Pruning Plan\n\n")
        f.write("Generated inventory and recommendations. Review before any deletion.\n\n")
        f.write(f"Total files scanned: {len(inv)}\n\n")
        f.write("## Top candidates to review (top 50)\n\n")
        f.write("|path|size|risk_score|recommendation|ref_count|duplicates|\n")
        f.write("|---|---:|---:|---|---:|---|\n")
        for it in top_candidates:
            dup = ""
            if it["duplicate_group"]:
                dup = str(len(it["duplicate_group"]))
            f.write(
                f"|{it['path']}|{it['size']}|{it['risk_score']}|{it['recommended_action']}|{it['ref_count']}|{dup}|\n"
            )
        f.write("\n\n")
        f.write("## Notes\n")
        f.write(
            "- `DELETE_CANDIDATE` means low references and high risk score; still requires manual review.\n"
        )
        f.write("- `REVIEW` indicates files that should be manually checked before deletion.\n")
        f.write("- `KEEP` indicates low-risk files.\n")


def main():
    files = scan_files()
    print(f"Files found: {len(files)}")
    inv = build_inventory(files)
    inv = reference_counts(inv)
    inv = score_and_recommend(inv)
    write_outputs(inv)
    print("Wrote:", OUT_CSV, OUT_JSON, OUT_MD)


if __name__ == "__main__":
    main()
