.PHONY: bootstrap test lint verify demo clean

bootstrap:
	@command -v uv >/dev/null 2>&1 || { echo "uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
	uv sync --group dev --group test --extra cli --extra mcp

test:
	uv run pytest -q

test-cov:
	uv run pytest --cov --cov-report=term-missing

lint:
	uv run ruff check src tests analyzers

format:
	uv run ruff format src tests analyzers

verify: lint test
	python -m compileall src tests analyzers -q

clean:
	rm -rf dist build *.egg-info .pytest_cache .coverage htmlcov out .ruff_cache
