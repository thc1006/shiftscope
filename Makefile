.PHONY: bootstrap test lint verify clean

bootstrap:
	@command -v uv >/dev/null 2>&1 || { echo "uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
	uv sync --group dev --group test --extra cli --extra mcp

test:
	uv run pytest -q

test-cov:
	uv run pytest --cov --cov-report=term-missing

lint:
	uv run ruff check src tests

format:
	uv run ruff format src tests

verify: lint test
	uv run python -m compileall src tests -q

clean:
	rm -rf dist build *.egg-info .pytest_cache .coverage htmlcov out .ruff_cache
