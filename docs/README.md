# SOMA-SFM-INDEX-001 — Documentation

## Document Control

| Field | Value |
|---|---|
| Document Title | Documentation Index |
| Document Identifier | SOMA-SFM-INDEX-001 |
| Version | 1.1.0 |
| Date | 2026-09-28 |
| Status | Draft |
| Author | SomaTech Engineering |
| Approver | — |
| Classification | Internal |
| ISO Reference | ISO 9001:2015 — Quality Management Systems — Requirements |
| Next Review | 2026-12-28 |


## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0.0 | 2026-09-28 | SomaTech Engineering | Initial issue. Brought under the house ISO document-control contract. |
| 1.1.0 | 2026-09-28 | SomaTech Engineering | Contents rewritten to the tree that actually exists. The previous index advertised `user-manual/`, `development-manual/`, `technical-manual/` and `onboarding-manual/`; none of those directories exist, so thirteen of its links resolved to nothing. Also fixed fenced code blocks that were written with escaped backticks and rendered as literal text. |

SomaFractalMemory documentation.

## Contents

### Guides

- [User Guide](USER_GUIDE.md) — install, quick-start, features and FAQ
- [Operations Manual](OPS_MANUAL.md) — endpoints and operating procedures
- [Production Readiness](PRODUCTION_READINESS.md) — production readiness checklist
- [Style Guide](style-guide.md) — code style guidelines

### Reference

- [Architecture](architecture.md) — system architecture and components
- [API Reference](api-reference.md) — API endpoint documentation
- [Deployment](deployment.md) — production deployment guide
- [SRS](SRS-SOMAFRACTALMEMORY-MASTER.md) — software requirements specification

### Quality Management System

Controlled documents under `docs/iso/`. The set is governed by
[SOMA-SFM-DOCS-001](iso/SOMA-SFM-DOCS-001.md) and inventoried in the
[Document Register](iso/DOCUMENT-REGISTER.md).

- [Quality Manual](iso/SOMA-SFM-QMS-001.md)
- [Document Control & Traceability](iso/SOMA-SFM-DOCS-001.md)
- [Architecture](iso/SOMA-SFM-ARCH-001.md) ·
  [Software Development Plan](iso/SOMA-SFM-SDP-001.md) ·
  [Requirements](iso/SOMA-SFM-SRS-001.md)
- [Security](iso/SOMA-SFM-SEC-001.md) ·
  [Verification & Validation](iso/SOMA-SFM-VV-001.md) ·
  [Risk Register](iso/SOMA-SFM-RISK-001.md)
- [Audit](iso/SOMA-SFM-AUDIT-001.md) ·
  [Compatibility](iso/SOMA-SFM-COMPAT-001.md) ·
  [Production](iso/SOMA-SFM-PROD-001.md)

### Project Records

Records of specific project work under `docs/project/`. Registered in the
Document Register, but not QMS documents.

- [Execution Plan](project/SOMA-SFM-EXEC-001.md)
- [Architecture Redesign](project/SOMA-ARCH-REDESIGN-001.md)
- [Feature Matrix](project/SOMA-FEAT-MATRIX-001.md)
- [Module Architecture](project/SOMA-MOD-ARCH-001.md) ·
  [Module Specification](project/SOMA-MOD-SPEC-001.md)
- [UI Specification](project/SOMA-UI-SPEC-001.md) ·
  [UI/UX](project/SOMA-UI-UX-001.md) ·
  [UI Mockups](project/SOMA-UI-MOCKUPS-001.md)

## Document control

Every `*.md` under `docs/` is a controlled document. Before editing one, read
[SOMA-SFM-DOCS-001](iso/SOMA-SFM-DOCS-001.md). After adding, renaming or
removing one:

```bash
make docs-register   # regenerate docs/iso/DOCUMENT-REGISTER.md
make docs-check      # enforce C-01..C-12
```

## Building the site

Documentation is built with MkDocs. The navigation in `mkdocs.yml` lists real
pages only, and the site is built with `--strict`, so a dangling link fails the
build.

```bash
pip install "mkdocs-material[imaging]"
mkdocs build --strict
```

End of Document
