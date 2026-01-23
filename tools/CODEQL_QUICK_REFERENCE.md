# CodeQL Local Validation - Quick Reference

## One-Liner

```bash
python3 tools/check_codeql_suppressions.py
```

## Result Interpretation

| Result | Meaning | Action |
|--------|---------|--------|
| ✓ ALL SUPPRESSIONS IN PLACE | Code is safe to push | `git commit && git push` |
| ✗ Missing suppressions | CodeQL will reject PR | Add `# codeql [py/path-injection]` comments and retry |

## Suppression Syntax

```python
# CORRECT - suppression on the path operation line
path = cookbook_dir / "recipes" / recipe_name  # codeql [py/path-injection]

# WRONG - suppression on a separate line
# codeql[py/path-injection]  # <- This doesn't work
path = cookbook_dir / "recipes" / recipe_name
```

## Before You Push

1. Make changes with path operations
2. Add suppressions: `# codeql [py/path-injection]`
3. Run: `python3 tools/check_codeql_suppressions.py`
4. See ✓? Push it! See ✗? Fix it!

## Safe Path Patterns in SousChef

```python
# Pattern 1: Path normalized by caller
path = normalized_cookbook_path / "recipes"  # codeql [py/path-injection]

# Pattern 2: Safe path join utility
from souschef.core.path_utils import _safe_join
file = _safe_join(base_dir, user_input)  # codeql [py/path-injection]

# Pattern 3: Archive extraction with validation
extracted = safe_archive_dir / member  # codeql [py/path-injection]
```

## More Information

- **Detailed Guide:** [LOCAL_CODEQL_GUIDE.md](LOCAL_CODEQL_GUIDE.md)
- **Tool Documentation:** [README.md](README.md)
- **Security Policy:** [../SECURITY.md](../SECURITY.md)

---

**That's it!** Run the tool before pushing code with path operations and you're golden.
