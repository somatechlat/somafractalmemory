# Documentation

## Document Control

| Field | Value |
|---|---|
| Document Title | Documentation |
| Document Identifier | SOMA-SFM-INDEX-001 |
| Version | 1.0.0 |
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


SomaFractalMemory documentation.

## Contents

### Getting Started

- [README](../README.md) - Project overview and quick start

### Reference

- [Architecture](architecture.md) - System architecture and components
- [API Reference](api-reference.md) - Complete API endpoint documentation
- [Deployment](deployment.md) - Production deployment guide

### User Guides

- [User Manual](user-manual/index.md) - End-user documentation
  - [Quick Start](user-manual/quick-start.md)
  - [Features](user-manual/features.md)
  - [Installation](user-manual/installation.md)
  - [FAQ](user-manual/faq.md)

### Developer Guides

- [Development Manual](development-manual/local-setup.md) - Local development setup
- [Technical Manual](technical-manual/index.md) - Technical details
  - [Configuration](technical-manual/config-reference.md)
  - [Endpoints](technical-manual/endpoints.md)
  - [Docker Deployment](technical-manual/deployment-docker.md)
  - [Security](technical-manual/security-secrets.md)
- [Onboarding](onboarding-manual/index.md) - New developer onboarding
- [Style Guide](style-guide.md) - Code style guidelines

## Building Documentation

Documentation is built with MkDocs:

\`\`\`bash
# Install mkdocs
pip install mkdocs mkdocs-material

# Serve locally
mkdocs serve

# Build static site
mkdocs build
\`\`\`

## Contributing

1. Edit markdown files in \`docs/\`
2. Test locally with \`mkdocs serve\`
3. Submit pull request
