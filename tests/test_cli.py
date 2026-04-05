"""Tests for CLI scaffolding."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from shiftscope.cli.app import build_cli
from shiftscope.core.analyzer import AnalyzerRegistry

from tests.stubs import StubAnalyzer


class TestBuildCLI:
    def test_build_cli_returns_callable(self, registry_with_stub):
        app = build_cli(registry_with_stub)
        assert app is not None

    def test_analyze_command_json_output(self, tmp_path, registry_with_stub):
        app = build_cli(registry_with_stub)
        input_file = tmp_path / "test.yaml"
        input_file.write_text("apiVersion: v1\n")

        runner = CliRunner()
        result = runner.invoke(app, ["analyze", "stub-analyzer", str(input_file), "--output", "json"])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["analyzer_name"] == "stub-analyzer"
        assert len(parsed["findings"]) == 1

    def test_analyze_command_markdown_output(self, tmp_path, registry_with_stub):
        app = build_cli(registry_with_stub)
        input_file = tmp_path / "test.yaml"
        input_file.write_text("apiVersion: v1\n")

        runner = CliRunner()
        result = runner.invoke(app, ["analyze", "stub-analyzer", str(input_file), "--output", "markdown"])
        assert result.exit_code == 0
        assert "Migration Report" in result.output
        assert "[INFO]" in result.output

    def test_analyze_unknown_analyzer(self):
        registry = AnalyzerRegistry()
        app = build_cli(registry)

        runner = CliRunner()
        result = runner.invoke(app, ["analyze", "nonexistent", "/tmp/test.yaml"])
        assert result.exit_code != 0

    def test_analyze_invalid_output_format(self, tmp_path, registry_with_stub):
        app = build_cli(registry_with_stub)
        input_file = tmp_path / "test.yaml"
        input_file.write_text("apiVersion: v1\n")

        runner = CliRunner()
        result = runner.invoke(app, ["analyze", "stub-analyzer", str(input_file), "--output", "xml"])
        assert result.exit_code != 0
        assert "unsupported output format" in result.output

    def test_list_analyzers_command(self, registry_with_stub):
        app = build_cli(registry_with_stub)
        runner = CliRunner()
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "stub-analyzer" in result.output

    def test_list_analyzers_empty(self):
        registry = AnalyzerRegistry()
        app = build_cli(registry)
        runner = CliRunner()
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "No analyzers registered" in result.output
