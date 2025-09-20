SomaFractalMemory — Documentation Table of Contents
==================================================

This is the curated table of contents for the canonical documentation set. Files listed here are the recommended, authoritative docs for the repository. Use this TOC as the entry point for maintainers and operators.

Canonical docs (recommended)

- `README.md` — User-facing quickstart, install, and high-level overview (already present at repo root).
- `docs/README_canonical.md` — Formal canonical specification (already present).
- `docs/ARCHITECTURE.md` — Architecture, components, dataflows, integration patterns.
- `docs/METRICS.md` — Metric names, types, labels, PromQL examples, scrape/expose guidance, alert suggestions.
- `docs/OPERATIONAL.md` — Runbook: startup, health checks, WAL reconciliation, backups, common incidents and remediation steps.
- `docs/CONTRIBUTING.md` — Contribution guidelines, commit message style, security reporting, patch process.
- `docs/CANONICAL_PROGRESS.md` — Progress snapshots and engineering notes (kept as operational history).
- `docs/SECURITY_ROADMAP.md` — Security decisions and opt-in flags (kept).
- `docs/ROADMAP.md` — Roadmap and CI plan (kept; consider pruning to high-level items only).

Files recommended for relocation or removal (proposal, do not delete yet)

- Grafana dashboard JSON has been archived to `docs/archive/grafana/soma_dashboard.json` and removed from active docs. If you want a separate dashboards repo, we can extract it there.

How to use this TOC

Read `README.md` first for a quick start. For integration and ops, read `docs/ARCHITECTURE.md`, then `docs/OPERATIONAL.md`. For observability and monitoring, read `docs/METRICS.md`.
