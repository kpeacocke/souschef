# Technical Debt Tracking

SousChef uses **GitHub Issues** to track technical debt, not this document.

## 🎯 How We Track Technical Debt

All technical debt is tracked as GitHub Issues with the `technical-debt` label.

### View Current Technical Debt

```bash
# List all technical debt issues
gh issue list --label technical-debt

# View by priority
gh issue list --label technical-debt,priority:high
gh issue list --label technical-debt,priority:medium
gh issue list --label technical-debt,priority:low

# View in browser
gh issue list --label technical-debt --web
```

**Or visit**: https://github.com/kpeacocke/souschef/labels/technical-debt

## 📝 Creating Technical Debt Issues

### Option 1: Use the Issue Template

1. Go to: https://github.com/kpeacocke/souschef/issues/new/choose
2. Select "Technical Debt" template
3. Fill in the form fields
4. Submit

### Option 2: Command Line

```bash
gh issue create \
  --title "[Tech Debt] Your title here" \
  --label "technical-debt,priority:medium" \
  --body "Description of the technical debt" \
  --milestone "v2.0.0"
```

## 🚀 Migrating Existing Technical Debt

Run this script to create issues for all known complexity violations:

```bash
.g# Test Data Line Length (E501)

**Not tracked as technical debt** - This is intentional:
- Test files contain Chef cookbook code as literal strings
- Chef code must remain intact for accurate testing
- Only applies to test data, not actual Python code
- Configured in `pyproject.toml` with clear comments

## ✅ Suppressions Policy

### Acceptable Suppressions

- `# noqa: C901` - Complex domain logic (tracked in issues)
- Per-file: `S101` - Pytest assertions are OK in tests
- Per-file: `T201` - Print statements OK in main entry points
- Per-file: `E501` - Test data line length (Chef cookbook strings)

### Not Acceptable

❌ Suppressing actual bugs
❌ Blanket suppressions without documentation
❌ Hiding code smells instead of fixing
❌ Security warnings

**All suppressions require**:
1. GitHub issue tracking the debt (if fixable)
2. Clear justification in code comments
3. Review during PR approval
4. Target milestone for resolution (if applicable)

## 🎯 How to Contribute

### Fixing Technical Debt

1. Find issue: `gh issue list --label technical-debt`
2. Assign yourself: `gh issue edit <number> --add-assignee @me`
3. Create branch: `git checkout -b fix/issue-<number>`
4. Fix, test, commit
5. Reference issue in PR: `Fixes #<number>`

### Reviewing PRs with Suppressions

If PR adds new `# noqa` comments:
- ✅ Check if GitHub issue exists
- ✅ Verify justification is valid
- ✅ Confirm target milestone is set
- ✅ Ensure tests exist
- ❌ Reject if just hiding problems

## 📈 Progress Tracking

Track technical debt resolution in projects:

```bash
# Create project board
gh project create --title "Technical Debt" --owner kpeacocke

# Add tech debt issues to project
gh project item-add <project-id> --owner kpeacocke --url <issue-url>
```

## 🔄 Quarterly Review

Technical debt is reviewed every quarter:
- Triage new issues
- Update priorities
- Close resolved issues
- Adjust milestones
- Update metrics

**Next Review**: April 2, 2026

---

For questions about technical debt, open a discussion or comment on specific issues
- Suppressing instead of fixing correctable issues

All suppressions must be:
1. ✅ Documented in this file or inline comments
2. ✅ Justified with clear reasoning
3. ✅ Tracked for eventual resolution
4. ✅ Reviewed during code review

## Future Improvements

### Code Quality
- [ ] Refactor complex functions to reduce C901 violations
- [ ] Improve error messages with specific Chef construct names
- [ ] Add more descriptive variable names in complex functions

### Testing
- [ ] Increase coverage from 82% to 95%+
- [ ] Add more integration tests with real-world cookbooks
- [ ] Performance benchmarks for large cookbook parsing

### Documentation
- [ ] API documentation with examples
- [ ] Chef-to-Ansible mapping reference guide
- [ ] Migration pattern cookbook

---

**Last Updated**: January 2, 2026

This document is reviewed quarterly and updated as technical debt is addressed.
