# Contributing to NexusAI

Thank you for your interest in contributing to NexusAI! This document provides guidelines for contributing to the project.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally
3. **Set up the development environment** (see [Getting Started](./docs/GETTING_STARTED.md))
4. **Create a feature branch** from `main`

## Development Workflow

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring

### Commit Messages

Follow conventional commits:

```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
```
feat(chat): add streaming response support
fix(auth): resolve token refresh race condition
docs(api): update endpoint documentation
```

## Code Style

### Python (Backend)

- Follow PEP 8
- Use type hints
- Format with `ruff format`
- Lint with `ruff check`
- Maximum line length: 100

```bash
cd backend
ruff format .
ruff check .
mypy app
```

### TypeScript (Frontend)

- Follow ESLint configuration
- Use TypeScript strict mode
- Format with Prettier (via ESLint)

```bash
cd frontend
npm run lint
npm run type-check
```

## Testing

### Backend Tests

```bash
cd backend
pytest
pytest --cov=app  # With coverage
```

### Frontend Tests

```bash
cd frontend
npm test
npm run test:coverage
```

## Pull Request Process

1. **Update documentation** if needed
2. **Add tests** for new functionality
3. **Ensure all tests pass**
4. **Update the README** if applicable
5. **Create a pull request** with a clear description

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How has this been tested?

## Checklist
- [ ] Code follows style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

## Code Review

- Be respectful and constructive
- Focus on the code, not the person
- Explain reasoning for requested changes
- Approve once all concerns are addressed

## Reporting Issues

Use GitHub Issues with appropriate labels:

- `bug` - Something isn't working
- `enhancement` - New feature request
- `documentation` - Documentation improvements
- `question` - Need help/clarification

### Bug Report Template

```markdown
**Describe the bug**
Clear description of the issue

**To Reproduce**
Steps to reproduce the behavior

**Expected behavior**
What you expected to happen

**Environment**
- OS: [e.g., macOS 14]
- Python version: [e.g., 3.12]
- Node version: [e.g., 20.10]

**Additional context**
Any other relevant information
```

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

Feel free to open an issue for any questions about contributing!
