---
title: "Coding Standards"
purpose: "- **Language**: Python 3.11 with `ruff` and `black` enforced via pre-commit."
audience:
  - "Developers and Contributors"
last_updated: "2025-10-16"
---

# Coding Standards

- **Language**: Python 3.11 with `ruff` and `black` enforced via pre-commit.
- **Imports**: Follow the `isort` profile already configured in `pyproject.toml`.
- **Typing**: Use `typing.Annotated` sparingly; prefer concrete `TypedDict`/`pydantic` models for API payloads.
- **Logging**: Emit structured logs through `structlog`. Never `print` in production code.
- **HTTP API**: New routes must go through the FastAPI app in `http_api.py`. Do not reintroduce `/store`, `/recall`, or graph endpoints.
- **CLI**: Mirror the `/memories` capabilities only. Commands must be idempotent and return JSON on stdout.
- **Docs**: Update the appropriate manual when changing behaviour. The docs tree must remain compliant with the 4-manual structure.

## VIBE Coding Rules (Adopted)

Non-negotiable standards for safe, verifiable, production-ready changes:

- NO BULLSHIT: No placeholders or fake implementations. If uncertain, state risks.
- CHECK FIRST, CODE SECOND: Review architecture and callers before editing.
- NO UNNECESSARY FILES: Prefer modifying existing files; create new files only when justified.
- REAL IMPLEMENTATIONS ONLY: No TODOs or stubs; all functions complete and testable.
- DOCUMENTATION = TRUTH: Update docs; cite official sources when using external libs.
- COMPLETE CONTEXT REQUIRED: Trace data flow end-to-end before changes.

### 7-Step Workflow
1. Understand → 2. Gather Knowledge → 3. Investigate → 4. Verify Context → 5. Plan → 6. Implement → 7. Verify.

### Testing & Error Handling
- Add or update unit tests for every new function/behavior; run `pytest` locally.
- Public functions must catch expected exceptions and log via `structlog`.
- Never invent APIs or response shapes—verify with actual code or official docs.

### CI Expectations
- Lint (ruff/black/mypy), Tests (pytest), Docs (markdownlint/link-check) must pass.
