# Contribution Process

## Overview

This guide explains how to contribute to the Soma Fractal Memory project.

## Prerequisites

- GitHub account
- Signed Contributor License Agreement (CLA)
- Development environment [set up](local-setup.md)

## Process Overview

1. Find or create issue
2. Fork repository
3. Create branch
4. Make changes
5. Submit PR
6. Review process
7. Merge

## Detailed Steps

### 1. Issue Creation/Selection

- Check existing issues
- Use issue templates
- Get assignment

### 2. Development

```bash
# Fork and clone
git clone https://github.com/YOUR-USERNAME/somafractalmemory.git
cd somafractalmemory

# Create branch
git checkout -b feature/your-feature

# Make changes
# ...

# Run tests
pytest

# Check style
black .
mypy .
```

### 3. Pull Request

#### PR Template
```markdown
## Description
Brief description of changes

## Type of change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Documentation
- [ ] Documentation updated
- [ ] Changelog updated
```

### 4. Review Process

1. Automated Checks
   - CI pipeline
   - Code coverage
   - Style checks

2. Code Review
   - 2 approvals required
   - Address feedback
   - Update PR

3. Final Checks
   - Squash commits
   - Rebase if needed
   - Update changelog

## Best Practices

### Commits

```
type(scope): description

Longer description if needed

Refs: #123
```

Types:
- feat: New feature
- fix: Bug fix
- docs: Documentation
- style: Formatting
- refactor: Code restructuring
- test: Adding tests
- chore: Maintenance

### Branch Naming

- feature/description
- fix/issue-description
- docs/description
- refactor/description

### Code Style

- Follow [coding standards](coding-standards.md)
- Use type hints
- Add docstrings
- Write tests

## Review Guidelines

### Reviewer Responsibilities

1. Code Quality
   - Style compliance
   - Test coverage
   - Documentation

2. Functionality
   - Feature completeness
   - Bug verification
   - Edge cases

3. Performance
   - Resource usage
   - Scalability
   - Efficiency

### Author Responsibilities

1. Before Review
   - Self-review changes
   - Run all tests
   - Update documentation

2. During Review
   - Respond promptly
   - Explain changes
   - Update based on feedback

3. After Approval
   - Squash commits
   - Merge PR
   - Delete branch

## Release Process

1. Version Bump
   - Update version
   - Update changelog
   - Create tag

2. Release Build
   - Create release
   - Upload artifacts
   - Update documentation

## Support

- GitHub Issues
- Development chat (#dev-chat)
- Weekly office hours
