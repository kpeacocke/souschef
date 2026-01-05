# Pull Request Template

## 🌿 Gitflow Branch Check

**Source branch**: `[your branch name]`
**Target branch**: `[base branch]`

Please verify your branch follows gitflow conventions:
- ✅ `feature/*` → targets `develop`
- ✅ `bugfix/*` → targets `develop`
- ✅ `release/*` → targets `main`
- ✅ `hotfix/*` → targets `main`

_The gitflow workflow will automatically validate this._

---

## 📋 Summary

Brief description of what this PR does and why.

**Type of Change** (check all that apply):
- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📚 Documentation update
- [ ] 🧪 Test improvements
- [ ] 🔧 Refactoring (no functional changes)
- [ ] 📦 Dependencies update
- [ ] 🚀 Performance improvement

## 🎯 Related Issues

Closes #[issue number]
Relates to #[issue number]
Fixes #[issue number]

## 🔧 Changes Made

### Core Changes
- List the main changes made
- Include any new MCP tools added
- Note any CLI command changes
- Describe algorithm or logic improvements

### Files Modified
- `souschef/server.py` - [description of changes]
- `souschef/cli.py` - [description of changes]
- `tests/test_*.py` - [description of test changes]
- `README.md` - [description of documentation changes]

## 🧪 Testing

### Test Coverage
- [ ] Unit tests added/updated for new functionality
- [ ] Integration tests added/updated
- [ ] Property-based tests added if applicable
- [ ] All existing tests pass
- [ ] Code coverage maintained or improved

### Manual Testing
Describe how you tested this change:

```bash
# Commands run for testing
souschef-cli recipe examples/recipe.rb
```

**Test Results**:
```
# Paste relevant test output
Resource 1: package[nginx]
  Type: package
  Action: install
```

### Test Cases Covered
- [ ] Normal/happy path scenarios
- [ ] Edge cases and error conditions
- [ ] Cross-platform compatibility
- [ ] Performance with large inputs
- [ ] Integration with existing features

## 📊 Performance Impact

If applicable, describe performance implications:

- **Memory usage**: No significant change / Reduced / Increased by X%
- **Processing time**: Benchmarks show X% improvement/regression
- **Scalability**: Handles larger cookbooks / No impact

## 🔒 Security Considerations

For changes that might have security implications:

- [ ] Input validation added/improved
- [ ] No secrets or credentials exposed
- [ ] File path validation in place
- [ ] Error messages don't leak sensitive information
- [ ] Dependencies updated to secure versions

## 📖 Documentation

- [ ] README.md updated if needed
- [ ] CLI help text updated
- [ ] Code comments added for complex logic
- [ ] Docstrings added/updated following Google style
- [ ] Examples added or updated

## 🧹 Code Quality

### Checklist (verify before submitting)
- [ ] ✅ Code passes linting (`poetry run ruff check .`)
- [ ] ✅ Code is properly formatted (`poetry run ruff format .`)
- [ ] ✅ All tests pass (`poetry run pytest`)
- [ ] ✅ Type hints are complete and accurate
- [ ] ✅ Docstrings follow Google style format
- [ ] ✅ No warnings introduced (zero warnings policy)
- [ ] ✅ Code follows existing patterns and style
- [ ] ✅ Error handling is comprehensive

### Code Review Areas
Please pay special attention to:
- [ ] Resource-to-task conversion logic
- [ ] ERB-to-Jinja2 template conversion
- [ ] File path handling and security
- [ ] Error messages and user experience
- [ ] Test coverage and edge cases

## 🎨 UI/UX Changes

For CLI or output changes:

**Before**:
```
# Old CLI output or behavior
```

**After**:
```
# New CLI output or behavior
```

## ⚠️ Breaking Changes

If this PR introduces breaking changes, describe:

1. **What breaks**: Specific functionality that changes
2. **Migration path**: How users should adapt
3. **Deprecation period**: Timeline for removing old functionality
4. **Documentation**: Where migration info is documented

## 🚀 Deployment Notes

Any special considerations for deployment:

- [ ] Database migrations required
- [ ] Configuration changes needed
- [ ] Environment variable updates
- [ ] Dependencies updated
- [ ] Version bump required

## 📝 Additional Context

Add any additional context, screenshots, or information that reviewers should know:

- Links to related discussions or documentation
- Design decisions and trade-offs made
- Alternative approaches considered
- Future work this enables

## 🔄 Reviewer Guidance

**Focus Areas for Review**:
- Code correctness and edge case handling
- Test coverage and quality
- Documentation accuracy
- Performance implications
- Security considerations

**Questions for Reviewers**:
- Is the Chef-to-Ansible mapping accurate?
- Are there edge cases I missed?
- Is the error handling appropriate?
- Should this be split into smaller PRs?

---

## 📋 Pre-Submit Checklist

Before submitting this PR, I have verified:

- [ ] 🧪 All tests pass locally (`poetry run pytest`)
- [ ] 🎨 Code is linted and formatted (`poetry run ruff check . && poetry run ruff format .`)
- [ ] 📊 Test coverage is maintained or improved
- [ ] 📖 Documentation is updated where needed
- [ ] 🔍 I have self-reviewed my code changes
- [ ] 💭 Complex logic has explanatory comments
- [ ] 🚨 No debug code or console.log statements left
- [ ] 🔧 Commit messages follow conventional format

**By submitting this PR, I confirm that**:
- [ ] My contribution is made under the project's MIT license
- [ ] I have followed the project's coding standards and guidelines
- [ ] I have read and agree to the [Code of Conduct](../CODE_OF_CONDUCT.md)

---

**Thank you for contributing to SousChef!** 🙏

Your improvements help make Chef-to-Ansible migrations easier for everyone.
