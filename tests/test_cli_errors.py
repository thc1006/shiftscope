"""Tests for CLI error handling — friendly messages instead of tracebacks."""

from __future__ import annotations

from typer.testing import CliRunner

from shiftscope.analyzers.gateway_api import GatewayApiAnalyzer
from shiftscope.cli.app import build_cli
from shiftscope.core.analyzer import AnalyzerRegistry
from tests.stubs import StubAnalyzer


def _build_app():
    registry = AnalyzerRegistry()
    registry.register(StubAnalyzer())
    registry.register(GatewayApiAnalyzer())
    return build_cli(registry)


class TestCLIErrorHandling:
    def test_nonexistent_file_friendly_error(self):
        app = _build_app()
        runner = CliRunner()
        result = runner.invoke(app, ["analyze", "gateway-api", "/nonexistent/file.yaml"])
        assert result.exit_code == 1
        assert "input file not found" in result.output
        assert "Traceback" not in result.output

    def test_invalid_yaml_friendly_error(self, tmp_path):
        bad = tmp_path / "bad.yaml"
        bad.write_text("{{{{invalid yaml")
        app = _build_app()
        runner = CliRunner()
        result = runner.invoke(app, ["analyze", "gateway-api", str(bad)])
        assert result.exit_code == 1
        assert "Error" in result.output
        assert "Traceback" not in result.output

    def test_unknown_analyzer_friendly_error(self):
        app = _build_app()
        runner = CliRunner()
        result = runner.invoke(app, ["analyze", "nonexistent", "test.yaml"])
        assert result.exit_code == 1
        assert "not found" in result.output
        assert "Traceback" not in result.output

    def test_invalid_format_friendly_error(self, tmp_path):
        f = tmp_path / "test.yaml"
        f.write_text("test\n")
        app = _build_app()
        runner = CliRunner()
        result = runner.invoke(app, ["analyze", "stub-analyzer", str(f), "--output", "xml"])
        assert result.exit_code == 1
        assert "unsupported" in result.output
