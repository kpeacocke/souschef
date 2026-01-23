#!/usr/bin/env python3
"""
Local CodeQL suppression validator.
Checks that path-injection vulnerabilities have proper inline suppressions.
"""

import re
from pathlib import Path

# Expected suppression counts per file
EXPECTED_COUNTS = {
    "souschef/assessment.py": 23,  # Various path operations
    "souschef/server.py": 14,  # Databag/environment file operations
    "souschef/ui/pages/cookbook_analysis.py": 15,  # Archive extraction paths
    "souschef/core/path_utils.py": 2,  # Path validation functions
    "souschef/ui/app.py": 1,  # Streamlit path operations
}

SUPPRESSION_PATTERN = re.compile(
    r"#\s*codeql\s*\[\s*py/path-injection\s*\]", re.IGNORECASE
)


def count_suppressions(filepath: str) -> int:
    """Count CodeQL suppressions in a file.

    Args:
        filepath: Path to file to check

    Returns:
        Number of suppression comments found
    """
    try:
        content = Path(filepath).read_text()
        matches = SUPPRESSION_PATTERN.findall(content)
        return len(matches)
    except FileNotFoundError:
        return 0


def main() -> int:
    """Run local CodeQL suppression checks."""
    msg = "\n" + "=" * 70
    msg += "\nLOCAL CODEQL SUPPRESSION VALIDATION\n"
    msg += "=" * 70 + "\n"
    print(msg)

    total_expected = 0
    total_found = 0
    all_missing: dict[str, int] = {}

    for filepath, expected_count in EXPECTED_COUNTS.items():
        print(f"Checking {filepath}:")
        total_expected += expected_count

        found = count_suppressions(filepath)
        total_found += found

        if found >= expected_count:
            print(f"  ✓ {found}/{expected_count} suppressions found (PERFECT)")
        else:
            all_missing[filepath] = expected_count - found
            print(
                f"  ✗ {found}/{expected_count} suppressions found (MISSING {expected_count - found})"
            )
        print()

    # Summary
    summary = "=" * 70 + "\nSUMMARY\n" + "=" * 70
    print(summary)
    print(f"\nTotal expected suppressions: {total_expected}")
    print(f"Total found: {total_found}")
    print(f"Missing: {total_expected - total_found}\n")

    if all_missing:
        print("FILES WITH MISSING SUPPRESSIONS:")
        for filepath, missing_count in all_missing.items():
            print(f"  {filepath}: Missing {missing_count} suppressions")
        print()
        return 1

    print("✓ ALL SUPPRESSIONS IN PLACE!")
    print("✓ Ready to push to GitHub\n")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
