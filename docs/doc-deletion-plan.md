---
title: "Documentation Deletion Plan"
generated_on: "2025-10-24"
author: "automation: docs maintainer"
---

# Documentation Deletion Plan (proposed)

This file lists all markdown documentation files found under `docs/` and a recommended action.
Per your instruction, the recommendation is to hard-delete all non-canonical docs. I will NOT perform
any deletion until you give explicit final confirmation.

Canonical files to KEEP (created or designated canonical in this session):

- `docs/documentation-guide.md` — KEEP (canonical ISO guide)
- `docs/front_matter.yaml` — KEEP (global doc metadata)
- `docs/technical-manual/traceability-matrix.md` — KEEP (traceability template)
- `docs/.github/workflows/doc-health.yml` — KEEP (doc-health workflow draft)
- `docs/tools/validate_traceability.py` — KEEP (validator script)

Recommended DELETE (all other docs discovered by the scan):

The list below is derived from the recent scan (`docs/tools/validate_traceability.py`). Each file is recommended for hard deletion unless you mark it KEEP.

MISSING README.md
MISSING changelog.md
MISSING ci-cd.md
MISSING glossary.md
MISSING style-guide.md
MISSING onboarding-manual/codebase-walkthrough.md
MISSING onboarding-manual/domain-knowledge.md
MISSING onboarding-manual/environment-setup.md
MISSING onboarding-manual/first-contribution.md
MISSING onboarding-manual/index.md
MISSING onboarding-manual/onboarding-timeline.md
MISSING onboarding-manual/project-context.md
MISSING onboarding-manual/team-collaboration.md
MISSING onboarding-manual/checklists/pr-checklist.md
MISSING onboarding-manual/checklists/pre-commit-checklist.md
MISSING onboarding-manual/checklists/setup-checklist.md
MISSING onboarding-manual/resources/glossary.md
MISSING onboarding-manual/resources/troubleshooting.md
MISSING onboarding-manual/resources/useful-links.md
MISSING user-manual/faq.md
MISSING user-manual/index.md
MISSING user-manual/installation.md
MISSING user-manual/quick-start-tutorial.md
MISSING user-manual/features/memory-search.md
MISSING user-manual/features/memory-storage.md
MISSING technical-manual/api-reference.md
MISSING technical-manual/architecture.md
MISSING technical-manual/backup-and-recovery.md
MISSING technical-manual/ci-cd.md
MISSING technical-manual/deployment.md
MISSING technical-manual/index.md
MISSING technical-manual/monitoring.md
MISSING technical-manual/upgrade-features.md
MISSING technical-manual/security/rbac-matrix.md
MISSING technical-manual/security/secrets-policy.md
MISSING technical-manual/runbooks/api-service.md
MISSING technical-manual/runbooks/vector-store.md
MISSING development-manual/api-reference.md
MISSING development-manual/coding-standards.md
MISSING development-manual/contribution-process.md
MISSING development-manual/index.md
MISSING development-manual/local-setup.md
MISSING development-manual/testing-guidelines.md

Notes and safety measures
- I will create a TAR archive backup of the entire `docs/` directory before deleting anything, stored at the repository root as `docs-backup-2025-10-24.tar.gz`, unless you explicitly instruct otherwise.
- Deletions will be performed as git operations (rm + commit) so they can be reverted from the branch if needed. I will create a separate branch `docs/prune-2025-10-24` for the deletion commit.
- I will NOT push the deletion branch to remote unless you request it.

Next steps (what I will do after your explicit confirmation):
1. Create `docs-backup-2025-10-24.tar.gz` in the repository root.
2. Create branch `docs/prune-2025-10-24` (from current branch `perf/async-metrics-msgpack`).
3. Remove the files marked DELETE using `git rm` and commit with message: "chore(docs): prune non-canonical docs — 2025-10-24".
4. Run `git status` and show you the list of removed files and the commit diff for final approval.
5. If you confirm, optionally push the branch to origin.

Please review this plan. Reply with one of:

- `CONFIRM BACKUP AND DELETE` — create backup and perform deletions on a new local branch (I will show the commit before pushing).
- `CONFIRM DELETE NO BACKUP` — perform deletions without creating the TAR backup.
- `CANCEL` — stop and make no deletions.
- `KEEP <file>` — to mark any file in the DELETE list to be kept; you can list multiple files separated by commas.
