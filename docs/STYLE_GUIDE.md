---
title: "Documentation Style Guide"
purpose: "Ensure consistent documentation style and formatting"
audience:
  - "Documentation Contributors"
  - "Technical Writers"
  - "Developers"
version: "1.0.0"
last_updated: "2025-10-15"
review_frequency: "quarterly"
---

# Documentation Style Guide

## Document Structure

### Metadata Block
Every document must start with a YAML metadata block:
```yaml
---
title: "Document Title"
purpose: "Clear statement of document purpose"
audience:
  - "Primary audience"
  - "Secondary audience"
prerequisites:
  - "Required knowledge/setup"
version: "1.0.0"
last_updated: "YYYY-MM-DD"
review_frequency: "quarterly"
---
```

### Sections
1. Start with level-1 heading matching document title
2. Use hierarchical headings (H1 > H2 > H3)
3. Keep heading levels sequential (don't skip levels)

## Writing Style

### Voice and Tone
- Use active voice
- Be direct and concise
- Write in present tense
- Address the reader directly ("you")

### Technical Content
- Use code blocks for all code examples
- Include language identifier in code blocks
- Show example outputs where relevant
- Link to related documentation

## Formatting

### Code Examples
```python
def example_function():
    """Include docstrings for Python examples"""
    return True
```

### Tables
| Column 1 | Column 2 |
|----------|----------|
| Use tables | For structured data |
| Align | Content properly |

### Lists
- Use bullet points for unordered lists
- Start each item with capital letter
- End each item consistently (with or without period)

1. Use numbered lists for sequences
2. Use parallel structure
3. Maintain consistent capitalization

### Links
- Use descriptive link text
- Link to specific sections where possible
- Check links periodically for validity

## Common Elements

### Admonitions
!!! note
    Use for supplementary information

!!! warning
    Use for important cautions

!!! tip
    Use for helpful suggestions

### Command Line Examples
```bash
# Include comments for complex commands
command --flag value
```

### API Examples
```http
POST /api/endpoint
Content-Type: application/json

{
  "key": "value"
}
```

## Language

### Technical Terms
- Define technical terms on first use
- Link to glossary entries
- Maintain consistent terminology

### Abbreviations
- Spell out on first use with abbreviation in parentheses
- Example: "Representational State Transfer (REST)"
- Use abbreviation consistently thereafter

### Numbers
- Spell out numbers under ten
- Use numerals for 10 and above
- Use numerals for all technical values

## Reviewing

### Self-Review Checklist
- [ ] Metadata block complete
- [ ] Proper heading hierarchy
- [ ] Code examples tested
- [ ] Links validated
- [ ] Spelling and grammar checked
- [ ] Formatting consistent

### Peer Review Process
1. Technical accuracy check
2. Style guide compliance
3. Content clarity and completeness
4. Link validation
5. Code example verification

## References
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)
- [Google Developer Documentation Style Guide](https://developers.google.com/style)
- [Microsoft Writing Style Guide](https://docs.microsoft.com/style-guide)
