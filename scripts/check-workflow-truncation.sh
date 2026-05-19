#!/bin/bash
# Pre-commit hook to prevent accidental truncation of critical workflow files
# Detects if .github/workflows/ci.yml is being committed with suspiciously fewer lines

for file in "$@"; do
    # Check if file has staged changes
    if ! git diff --cached --quiet "$file" 2>/dev/null; then
        # Get number of lines in HEAD version
        head_lines=$(git show HEAD:"$file" 2>/dev/null | wc -l)

        # Get the total line count of the staged file content.
        staged_file_lines=$(git show :"$file" 2>/dev/null | wc -l)

        # If HEAD version has substantial content and we're removing most of it, flag as truncation
        if [[ -n "$head_lines" && "$head_lines" -gt 20 ]]; then
            # If staged file is significantly smaller than HEAD, likely a truncation.
            if [[ "$staged_file_lines" -lt $((head_lines / 3)) ]]; then
                echo "ERROR: $file appears to be truncated!" >&2
                echo "  Current HEAD lines: $head_lines" >&2
                echo "  Staged file lines: $staged_file_lines" >&2
                echo "  This file has been accidentally overwritten before." >&2
                echo "  Use: git commit --no-verify (if intentional)" >&2
                exit 1
            fi
        fi
    fi
done

exit 0
