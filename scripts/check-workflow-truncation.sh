#!/bin/bash
# Pre-commit hook to prevent accidental truncation of critical workflow files
# Detects if .github/workflows/ci.yml is being committed with suspiciously fewer lines

for file in "$@"; do
    # Check if file has staged changes
    if ! git diff --cached --quiet "$file" 2>/dev/null; then
        # Get number of lines in HEAD version
        head_lines=$(git show HEAD:"$file" 2>/dev/null | wc -l)

        # Count lines in the staged version (full diff output lines)
        staged_lines=$(git diff --cached "$file" 2>/dev/null | wc -l)

        # Get the number of actual content lines being added (lines starting with '+' that aren't the diff marker)
        staged_additions=$(git diff --cached "$file" 2>/dev/null | grep "^+[^+]" | wc -l)

        # If HEAD version has substantial content and we're removing most of it, flag as truncation
        if [[ -n "$head_lines" && "$head_lines" -gt 20 ]]; then
            # If staged additions are significantly fewer than HEAD, likely a truncation
            if [[ "$staged_additions" -lt $((head_lines / 3)) ]]; then
                echo "ERROR: $file appears to be truncated!" >&2
                echo "  Current HEAD lines: $head_lines" >&2
                echo "  Staged additions: $staged_additions lines" >&2
                echo "  This file has been accidentally overwritten before." >&2
                echo "  Use: git commit --no-verify (if intentional)" >&2
                exit 1
            fi
        fi
    fi
done

exit 0
