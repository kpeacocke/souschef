#!/bin/bash
# Pre-commit hook to prevent accidental truncation of critical workflow files
# Detects if .github/workflows/ci.yml is being committed with suspiciously fewer lines

for file in "$@"; do
    # Get number of lines in HEAD version
    head_lines=$(git show HEAD:"$file" 2>/dev/null | wc -l)
    
    # Get number of addition lines in the staged change
    staged_lines=$(git diff --cached "$file" 2>/dev/null | grep "^+" | wc -l)
    
    # If HEAD version has substantial content and staged has less than 50% of it, flag as truncation
    if [[ -n "$head_lines" && "$head_lines" -gt 20 && "$staged_lines" -lt $((head_lines / 2)) ]]; then
        echo "ERROR: $file appears to be truncated!" >&2
        echo "  Staged additions: $staged_lines lines" >&2
        echo "  Expected: ~$head_lines lines" >&2
        echo "  This file has been accidentally overwritten before." >&2
        echo "  Use: git commit --no-verify (if intentional)" >&2
        exit 1
    fi
done

exit 0
