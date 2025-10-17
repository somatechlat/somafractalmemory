#!/usr/bin/env python3
"""
Inject YAML frontmatter into docs/**/*.md using real content:
- title: first H1 (# ...)
- purpose: first paragraph after H1 (plain text, trimmed to one sentence)
- audience: inferred from path (user/technical/development/onboarding)
- last_updated: last git commit date for the file (YYYY-MM-DD)

No placeholders or invented text beyond selecting existing content.
"""

from __future__ import annotations

import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, cast  # noqa: F401 (compat for older editors)

import yaml

ROOT = Path(__file__).parent.parent
DOCS = ROOT / "docs"

AUD_MAP = {
    "user-manual": "End Users",
    "technical-manual": "Operators and SREs",
    "development-manual": "Developers and Contributors",
    "onboarding-manual": "New Team Members",
}


def get_last_updated(path: Path) -> str:
    try:
        out = (
            subprocess.check_output(["git", "log", "-1", "--format=%cs", str(path)], cwd=str(ROOT))
            .decode()
            .strip()
        )
        datetime.strptime(out, "%Y-%m-%d")
        return out
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")


def extract_title_and_purpose(text: str) -> tuple[str | None, str | None]:
    lines = text.splitlines()
    title = None
    # Find first H1
    for i, line in enumerate(lines):
        if line.startswith("# "):
            title = line[2:].strip()
            # Find first non-empty paragraph after H1
            para = []
            for j in range(i + 1, len(lines)):
                if lines[j].strip() == "":
                    if para:
                        break
                    else:
                        continue
                para.append(lines[j])
            purpose_text = " ".join(para).strip()
            # First sentence (rudimentary)
            purpose = re.split(r"(?<=[.!?])\s+", purpose_text)[0] if purpose_text else None
            return title or None, purpose or None
    return None, None


def infer_audience(path: Path) -> str:
    parts = path.relative_to(DOCS).parts
    for p in parts:
        if p in AUD_MAP:
            return AUD_MAP[p]
    return "All Stakeholders"


def split_frontmatter(text: str) -> tuple[dict | None, str]:
    """Return (meta_dict or None, body) from a markdown file."""
    if not text.startswith("---\n"):
        return None, text
    try:
        _, rest = text.split("---\n", 1)
        fm_text, body = rest.split("\n---\n", 1)
    except ValueError:
        # Malformed frontmatter; treat entire file as body to replace
        return None, text
    try:
        meta = yaml.safe_load(fm_text) or {}
        if not isinstance(meta, dict):
            meta = {}
    except Exception:
        meta = {}
    return meta, body


def build_frontmatter(title: str, purpose: str, audience: str, last_updated: str) -> str:
    meta = {
        "title": title,
        "purpose": purpose,
        "audience": [audience],
        "last_updated": last_updated,
    }
    dumped = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True)
    return f"---\n{dumped}---\n\n"


def main() -> int:
    updated = 0
    for md in DOCS.rglob("*.md"):
        text = md.read_text(encoding="utf-8")
        meta, body = split_frontmatter(text)
        if meta is None:
            # No or invalid frontmatter; rebuild
            title, purpose = extract_title_and_purpose(body)
            if not title:
                title = md.stem.replace("-", " ").title()
            if not purpose:
                purpose = title
            audience = infer_audience(md)
            last_updated = get_last_updated(md)
            fm = build_frontmatter(title, purpose, audience, last_updated)
            md.write_text(fm + body, encoding="utf-8")
            updated += 1
            print(f"Injected frontmatter: {md.relative_to(DOCS)}")
        else:
            # Validate and fix required fields if missing
            changed = False
            title_infer, purpose_infer = extract_title_and_purpose(body)
            if "title" not in meta or not meta["title"]:
                meta["title"] = title_infer or md.stem.replace("-", " ").title()
                changed = True
            if (
                "purpose" not in meta
                or not isinstance(meta["purpose"], str)
                or not meta["purpose"].strip()
            ):
                meta["purpose"] = (purpose_infer or meta["title"]).strip()
                changed = True
            if "audience" not in meta or not meta["audience"]:
                meta["audience"] = [infer_audience(md)]
                changed = True
            if "last_updated" not in meta or not meta["last_updated"]:
                meta["last_updated"] = get_last_updated(md)
                changed = True
            if changed:
                dumped = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True)
                md.write_text(f"---\n{dumped}---\n\n{body}", encoding="utf-8")
                updated += 1
                print(f"Fixed frontmatter: {md.relative_to(DOCS)}")
    print(f"Done. Updated {updated} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
