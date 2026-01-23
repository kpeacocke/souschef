# CodeQL Local Validation Tool

This directory contains development and validation tools for the SousChef project.

Companion docs:
- [LOCAL_CODEQL_GUIDE.md](LOCAL_CODEQL_GUIDE.md) — full guide to running CodeQL locally
- [CODEQL_QUICK_REFERENCE.md](CODEQL_QUICK_REFERENCE.md) — quick reference card

## check_codeql_suppressions.py

A local validation tool that verifies CodeQL path-injection security suppressions are in place before pushing code to GitHub.

### What It Does

CodeQL is GitHub's code analysis tool that detects potential security vulnerabilities, including "path-injection" attacks where user input could be used unsafely in file path operations.

This tool validates that:
- All path operations that could be flagged by CodeQL have proper inline suppressions
- The suppression format is correct: `# codeql [py/path-injection]` (with space)
- All files with path operations are checked

### Running the Tool

```bash
python3 tools/check_codeql_suppressions.py
```

### Output Examples

**Success (all suppressions in place):**
```
======================================================================
LOCAL CODEQL SUPPRESSION VALIDATION
======================================================================

Checking souschef/assessment.py:
  ✓ 49/23 suppressions found (PERFECT)
...
✓ ALL SUPPRESSIONS IN PLACE!
✓ Ready to push to GitHub
```

**Failure (missing suppressions):**
```
Checking souschef/assessment.py:
  ✗ 22/30 suppressions found (MISSING 8)
...
FILES WITH MISSING SUPPRESSIONS:
  souschef/assessment.py: Missing 8 suppressions
```

### Why This Matters

CodeQL runs on every push to GitHub and will block PRs if security warnings are not properly addressed. This tool lets you catch and fix issues **locally before pushing**, saving time and preventing CI failures.

### Understanding CodeQL Suppressions

CodeQL suppressions must:
1. Use the exact format: `# codeql [py/path-injection]` (note the space between "codeql" and "[")
2. Be on the **same line** as the path operation that triggered the warning
3. Only suppress issues that are actually safe (e.g., paths normalized via `_normalize_path()` or `_safe_join()`)

**Example:**
```python
# Safe: cookbook_path is normalized by caller via _normalize_path()
recipe_path = cookbook_path / "recipes" / recipe_name  # codeql [py/path-injection]
```

### Files Checked

- `souschef/assessment.py` - Cookbook assessment logic with path operations
- `souschef/server.py` - MCP server with databag and environment file operations
- `souschef/ui/pages/cookbook_analysis.py` - Streamlit UI with archive extraction
- `souschef/core/path_utils.py` - Path validation utilities
- `souschef/ui/app.py` - Main Streamlit application

### Integration with Development Workflow

Before committing path operation changes:

```bash
# 1. Make your changes
# 2. Run local validation
python3 tools/check_codeql_suppressions.py

# 3. If successful, commit and push
git commit -m "feat: add path operation"
git push origin main

# 4. Monitor GitHub Actions for CodeQL results
```

### Common Issues

**Issue:** "Missing suppressions" reported
**Solution:** Check that the suppression comment is on the exact line with the path operation, not on a separate comment line.

**Issue:** CodeQL still complains on GitHub
**Solution:** Ensure the suppression format is exactly `# codeql [py/path-injection]` with the space. Also verify the path operation is actually safe (normalized before use).

### Troubleshooting

To see which files have suppressions:
```bash
grep -r "codeql \[py/path-injection\]" souschef/
```

To count total suppressions:
```bash
grep -r "codeql \[py/path-injection\]" souschef/ | wc -l
```

To check a specific file:
```bash
grep "codeql \[py/path-injection\]" souschef/assessment.py | wc -l
```

### For More Information

- [CodeQL Documentation](https://codeql.github.com/)
- [SousChef Security Guidelines](../SECURITY.md)
- [SousChef Architecture](../docs/ARCHITECTURE.md)
