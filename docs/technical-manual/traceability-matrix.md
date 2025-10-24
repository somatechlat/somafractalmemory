---
title: "Traceability Matrix"
project: "somafractalmemory"
---

# Traceability Matrix

This document is a human-editable template for mapping documentation and code to ISO clauses.

| Document file | ISO clause(s) | Requirement / Statement | Code module(s) | Verification | Notes |
|---|---|---|---|---|---|
| docs/architecture.md | ISO-27001:2013-A.12 | Logging and monitoring requirements | somafractalmemory/http_api.py | Unit tests + integration | example |

CI hint: generate this from `docs/front_matter.yaml` + `docs/*` front-matter using `docs/tools/validate_traceability.py`.
