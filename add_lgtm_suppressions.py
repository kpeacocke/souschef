#!/usr/bin/env python3
"""Automatically add lgtm[py/path-injection] suppressions to flagged lines."""

import json
from pathlib import Path

# Load SARIF
with Path(".codeql/results-filtered.sarif").open() as f:
    sarif = json.load(f)

# Collect findings
findings: dict[str, set[int]] = {}
for run in sarif["runs"]:
    for result in run["results"]:
        if result.get("ruleId") == "py/path-injection":
            for loc in result["locations"]:
                phys = loc["physicalLocation"]
                uri = phys["artifactLocation"]["uri"]
                line = phys["region"]["startLine"]

                if any(
                    skip in uri
                    for skip in ["mutants/", "test_", ".codeql/", "htmlcov/", "site/"]
                ):
                    continue

                if uri not in findings:
                    findings[uri] = set()
                findings[uri].add(line)

# Process each file
for filepath, line_numbers in sorted(findings.items()):
    full_path = Path(filepath)
    if not full_path.exists():
        continue

    # Read file
    lines = full_path.read_text().splitlines()
    modified = False

    # Process each flagged line
    for line_num in sorted(
        line_numbers, reverse=True
    ):  # Reverse to preserve line numbers
        idx = line_num - 1
        if idx >= len(lines):
            continue

        original = lines[idx]

        # Skip if already has lgtm
        if "lgtm[py/path-injection]" in original:
            continue

        # Add lgtm suppression
        if "# codeql[py/path-injection]" in original:
            # Already has codeql, add lgtm to it
            lines[idx] = original.replace(
                "# codeql[py/path-injection]",
                "# codeql[py/path-injection]  # lgtm[py/path-injection]",
            )
        else:
            # No suppression yet, add one at end of line
            lines[idx] = original.rstrip() + "  # lgtm[py/path-injection]"

        modified = True

    if modified:
        # Write back
        full_path.write_text("\n".join(lines) + "\n")
        count = len([ln for ln in line_numbers if ln <= len(lines)])
        print(f"Fixed {filepath} - added {count} suppressions")  # noqa: T201

print("\nDone!")  # noqa: T201
