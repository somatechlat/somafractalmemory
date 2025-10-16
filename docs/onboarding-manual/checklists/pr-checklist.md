---
title: "Pull Request Checklist"
purpose: "Verification before submitting a pull request for code review"
audience: "Developers, Reviewers, Contributors"
last_updated: "2025-10-16"
---

# Pull Request Checklist

## Before Creating the PR

### Code Changes
- [ ] All code changes are complete and tested locally
- [ ] Branch is based on latest `main` or integration branch
- [ ] No accidental commits from other work
- [ ] All debugging statements removed
- [ ] No commented-out code (unless explaining a design decision)

### Testing
- [ ] All new tests written and passing
- [ ] All existing tests still pass: `pytest tests/ -v`
- [ ] Edge cases covered
- [ ] Manual testing completed in local environment
- [ ] No flaky tests introduced

### Documentation
- [ ] Code changes documented in docstrings
- [ ] User-facing features documented in User Manual
- [ ] API changes documented in API Reference
- [ ] README.md updated if needed
- [ ] CHANGELOG.md entry added

### Compliance
- [ ] Code follows [Coding Standards](../../development-manual/coding-standards.md)
- [ ] No security vulnerabilities: `bandit -r somafractalmemory/`
- [ ] No performance regressions
- [ ] No breaking changes to public APIs (or clearly noted)
- [ ] Backwards compatible (unless major version bump)

## Creating the PR

### PR Title & Description
- [ ] Title is clear and descriptive
- [ ] Title follows convention: `[type]: description` (e.g., `[feat]: add memory linking`)
- [ ] Description explains:
  - What problem does this solve?
  - How does the solution work?
  - Any trade-offs or decisions made?
  - Related issues/PRs (use `Closes #123`)
- [ ] Screenshots/diagrams included (if applicable)

### PR Metadata
- [ ] Correct labels applied (e.g., `documentation`, `bug`, `enhancement`)
- [ ] Assigned to appropriate reviewers
- [ ] Linked to related issues
- [ ] Milestone set (if applicable)

### PR Template
```markdown
## What does this PR do?
[Clear description of changes]

## Why?
[Motivation and context]

## How to test?
[Step-by-step testing instructions]

## Related Issues
Closes #123

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Code follows style guide
- [ ] No breaking changes
- [ ] PR title follows convention
```

## During Code Review

### Responding to Feedback
- [ ] All reviewer comments addressed
- [ ] Changes committed with clear messages (e.g., `fix review comment: simplify logic`)
- [ ] No force-pushes if PR is under review (use `git commit --amend` + `git push`)
- [ ] Conversations marked as resolved after fixes applied

### Approval
- [ ] At least one approval from code owner
- [ ] All CI checks passing
  - [ ] Tests pass
  - [ ] Linting passes
  - [ ] Coverage maintained
- [ ] No conflicts with base branch
- [ ] Ready for merge

## Merging

### Before Merge
- [ ] Latest commits from base branch pulled: `git pull origin main`
- [ ] No new conflicts introduced
- [ ] All CI checks still passing
- [ ] All reviewer approvals still present
- [ ] PR not stale (within 1 week of approval)

### Merge Strategy
- [ ] Use "Squash and merge" for single-commit PRs
- [ ] Use "Create a merge commit" for multi-commit features
- [ ] Use "Rebase and merge" for small bug fixes
- [ ] Commit message follows convention: `type: description (PR #123)`

### Post-Merge
- [ ] Delete feature branch
- [ ] Monitor main branch CI pipeline
- [ ] Update related issues/milestones
- [ ] Post in #releases channel if user-facing change

## Common PR Types & Titles

| Type | Example | Notes |
|------|---------|-------|
| **Feature** | `[feat]: add memory linking API` | New functionality |
| **Bug Fix** | `[fix]: resolve race condition in cache` | Bug resolution |
| **Documentation** | `[docs]: add deployment guide` | Docs only |
| **Refactor** | `[refactor]: simplify vector store logic` | Code improvement, no behavior change |
| **Performance** | `[perf]: optimize query latency by 50%` | Performance improvement |
| **Test** | `[test]: add integration tests for API` | Test coverage only |
| **Security** | `[security]: fix SQL injection in query builder` | Security fix |

---

**PR ready for review!** 🎯
