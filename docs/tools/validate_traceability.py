#!/usr/bin/env python3
"""Simple traceability validator for docs front-matter.

Scans `docs/` for markdown files, extracts YAML-style front-matter blocks
(lines between '---' and '---') and attempts to locate an `iso_clauses` entry.

This is intentionally lightweight (no PyYAML) so it runs without extra deps.
It emits a small report and optionally writes `docs/traceability_report.csv`.
"""

import argparse
import csv
import os
import re
import sys


def extract_front_matter(path):
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read(8192)
    except Exception:
        return None
    if not text.startswith("---"):
        return None
    m = re.search(r"^---\s*$([\s\S]*?)^---\s*$", text, flags=re.M)
    if not m:
        return None
    return m.group(1)


def parse_iso_clauses(fm_text):
    if not fm_text:
        return []
    # inline list: iso_clauses: ["ISO-1", "ISO-2"]
    m = re.search(r"iso_clauses\s*:\s*(\[.*?\]|[^\n]+)", fm_text)
    if not m:
        # block list style:
        m2 = re.search(r"iso_clauses\s*:\s*\n((?:\s*-\s*.*\n)+)", fm_text)
        if m2:
            lines = re.findall(r"-\s*(.*)", m2.group(1))
            return [l.strip().strip("\"'") for l in lines if l.strip()]
        return []
    val = m.group(1).strip()
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1]
        parts = [p.strip().strip("\"'") for p in inner.split(",") if p.strip()]
        return parts
    return [val.strip().strip("\"'")]


def scan_docs(root):
    results = []
    for dirpath, _, filenames in os.walk(root):
        for fn in sorted(filenames):
            if not fn.endswith(".md"):
                continue
            path = os.path.join(dirpath, fn)
            fm = extract_front_matter(path)
            clauses = parse_iso_clauses(fm)
            results.append((path, clauses))
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--docs-root", default="docs", help="Docs root to scan")
    p.add_argument("--write-csv", action="store_true", help="Write CSV report under docs/")
    args = p.parse_args()

    if not os.path.isdir(args.docs_root):
        print(f"Docs root not found: {args.docs_root}")
        return 2

    results = scan_docs(args.docs_root)
    missing = [r for r in results if not r[1]]

    print(f"Checked {len(results)} markdown files under {args.docs_root}")
    print(f"{len(missing)} files missing iso_clauses front-matter")
    print("")
    for path, clauses in results:
        rel = os.path.relpath(path, args.docs_root)
        if clauses:
            print(f"OK     {rel} -> {clauses}")
        else:
            print(f"MISSING {rel}")

    if args.write_csv:
        out = os.path.join(args.docs_root, "traceability_report.csv")
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["file", "iso_clauses"])
            for path, clauses in results:
                rel = os.path.relpath(path, args.docs_root)
                w.writerow([rel, ";".join(clauses)])
        print("")
        print("Wrote", out)

    return 0


if __name__ == "__main__":
    sys.exit(main())
