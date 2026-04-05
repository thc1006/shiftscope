# Contributing to ShiftScope

Thank you for your interest in contributing to ShiftScope!

## Development Setup

```bash
# Clone the repository
git clone https://github.com/shiftscope/shiftscope.git
cd shiftscope

# Install dependencies (requires uv)
make bootstrap

# Run tests
make test

# Run linter
make lint
```

## Making Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-change`)
3. Write tests first (TDD)
4. Implement your change
5. Run `make verify` to ensure all checks pass
6. Submit a pull request

## Writing an Analyzer Plugin

See `analyzers/gateway_api/` for a reference implementation. An analyzer plugin:

1. Subclasses `shiftscope.core.analyzer.Analyzer`
2. Implements `analyze()` and `list_rules()` methods
3. Contains `Rule` subclasses with `applies_to()` and `evaluate()` methods
4. Registers via entry points in `pyproject.toml`

## Code Style

- Python 3.12+
- Ruff for linting and formatting
- Type hints required on all public APIs
- Pydantic BaseModel for data models
- ABC for behavioral contracts

## Testing

- pytest for all tests
- Hypothesis for property-based testing of rule boundaries
- syrupy for golden-file snapshot tests
- All PRs must maintain test coverage above 90%

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
