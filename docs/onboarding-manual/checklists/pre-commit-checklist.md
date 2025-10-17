---
title: "Pre-Commit Checklist"
purpose: "- [ ] `make lint` passes."
audience:
  - "New Team Members"
last_updated: "2025-10-16"
---

# Pre-Commit Checklist

- [ ] `make lint` passes.
- [ ] `pytest` passes locally.
- [ ] API smoke test (`scripts/smoke.sh`) passes.
- [ ] Documentation updated (only within the approved directories).
- [ ] No references to `/store`, `/recall`, or graph endpoints introduced.
