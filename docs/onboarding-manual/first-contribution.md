# Your First Contribution

## Getting Started

### 1. Find an Issue
- Visit the [Issues page](https://github.com/somatechlat/somafractalmemory/issues)
- Look for `good-first-issue` labels

### 2. Set Up Environment
```bash
# Fork the repository on GitHub

# Clone your fork
git clone https://github.com/YOUR-USERNAME/somafractalmemory.git

# Add upstream remote
git remote add upstream https://github.com/somatechlat/somafractalmemory.git
```

## Making Changes

### 1. Create a Branch
```bash
# Update main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name
```

### 2. Write Code
- Follow [coding standards](../development-manual/coding-standards.md)
- Add tests
- Update documentation

### 3. Test Changes
```bash
# Run tests
pytest

# Check code style
black .
mypy .
```

## Submitting Changes

### 1. Create Pull Request
```bash
# Commit changes
git add .
git commit -m "feat(scope): description"

# Push to your fork
git push origin feature/your-feature-name
```

### 2. PR Review Process
1. Open PR on GitHub
2. Wait for CI checks
3. Address review comments
4. Get approval
5. Merge!
