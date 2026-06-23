# Contributing

Thank you for your interest in contributing to the HR Policy Knowledge Agent project.

## Getting Started

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/my-change`
3. Install dependencies: `uv sync`
4. Copy and configure environment: `cp .env.example .env`
5. Make your changes.
6. Run the test suite: `uv run pytest tests/ -v -m mock`
7. Commit and push: `git push origin feature/my-change`
8. Open a Pull Request against `main`.

## Development Setup

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) for dependency management
- Node.js 18+ (only for frontend work)

## Code Standards

- Format with `ruff format`
- Lint with `ruff check`
- All tests must pass before merging

## Testing

```bash
# Unit tests (no Azure credentials needed)
uv run pytest tests/ -v -m mock

# Full integration tests (requires Azure resources)
uv run pytest tests/ -v
```

## Branch Naming

- `feature/` — new functionality
- `fix/` — bug fixes
- `docs/` — documentation changes

## Commit Messages

Use clear, descriptive commit messages. Reference related issues where applicable.

## Reporting Issues

Open a GitHub Issue with:
- Steps to reproduce
- Expected vs. actual behavior
- Environment details (OS, Python version, SDK versions)

## Code of Conduct

Be respectful and constructive. Follow the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
