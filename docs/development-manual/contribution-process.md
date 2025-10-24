---
title: "Contribution Process"
purpose: "1."
audience:
  - "Developers and Contributors"
last_updated: "2025-10-16"
---

# Contribution Process

1. **Discuss** the change in `#somafractalmemory-dev` or open a GitHub issue.
2. **Plan** using the VIBE 7-step workflow (understand → gather → investigate → verify context → plan → implement → verify). Capture assumptions if any.
3. **Branch** from `soma_integration` using the naming scheme `feature/<short-description>`.
4. **Implement** the change following coding standards and VIBE rules. Do not add new endpoints unless they align with the `/memories` surface.
5. **Documentation-first**: Update the appropriate manual. Docs are the source of truth; no stray files or directories.
6. **Run checks**:
   ```bash
   make lint test
   mkdocs build
   ```
7. **Open a Pull Request** with:
   - Linked issue or rationale.
   - Summary of changes.
   - Testing evidence (unit/integration, or CLI/curl outputs). New behavior must have tests.
8. **Review**: At least one maintainer must approve. Reviewers confirm:
   - `/memories` contract untouched or properly versioned.
   - No legacy references to `/store`, `/recall`, or graph APIs remain.
   - Documentation updated.
9. **Escalation**: If blocked after two attempts to gather context, raise for human review.
10. **Merge** using Squash & Merge. Delete the branch after merge.
