---
title: "Development Manual"
purpose: "How to build, modify, and contribute to SomaFractalMemory."
audience:
  - "Engineers"
  - "Contributors"
last_updated: "2025-10-24"
---

# Development Manual

## Scope & Audience
This manual covers the development lifecycle, local setup, coding standards, testing guidelines, API reference, and contribution process for SomaFractalMemory. It is written for engineers and contributors.

## Content Blueprint
| Section | ISO Reference | Content |
|---------|---------------|---------|
| Local Setup | ISO 29148 § 5.2 | Dev environment guide |
| Coding Standards | ISO 12207 § 8.3 | Style guide, linting, naming |
| Testing Guidelines | ISO 29119 § 4 | Unit, integration, e2e strategy |
| API Reference | ISO 29148 § 5.4 | OpenAPI spec, versioned |
| Contribution Process | ISO 12207 § 6.6 | Branching, PR workflow, review |

See [local-setup.md](local-setup.md) and [api-reference.md](../technical-manual/api-reference.md) for details.

## Quick Links

- [Local Development Setup](local-setup.md)
- [Coding Standards](coding-standards.md)
- [Testing Guidelines](testing-guidelines.md)
- [API Reference](api-reference.md)
- [Contribution Process](contribution-process.md)

## Repository Structure

```
somafractalmemory/
├─ somafractalmemory/     # Main package code
├─ common/                # Shared utilities
├─ tests/                # Test suite
└─ docs/                 # Documentation
```

## Getting Started

1. [Set up your development environment](local-setup.md)
2. [Review coding standards](coding-standards.md)
3. [Learn about testing](testing-guidelines.md)
4. [Explore the API](api-reference.md)
5. [Follow the contribution process](contribution-process.md)

## Core Technologies

- Python 3.10+
- PostgreSQL
- Redis
- Qdrant
- Docker
