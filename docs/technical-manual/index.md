title: "Technical Manual"
purpose: "This manual is for SREs, platform engineers, and operators responsible for deploying and running SomaFractalMemory."
audience:
  - "Operators and SREs"
last_updated: "2025-10-16"

# Technical Manual

## Scope & Audience
This manual covers deployment, operations, architecture, monitoring, runbooks, and security for SomaFractalMemory. It is written for SREs, ops, and platform engineers.

## Content Blueprint
| Section | ISO Reference | Content |
|---------|---------------|---------|
| Architecture | ISO 42010 § 3 | C4 diagrams, component map |
| Deployment | ISO 12207 § 6.4 | Installation, configuration |
| Monitoring | ISO 21500 § 7.5 | Metrics, dashboards, alerts |
| Runbooks | ISO 12207 § 6.5 | Incident response, recovery |
| Security | ISO 27001 § 5 | Secrets policy, RBAC matrix |

See [architecture.md](architecture.md) for diagrams and [deployment.md](deployment.md) for install/configuration.

Every section reflects the simplified `/memories` API introduced in version 2.0.0. All runbooks, diagrams, and playbooks have been purged of legacy `/store`/`/recall` references.
