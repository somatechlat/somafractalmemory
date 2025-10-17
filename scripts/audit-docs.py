#!/usr/bin/env python3
"""
Documentation Health Audit Script

This script performs automated checks on the documentation:
- Validates all internal links
- Flags sections not updated in > 90 days
- Generates a Documentation Health Report
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml

DOCS_ROOT = Path(__file__).parent.parent / "docs"
MAX_AGE_DAYS = 90


def check_frontmatter(file_path: Path):
    """Validate YAML frontmatter at top of markdown file.

    Uses explicit '---\n' start and '\n---\n' end delimiters to avoid
    accidental splits on horizontal rules in the body.
    """
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    if not content.startswith("---\n"):
        return False, "Missing frontmatter"

    try:
        start = 4  # len('---\n')
        end = content.find("\n---\n", start)
        if end == -1:
            return False, "Invalid frontmatter: closing delimiter not found"
        fm_text = content[start:end]
        metadata = yaml.safe_load(fm_text) or {}
        if not isinstance(metadata, dict):
            return False, "Invalid frontmatter: not a mapping"

        # Required fields
        required = ["title", "purpose", "audience", "last_updated"]
        missing = [f for f in required if f not in metadata or not metadata[f]]
        if missing:
            return False, f"Missing required fields: {', '.join(missing)}"

        # Check last_updated
        last_updated = datetime.strptime(str(metadata["last_updated"]), "%Y-%m-%d")
        age = datetime.now() - last_updated
        if age.days > MAX_AGE_DAYS:
            return False, f"Content is {age.days} days old"

    except Exception as e:
        return False, f"Invalid frontmatter: {str(e)}"

    return True, "OK"


def check_internal_links(file_path: Path):
    """Validate internal documentation links.

    Resolve links relative to the file's own directory.
    Ignore external links (http/https/mailto) and pure anchors (#...).
    For links with anchors (file.md#section), validate only the file's existence.
    """
    with open(file_path) as f:
        content = f.read()

    links = re.findall(r"\[([^\]]+)\]\(([^\)]+)\)", content)
    issues = []

    for _text, link in links:
        if link.startswith("http") or link.startswith("#") or link.startswith("mailto:"):
            continue

        # Strip anchor/query
        link_path = link.split("#", 1)[0].split("?", 1)[0]
        target = (file_path.parent / link_path).resolve()

        try:
            target.relative_to(DOCS_ROOT.resolve())
        except Exception:
            issues.append(f"Broken link to {link}")
            continue

        if not target.exists():
            issues.append(f"Broken link to {link}")

    return len(issues) == 0, issues


def main():
    """Main audit function."""
    issues = []
    stats = {"total": 0, "passed": 0, "failed": 0}

    for md_file in DOCS_ROOT.rglob("*.md"):
        stats["total"] += 1
        file_issues = []

        # Check frontmatter
        fm_ok, fm_msg = check_frontmatter(md_file)
        if not fm_ok:
            file_issues.append(fm_msg)

        # Check links
        links_ok, link_issues = check_internal_links(md_file)
        if not links_ok:
            file_issues.extend(link_issues)

        if file_issues:
            stats["failed"] += 1
            issues.append({"file": str(md_file.relative_to(DOCS_ROOT)), "issues": file_issues})
        else:
            stats["passed"] += 1

    # Generate report
    report = {"timestamp": datetime.now().isoformat(), "stats": stats, "issues": issues}

    report_path = DOCS_ROOT / "doc-health-report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    # Print summary
    print("Documentation Health Report")
    print("-------------------------")
    print(f"Total files: {stats['total']}")
    print(f"Passed: {stats['passed']}")
    print(f"Failed: {stats['failed']}")
    print(f"\nDetailed report saved to: {report_path}")

    return 0 if stats["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
