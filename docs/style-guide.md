---# Documentation Style Guide

title: "Documentation Style Guide"

purpose: "Standard formatting, terminology, and style rules for all documentation"## General Principles

audience:

  - "All Contributors"1. **Clarity First**

  - "Documentation Team"   - Write for understanding

prerequisites:   - Use simple language

  - "Markdown basics"   - Explain distributed terms

  - "Git workflow"

version: "1.0.0"2. **Consistency**

last_updated: "2025-10-16"   - Follow established patterns

review_frequency: "quarterly"   - Use standard terminology

---   - Maintain voice and tone



# Documentation Style Guide3. **Completeness**

   - Cover prerequisites

## File Structure & Naming   - Include examples

   - Provide context

### Directory Structure

```## Writing Style

docs/

├─ user-manual/           # End-user guides### Voice and Tone

├─ technical-manual/      # Operations and deployment

├─ development-manual/    # Developer resources- Use active voice

├─ onboarding-manual/     # New team member guides- Be direct and concise

├─ _templates/           # Document templates- Maintain professional tone

└─ automation/          # Linting and automation- Avoid jargon

```

### Formatting

### Naming Conventions

- **kebab-case** for files: `memory-storage.md`#### Headers

- **Descriptive names**: `postgresql-setup.md` not `db.md````markdown

- **Standard prefixes**: `how-to-*`, `guide-*`, `ref-*`# Main Title (H1)

## Major Section (H2)

## Metadata Requirements### Subsection (H3)

#### Detail (H4)

Every document MUST start with:```

```yaml

---#### Code Blocks

title: "Document Title"```markdown

purpose: "One-sentence purpose statement"```python

audience:# Python code with syntax highlighting

  - "Primary audience"def example():

  - "Secondary audience"    pass

prerequisites:```

  - "Required knowledge"```

version: "1.0.0"

last_updated: "YYYY-MM-DD"#### Lists

review_frequency: "quarterly"```markdown

---1. First step

```2. Second step



## Content Structure- Bullet point

- Another point

### Headers```

- Use hierarchical headings (H1 > H2 > H3)

- Don't skip levels## File Organization

- Start with H1 matching document title

### Naming Conventions

### Code Examples

```python- Use kebab-case: `memory-system.md`

# Always include language identifier- Be descriptive: `postgresql-setup.md`

def example_function():- Use standard prefixes:

    """Include docstrings"""  - `how-to-*` for tutorials

    return True  - `guide-*` for guides

```  - `ref-*` for reference



### Tables### Directory Structure

| Column 1 | Column 2 |

|----------|----------|```

| Align content | Properly |docs/

| Use for | Structured data |├─ user-manual/

├─ technical-manual/

### Links├─ development-manual/

- Use descriptive text: `[API Reference](api.md)`└─ onboarding-manual/

- Prefer relative paths: `../user-manual/installation.md````

- Check validity regularly

## Content Guidelines

## Writing Style

### Document Types

### Voice and Tone

- Use active voice: "Run the command" not "The command should be run"#### Tutorials

- Be direct and concise- Step-by-step instructions

- Address reader directly: "You can configure..."- Include prerequisites

- Present tense for current features- Show expected outcomes



### Technical Content#### Reference

- Define abbreviations on first use- Complete and accurate

- Link to glossary entries- Organized logically

- Include expected outputs for commands- Include examples

- Provide verification steps

#### Guides

## Common Elements- Problem-oriented

- Include context

### Admonitions- Explain decisions

```markdown

> **Note:** Supplementary information### Common Elements



> **Warning:** Important caution#### Tables

```markdown

> **Tip:** Helpful suggestion| Header 1 | Header 2 |

```|----------|----------|

| Cell 1   | Cell 2   |

### Step-by-Step Instructions```

1. Start with clear prerequisites

2. Use numbered lists for sequences#### Notes and Warnings

3. Include commands with expected output```markdown

4. Provide verification steps> **Note:** Important information here.



### Command Examples> **Warning:** Critical warning here.

```bash```

# Include comments for distributed commands

docker compose up -d## Markdown Rules

# Expected: All services start successfully

```### Must Have



## Review Process1. Front matter

   ```yaml

### Self-Review Checklist   ---

- [ ] Metadata block complete   title: Document Title

- [ ] Proper heading hierarchy     description: Brief description

- [ ] Code examples tested   ---

- [ ] Links validated   ```

- [ ] Spelling checked

- [ ] Follows style guide2. Table of contents

   ```markdown

### Peer Review   ## Table of Contents

1. Technical accuracy verification   - [Section 1](#section-1)

2. Style guide compliance   - [Section 2](#section-2)

3. Content clarity assessment   ```

4. Link validation

5. Code example testing3. Introduction

   ```markdown

## Automation   ## Overview

   Brief introduction to the document.

### Linting Rules   ```

- `markdownlint` enforces formatting

- Link checker validates references### Best Practices

- Spell checker for content quality

1. **Links**

### CI Requirements   - Use relative paths

- All docs must pass linting   - Check for validity

- Links must be valid   - Describe target

- No broken references allowed

2. **Images**

---   - Include alt text

*Was this document helpful? Please provide feedback to improve our documentation standards.*   - Keep under 1MB
   - Use descriptive names

3. **Code**
   - Include language
   - Show output
   - Explain distributed parts

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
