---
title: Documentation Style Guide---
purpose: 'title: "Documentation Style Guide"'
audience:
- All Stakeholders
last_updated: '2025-10-16'
---


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
last_updated: "YYYY-MM-DD"
---
 This style guide enforces ISO/IEC 12207 §8.3 for SomaFractalMemory documentation.

 ## Formatting
 - Use `kebab-case.md` for files
 - Use singular nouns for directories
 - All diagrams stored as source (`.puml`, `.drawio`)
 - Fenced code blocks for commands and output
 - Use tables for mapping, checklists, and matrices

 ## Terminology
 - Use consistent terms from `glossary.md`
 - Prefer active voice, short sentences
 - All acronyms defined on first use

 ## Linting & Automation
 - All docs must pass `markdownlint` and link checks in CI
 - Diagrams rendered via CI hooks
 - Version badge auto-generated from git tag

 ## Accessibility
 - Alt-text for images
 - Colour contrast and screen-reader friendly

 See [front_matter.yaml](front_matter.yaml) for standards mapping.
