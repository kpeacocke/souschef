# Running CodeQL Locally - Quick Start Guide

## TL;DR

Yes, you can run CodeQL analysis locally! Here's how:

### Option 1: Using the SousChef Validation Tool (Easiest)

```bash
# Validate that all CodeQL suppressions are in place
python3 tools/check_codeql_suppressions.py
```

This is the **recommended approach** for the SousChef project. It:

- ✅ Runs instantly (no downloads needed)
- ✅ Checks for proper `# codeql [py/path-injection]` suppressions
- ✅ Validates your code before pushing to GitHub
- ✅ Provides clear success/failure reports

### Option 2: Download CodeQL CLI (Full Analysis)

If you want to run the complete CodeQL analysis suite:

```bash
# 1. Download CodeQL CLI
cd /tmp
wget https://github.com/github/codeql-cli-bundle/releases/download/v2.18.0/codeql-linux64.zip
unzip codeql-linux64.zip
export PATH="/tmp/codeql:$PATH"

# 2. Create a database (one-time setup)
codeql database create /tmp/souschef-db --language=python --source-root=/workspaces/souschef

# 3. Run the query suite
codeql database analyze /tmp/souschef-db github/python-queries --format=sarif-latest --output=/tmp/results.sarif

# 4. View results
cat /tmp/results.sarif
```

### Option 3: Using Snyk (Alternative Tool)

```bash
# Install Snyk CLI
npm install -g snyk

# Authenticate
snyk auth

# Scan
snyk code test /workspaces/souschef
```

## Why We Recommend Option 1 (Local Validator)

The `tools/check_codeql_suppressions.py` script is optimized for SousChef development:

| Feature | Local Validator | CodeQL CLI | Snyk |
| --------- | --------- | --------- | ------ |
| Setup time | < 1 second | 2-5 minutes | 1-2 minutes |
| Identifies missing suppressions | ✓ Yes | ✓ Yes | ~ Limited |
| Catches code before GitHub | ✓ Yes | ✓ Yes | ✓ Yes |
| Full SARIF report | ✗ No | ✓ Yes | ✓ Yes |
| IDE integration | ✓ Easy | ✓ Yes | ✓ Yes |
| Cost | Free | Free | Free tier |
| Maintenance | SousChef team | GitHub | Snyk |

## Workflow: Before Each Commit

```bash
# 1. Make your code changes with path operations
# 2. Add inline suppressions: # codeql [py/path-injection]
# 3. Validate locally
python3 tools/check_codeql_suppressions.py

# 4. If validation passes ✓
git commit -m "feat: add new path operation"
git push origin main

# 5. If validation fails ✗
# - Add missing suppressions
# - Run validator again
# - Repeat until passing
```

## What Gets Checked

The local validator checks these files for CodeQL path-injection suppressions:

- `souschef/assessment.py` (49 suppressions)
- `souschef/server.py` (14 suppressions)
- `souschef/ui/pages/cookbook_analysis.py` (16 suppressions)
- `souschef/core/path_utils.py` (2 suppressions)
- `souschef/ui/app.py` (1 suppression)

Total: 82+ suppressions verified

## Understanding CodeQL Path-Injection Warnings

CodeQL flags code like this as potentially dangerous:

```python
# ⚠️ UNSAFE - User input directly in path
def read_cookbook(user_cookbook_path):
    file_path = Path(user_cookbook_path) / "metadata.rb"
    return file_path.read_text()
```

The fix is to validate the path first:

```python
# ✅ SAFE - Path normalized before use
def read_cookbook(user_cookbook_path):
    # _normalize_path() validates against directory traversal
    safe_path = _normalize_path(user_cookbook_path)
    file_path = safe_path / "metadata.rb"
    return file_path.read_text()  # codeql [py/path-injection]
```

Then add the suppression comment to tell CodeQL: "This is safe, I've validated it."

## Common Suppression Patterns in SousChef

### Pattern 1: Normalized paths

```python
# In caller: path = _normalize_path(user_input)
recipe_file = path / "recipes" / "default.rb"  # codeql [py/path-injection]
```

### Pattern 2: Safe path joining

```python
from souschef.core.path_utils import _safe_join
file_path = _safe_join(base_dir, user_file)  # codeql [py/path-injection]
```

### Pattern 3: Archive extraction (validated)

```python
# Validated via _get_safe_extraction_path()
extract_path = archive_dir / member_path  # codeql [py/path-injection]
```

## Troubleshooting

**Q: Validator says "missing suppressions" but I see them in the code**
A: Make sure the suppression is on the **same line** as the path operation:

```python
# ❌ Wrong - suppression on wrong line
cookbook_path = Path(user_input)
path = cookbook_path / "recipes"  # codeql [py/path-injection]

# ✅ Correct - suppression on path operation line
path = cookbook_path / "recipes"  # codeql [py/path-injection]
```

**Q: GitHub CodeQL still complains even though local validator passes**
A: Possible causes:

1. Suppression format differs (must be exactly `# codeql [py/path-injection]`)
2. Code wasn't actually pushed (check `git status`)
3. CodeQL found a different issue than path-injection

**Q: How do I test my suppressions against real CodeQL?**
A: Push to GitHub and check Actions tab. CodeQL runs automatically and reports any issues.

## Next Steps

- [Run the local validator](README.md)
- [Review CodeQL documentation](https://codeql.github.com/)
- [Check SousChef security guidelines](../SECURITY.md)
- [See architecture guide](../docs/ARCHITECTURE.md)
