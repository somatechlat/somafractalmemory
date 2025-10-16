---
title: "Pre-Commit Checklist"
purpose: "Verification checklist before committing code changes"
audience: "Developers, Contributors"
last_updated: "2025-10-16"
---

# Pre-Commit Checklist

## Code Quality
- [ ] Code follows [Coding Standards](../../development-manual/coding-standards.md)
- [ ] Formatting correct: `black .` ran successfully
- [ ] Linting passes: `ruff check .` shows no errors
- [ ] Type hints: `mypy somafractalmemory/` shows no errors
- [ ] Security: `bandit -r somafractalmemory/` shows no critical issues

## Testing
- [ ] Unit tests written for new functionality
- [ ] All tests pass: `pytest tests/ -v`
- [ ] Coverage maintained or improved: `pytest --cov=somafractalmemory`
- [ ] Edge cases tested
- [ ] No test skips added without justification

## Documentation
- [ ] New features documented in [API Reference](../../development-manual/api-reference.md)
- [ ] Complex logic has inline comments explaining WHY (not just WHAT)
- [ ] Docstrings added to new functions/classes
- [ ] README updated if user-facing changes
- [ ] CHANGELOG.md updated with summary of changes

## Commits
- [ ] Commit messages follow [Contribution Process](../first-contribution.md)
- [ ] One logical change per commit
- [ ] Commit message format: `type: short description` (e.g., `feat: add memory linking API`)
- [ ] No debug statements left in code
- [ ] No hardcoded credentials or secrets

## Code Review Readiness
- [ ] Changes are self-contained (minimal scope)
- [ ] Related PRs referenced in commit message
- [ ] Branch is up-to-date: `git fetch origin` then `git rebase origin/main`
- [ ] No merge conflicts
- [ ] PR title is clear and descriptive

## Pre-Commit Git Hooks
These should run automatically:
- [ ] `black` formatter passes
- [ ] `ruff` linter passes
- [ ] `ruff-format` passes
- [ ] Trailing whitespace removed
- [ ] End-of-file fixer applied

If any hook fails:
```bash
# See what failed
git diff HEAD

# Fix formatting
black .
ruff check . --fix

# Re-stage and commit
git add .
git commit -m "fix: formatting"
```

## Quick Checklist for Fast Review
```bash
# Run all checks before commit
black . && ruff check . --fix && mypy somafractalmemory/ && pytest tests/ -v && bandit -r somafractalmemory/

# If all pass:
git add .
git commit -m "type: description"
git push origin your-branch-name
```

---

**Ready to commit!** 🚀
