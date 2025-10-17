# Development Manual---

title: "SomaFractalMemory Development Manual"

This manual is for contributors extending SomaFractalMemory. It defines environment setup, coding conventions, test strategy, and the supported `/memories` API contract.purpose: "Guide for software engineers on how to build, modify, and contribute to the codebase"

audience:

All legacy API variants were removed in October 2025. Only merge code and documentation that respects the `/memories` CRUD/search surface and the new CLI commands (`store`, `search`, `get`, `delete`).  - "Primary: Software Engineers"

  - "Primary: Contributors"
  - "Secondary: Technical Leads"
version: "1.0.0"
last_updated: "2025-10-16"
review_frequency: "quarterly"
---

# Developer Manual

## Overview

Welcome to the Soma Fractal Memory Developer Manual. This guide provides comprehensive information for developers who want to contribute to or build upon the Soma Fractal Memory system.

## Quick Links

- [Local Development Setup](local-setup.md)
- [Coding Standards](coding-standards.md)
- [Testing Guidelines](testing-guidelines.md)
- [API Reference](api-reference.md)
- [Contribution Process](contribution-process.md)
- [Core Concepts](concepts/)

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
