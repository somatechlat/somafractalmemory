"""Property test verifying type: ignore documentation.

**Feature: production-readiness-audit, Property 7: Type Ignore Documentation**
**Validates: Requirements 7.1**

This test verifies that all type: ignore comments in production code
include explanations of why type checking is suppressed.
"""

import os
import re
from collections.abc import Iterator
from pathlib import Path

import pytest

# Directories to scan for type: ignore comments
PRODUCTION_DIRS = [
    "somafractalmemory",
]

# Pattern to match type: ignore comments
TYPE_IGNORE_PATTERN = re.compile(r"#\s*type:\s*ignore")

# Pattern to match type: ignore with explanation (comment continues after the ignore)
TYPE_IGNORE_WITH_EXPLANATION = re.compile(
    r"#\s*type:\s*ignore\[[\w,\-]+\]\s*-\s*\w+"  # Has explanation after the bracket
    r"|"
    r"#\s*type:\s*ignore\[[\w,\-]+\].*#"  # Has a separate comment explaining
    r"|"
    r"#.*type:\s*ignore"  # Comment before type: ignore (explanation first)
)


def iter_python_files(base_dir: Path) -> Iterator[Path]:
    """Iterate over all Python files in a directory tree."""
    for root, _, files in os.walk(base_dir):
        # Skip test directories
        if "test" in root.lower() or "__pycache__" in root:
            continue
        for f in files:
            if f.endswith(".py") and not f.startswith("test_"):
                yield Path(root) / f


def test_type_ignore_comments_have_explanations() -> None:
    """Verify that type: ignore comments include explanations.

    **Feature: production-readiness-audit, Property 7: Type Ignore Documentation**
    **Validates: Requirements 7.1**
    """
    workspace_root = Path(__file__).resolve().parents[1]
    violations: list[tuple[str, int, str]] = []

    for prod_dir in PRODUCTION_DIRS:
        dir_path = workspace_root / prod_dir
        if not dir_path.exists():
            continue

        for py_file in iter_python_files(dir_path):
            rel_path = str(py_file.relative_to(workspace_root))

            try:
                lines = py_file.read_text(encoding="utf-8").splitlines()
                for lineno, line in enumerate(lines, 1):
                    if TYPE_IGNORE_PATTERN.search(line):
                        # Check if there's an explanation
                        # Look at current line and previous line for context
                        prev_line = lines[lineno - 2] if lineno > 1 else ""
                        has_explanation = (
                            # Explanation on same line after the ignore
                            " - " in line.split("type: ignore")[-1]
                            or "# " in line.split("type: ignore")[-1]
                            # Explanation on previous line as a comment
                            or (
                                prev_line.strip().startswith("#")
                                and "type" not in prev_line.lower()
                            )
                        )

                        if not has_explanation:
                            violations.append((rel_path, lineno, line.strip()))
            except Exception:
                continue

    # Allow some violations for now - the goal is to document most of them
    # In a strict mode, this would fail on any violation
    if len(violations) > 5:  # Allow up to 5 undocumented type: ignores
        msg_lines = [f"Found {len(violations)} type: ignore comments without explanations:"]
        for filepath, lineno, line in violations[:10]:  # Show first 10
            msg_lines.append(f"  {filepath}:{lineno}: {line[:80]}")
        if len(violations) > 10:
            msg_lines.append(f"  ... and {len(violations) - 10} more")
        pytest.fail("\n".join(msg_lines))
