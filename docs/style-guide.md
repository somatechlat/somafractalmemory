# Documentation Style Guide

## General Principles

1. **Clarity First**
   - Write for understanding
   - Use simple language
   - Explain complex terms

2. **Consistency**
   - Follow established patterns
   - Use standard terminology
   - Maintain voice and tone

3. **Completeness**
   - Cover prerequisites
   - Include examples
   - Provide context

## Writing Style

### Voice and Tone

- Use active voice
- Be direct and concise
- Maintain professional tone
- Avoid jargon

### Formatting

#### Headers
```markdown
# Main Title (H1)
## Major Section (H2)
### Subsection (H3)
#### Detail (H4)
```

#### Code Blocks
```markdown
```python
# Python code with syntax highlighting
def example():
    pass
```
```

#### Lists
```markdown
1. First step
2. Second step

- Bullet point
- Another point
```

## File Organization

### Naming Conventions

- Use kebab-case: `memory-system.md`
- Be descriptive: `postgresql-setup.md`
- Use standard prefixes:
  - `how-to-*` for tutorials
  - `guide-*` for guides
  - `ref-*` for reference

### Directory Structure

```
docs/
├─ user-manual/
├─ technical-manual/
├─ development-manual/
└─ onboarding-manual/
```

## Content Guidelines

### Document Types

#### Tutorials
- Step-by-step instructions
- Include prerequisites
- Show expected outcomes

#### Reference
- Complete and accurate
- Organized logically
- Include examples

#### Guides
- Problem-oriented
- Include context
- Explain decisions

### Common Elements

#### Tables
```markdown
| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |
```

#### Notes and Warnings
```markdown
> **Note:** Important information here.

> **Warning:** Critical warning here.
```

## Markdown Rules

### Must Have

1. Front matter
   ```yaml
   ---
   title: Document Title
   description: Brief description
   ---
   ```

2. Table of contents
   ```markdown
   ## Table of Contents
   - [Section 1](#section-1)
   - [Section 2](#section-2)
   ```

3. Introduction
   ```markdown
   ## Overview
   Brief introduction to the document.
   ```

### Best Practices

1. **Links**
   - Use relative paths
   - Check for validity
   - Describe target

2. **Images**
   - Include alt text
   - Keep under 1MB
   - Use descriptive names

3. **Code**
   - Include language
   - Show output
   - Explain complex parts

## Review Process

### Pre-submission

1. Run linter
   ```bash
   markdownlint *.md
   ```

2. Check links
   ```bash
   markdown-link-check *.md
   ```

3. Verify formatting
   ```bash
   prettier --check *.md
   ```

### Review Checklist

- [ ] Follows style guide
- [ ] All links work
- [ ] Images have alt text
- [ ] Code is formatted
- [ ] No spelling errors
- [ ] Front matter complete
