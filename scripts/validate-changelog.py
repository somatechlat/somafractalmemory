#!/usr/bin/env python3
"""
Changelog Validation Script

This script validates that the changelog is properly formatted and version numbers
match git tags. It ensures proper documentation of all changes.
"""

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

CHANGELOG_PATH = Path(__file__).parent.parent / "docs" / "changelog.md"


def get_latest_git_tag():
    """Get the most recent git tag."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"], capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def validate_changelog():
    """Validate changelog format and version."""
    if not CHANGELOG_PATH.exists():
        print("Error: changelog.md not found")
        return False

    with open(CHANGELOG_PATH) as f:
        content = f.read()

    # Check for version header format
    version_pattern = r"## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})"
    matches = re.findall(version_pattern, content)

    if not matches:
        print("Error: No properly formatted version headers found")
        return False

    latest_version, latest_date = matches[0]

    # Validate version matches git tag
    git_tag = get_latest_git_tag()
    if git_tag and git_tag.lstrip("v") != latest_version:
        print(f"Error: Latest changelog version {latest_version} doesn't match git tag {git_tag}")
        return False

    # Validate date format and recency
    try:
        changelog_date = datetime.strptime(latest_date, "%Y-%m-%d")
        age = datetime.now() - changelog_date
        if age.days > 90:
            print(f"Warning: Latest changelog entry is {age.days} days old")
    except ValueError:
        print(f"Error: Invalid date format in changelog: {latest_date}")
        return False

    # Check for required sections
    required_sections = ["Added", "Changed", "Deprecated", "Removed", "Fixed"]
    missing_sections = []

    for section in required_sections:
        if f"### {section}" not in content:
            missing_sections.append(section)

    if missing_sections:
        print("Warning: Missing changelog sections:", ", ".join(missing_sections))

    return True


def main():
    """Main validation function."""
    print("Validating changelog...")
    if validate_changelog():
        print("Changelog validation passed!")
        return 0
    else:
        print("Changelog validation failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
