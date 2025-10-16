------# Documentation Style Guide

title: "Documentation Style Guide"

purpose: "Standard formatting, terminology, and style rules for all documentation"title: "Documentation Style Guide"

audience:

  - "All Contributors"purpose: "Standard formatting, terminology, and style rules for all documentation"## General Principles

  - "Documentation Team"

prerequisites:audience:

  - "Markdown basics"

  - "Git workflow"  - "All Contributors"1. **Clarity First**

version: "1.0.0"

last_updated: "2025-10-16"  - "Documentation Team"   - Write for understanding

review_frequency: "quarterly"

---prerequisites:   - Use simple language



# Documentation Style Guide  - "Markdown basics"   - Explain distributed terms



## General Principles  - "Git workflow"



1. **Clarity First**version: "1.0.0"2. **Consistency**

   - Write for understanding

   - Use simple languagelast_updated: "2025-10-16"   - Follow established patterns

   - Explain unfamiliar terms

review_frequency: "quarterly"   - Use standard terminology

2. **Consistency**

   - Follow established patterns---   - Maintain voice and tone

   - Use standard terminology

   - Maintain voice and tone



3. **Completeness**# Documentation Style Guide3. **Completeness**

   - Cover prerequisites

   - Include examples   - Cover prerequisites

   - Provide context

## File Structure & Naming   - Include examples

## Writing Style

   - Provide context

### Voice and Tone

### Directory Structure

- Use active voice: "Run the command" not "The command should be run"

- Be direct and concise```## Writing Style

- Address reader directly: "You can configure..."

- Use present tense for current featuresdocs/



### Document Types├─ user-manual/           # End-user guides### Voice and Tone



#### Tutorials├─ technical-manual/      # Operations and deployment

- Step-by-step instructions

- Include prerequisites├─ development-manual/    # Developer resources- Use active voice

- Show expected outcomes

├─ onboarding-manual/     # New team member guides- Be direct and concise

#### Reference

- Complete and accurate├─ _templates/           # Document templates- Maintain professional tone

- Organized logically

- Include examples└─ automation/          # Linting and automation- Avoid jargon



#### Guides```

- Problem-oriented

- Include context### Formatting

- Explain decisions

### Naming Conventions

### Common Elements

- **kebab-case** for files: `memory-storage.md`#### Headers

#### Step-by-Step Instructions

1. Start with clear prerequisites- **Descriptive names**: `postgresql-setup.md` not `db.md````markdown

2. Use numbered lists for sequences

3. Include commands with expected output- **Standard prefixes**: `how-to-*`, `guide-*`, `ref-*`# Main Title (H1)

4. Provide verification steps

## Major Section (H2)

#### Command Examples

```bash## Metadata Requirements### Subsection (H3)

# Include comments for unclear commands

docker compose up -d#### Detail (H4)

# Expected: All services start successfully

```Every document MUST start with:```



#### Tables```yaml

```markdown

| Header 1 | Header 2 |---#### Code Blocks

|----------|----------|

| Cell 1   | Cell 2   |title: "Document Title"```markdown

```

purpose: "One-sentence purpose statement"```python

#### Notes and Warnings

```markdownaudience:# Python code with syntax highlighting

> **Note:** Important information here.

> **Warning:** Critical warning here.  - "Primary audience"def example():

> **Tip:** Helpful suggestion here.

```  - "Secondary audience"    pass



## File Organizationprerequisites:```



### Naming Conventions  - "Required knowledge"```



- **kebab-case** for files: `memory-storage.md`version: "1.0.0"

- **Descriptive names**: `postgresql-setup.md` not `db.md`

- **Standard prefixes**: `how-to-*`, `guide-*`, `ref-*`last_updated: "YYYY-MM-DD"#### Lists



### Directory Structurereview_frequency: "quarterly"```markdown



```---1. First step

docs/

├─ user-manual/           # End-user guides```2. Second step

├─ technical-manual/      # Operations and deployment

├─ development-manual/    # Developer resources

├─ onboarding-manual/     # New team member guides

└─ automation/            # Linting and automation## Content Structure- Bullet point

```

- Another point

## Markdown Rules

### Headers```

### Headers

- Use hierarchical headings (H1 > H2 > H3)

```markdown

# Main Title (H1)- Don't skip levels## File Organization

## Major Section (H2)

### Subsection (H3)- Start with H1 matching document title

#### Detail (H4)

```### Naming Conventions



- Use hierarchical headings (H1 > H2 > H3)### Code Examples

- Don't skip levels

- Start with H1 matching document title```python- Use kebab-case: `memory-system.md`



### Code Blocks# Always include language identifier- Be descriptive: `postgresql-setup.md`



```pythondef example_function():- Use standard prefixes:

# Always include language identifier

def example_function():    """Include docstrings"""  - `how-to-*` for tutorials

    """Include docstrings"""

    return True    return True  - `guide-*` for guides

```

```  - `ref-*` for reference

### Lists



```markdown

1. First step### Tables### Directory Structure

2. Second step

| Column 1 | Column 2 |

- Bullet point

- Another point|----------|----------|```

```

| Align content | Properly |docs/

### Links

| Use for | Structured data |├─ user-manual/

- Use descriptive text: `[API Reference](api.md)`

- Prefer relative paths: `../user-manual/installation.md`├─ technical-manual/

- Check validity regularly

### Links├─ development-manual/

## Metadata Requirements

- Use descriptive text: `[API Reference](api.md)`└─ onboarding-manual/

Every document MUST start with:

- Prefer relative paths: `../user-manual/installation.md````

```yaml

---- Check validity regularly

title: "Document Title"

purpose: "One-sentence purpose statement"## Content Guidelines

audience:

  - "Primary audience"## Writing Style

  - "Secondary audience"

prerequisites:### Document Types

  - "Required knowledge"

version: "1.0.0"### Voice and Tone

last_updated: "YYYY-MM-DD"

review_frequency: "quarterly"- Use active voice: "Run the command" not "The command should be run"#### Tutorials

---

```- Be direct and concise- Step-by-step instructions



## Content Guidelines- Address reader directly: "You can configure..."- Include prerequisites



### Technical Content- Present tense for current features- Show expected outcomes



- Define abbreviations on first use

- Link to glossary entries

- Include expected outputs for commands### Technical Content#### Reference

- Provide verification steps

- Define abbreviations on first use- Complete and accurate

### Admonitions

- Link to glossary entries- Organized logically

```markdown

> **Note:** Supplementary information- Include expected outputs for commands- Include examples



> **Warning:** Important caution- Provide verification steps



> **Tip:** Helpful suggestion#### Guides

```

## Common Elements- Problem-oriented

## Best Practices

- Include context

1. **Links**

   - Use relative paths### Admonitions- Explain decisions

   - Check for validity

   - Describe target```markdown



2. **Images**> **Note:** Supplementary information### Common Elements

   - Include alt text

   - Keep under 1MB

   - Use descriptive names

> **Warning:** Important caution#### Tables

3. **Code**

   - Include language specifier```markdown

   - Show expected output

   - Explain unclear parts> **Tip:** Helpful suggestion| Header 1 | Header 2 |



## Review Process```|----------|----------|



### Pre-submission| Cell 1   | Cell 2   |



1. Run linter### Step-by-Step Instructions```

   ```bash

   markdownlint *.md1. Start with clear prerequisites

   ```

2. Use numbered lists for sequences#### Notes and Warnings

2. Check links

   ```bash3. Include commands with expected output```markdown

   markdown-link-check *.md

   ```4. Provide verification steps> **Note:** Important information here.



3. Verify formatting

   ```bash

   prettier --check *.md### Command Examples> **Warning:** Critical warning here.

   ```

```bash```

### Review Checklist

# Include comments for distributed commands

- [ ] Follows style guide

- [ ] All links workdocker compose up -d## Markdown Rules

- [ ] Images have alt text

- [ ] Code is formatted# Expected: All services start successfully

- [ ] No spelling errors

- [ ] Front matter complete```### Must Have



---



*Was this document helpful? Please provide feedback to improve our documentation standards.*## Review Process1. Front matter


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
