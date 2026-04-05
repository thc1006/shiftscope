"""Tests for mcp-serve CLI command."""

from __future__ import annotations

from typer.testing import CliRunner

from shiftscope.cli.app import build_cli
from shiftscope.core.analyzer import AnalyzerRegistry
from tests.stubs import StubAnalyzer


def _build_app():
    registry = AnalyzerRegistry()
    registry.register(StubAnalyzer())
    return build_cli(registry)


class TestMCPServeCommand:
    def test_mcp_serve_help(self):
        app = _build_app()
        runner = CliRunner()
        result = runner.invoke(app, ["mcp-serve", "--help"])
        assert result.exit_code == 0
        assert "stdio" in result.output

    def test_mcp_serve_no_transport_error(self):
        app = _build_app()
        runner = CliRunner()
        result = runner.invoke(app, ["mcp-serve"])
        assert result.exit_code == 1
        assert "specify --stdio or --http" in result.output
