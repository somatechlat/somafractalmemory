---
title: "First Contribution Guide"
purpose: "1."
audience:
  - "New Team Members"
last_updated: "2025-10-16"
---

# First Contribution Guide

1. Pick an issue labelled `good-first-issue`.
2. Create a branch `feature/<issue-number>-<short-title>`.
3. Implement the change (often documentation updates or small API improvements).
4. Run `make lint test` and ensure `scripts/smoke.sh` passes.
5. Update the relevant manual—do not introduce files outside the approved documentation structure.
6. Open a PR with:
   - Summary of the change.
   - Screenshots or curl dumps if it touches `/memories`.
   - Confirmation that no legacy endpoints were added.
7. Address review feedback and land the change via Squash & Merge.
