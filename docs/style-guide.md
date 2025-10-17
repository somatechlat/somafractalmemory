# Documentation Style Guide---

title: "Documentation Style Guide"

- Use **sentence case** for headings.purpose: "Standard formatting, terminology, and style rules for all documentation"

- Keep paragraphs concise and prefer bullet lists for procedures.audience:

- All command examples must use fenced code blocks with language hints (`bash`, `json`).  - "All Contributors"

- Link to other manual pages using relative paths.  - "Documentation Team"

- Never reference removed endpoints (`/store`, `/recall`, graph routes). Always refer to the `/memories` API.prerequisites:

- Include verification steps for every procedure.  - "Markdown basics"

- Run `markdownlint` before committing documentation changes: `markdownlint-cli2 docs/**/*.md`.version: "1.0.0"

last_updated: "2025-10-16"
review_frequency: "quarterly"
---

# Documentation Style Guide

## General Principles

1. **Clarity First** - Write for understanding
2. **Consistency** - Follow established patterns
3. **Completeness** - Cover prerequisites

## Metadata Requirements

Every document MUST include frontmatter:

```yaml
---
title: "Document Title"
purpose: "One-sentence purpose"
audience:
  - "Primary audience"
version: "1.0.0"
last_updated: "YYYY-MM-DD"
review_frequency: "quarterly"
---
```

## Naming Conventions

- Use **kebab-case**: `memory-storage.md`
- Use **descriptive names**: `postgresql-setup.md`
- Use **prefixes**: `how-to-*`, `guide-*`, `ref-*`

## Writing Style

- Active voice: "Run the command"
- Direct and concise
- Address reader directly

---

*Documentation feedback welcome.*
