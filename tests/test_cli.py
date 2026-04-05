"""Tests for CLI scaffolding — TDD RED phase."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from shiftscope.cli.app import build_cli
from shiftscope.core.analyzer import Analyzer, AnalyzerRegistry
from shiftscope.core.models import Finding, Report, Severity
from shiftscope.core.rule import Rule


# --- Stub analyzer ---

class StubCLIRule(Rule):
    rule_id = "cli-test-rule"
    severity = Severity.INFO

    def applies_to(self, context: dict) -> bool:
        return True

    def evaluate(self, context: dict) -> Finding | None:
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title="CLI test finding",
            detail="Found by CLI test.",
            evidence="test",
            recommendation="None.",
        )


class StubCLIAnalyzer(Analyzer):
    name = "cli-stub"
    version = "0.1.0"
    description = "Stub for CLI testing."

    def __init__(self):
        self._rules = [StubCLIRule()]

    def analyze(self, input_path: str, **kwargs) -> Report:
        findings = self.run_rules({"input_path": input_path})
        return Report(
            analyzer_name=self.name,
            analyzer_version=self.version,
            source=input_path,
            findings=findings,
            metadata=kwargs,
        )

    def list_rules(self) -> list[Rule]:
        return list(self._rules)


# --- Tests ---

class TestBuildCLI:
    def test_build_cli_returns_callable(self):
        registry = AnalyzerRegistry()
        registry.register(StubCLIAnalyzer())
        app = build_cli(registry)
        assert app is not None

    def test_analyze_command_json_output(self, tmp_path, capsys):
        registry = AnalyzerRegistry()
        registry.register(StubCLIAnalyzer())
        app = build_cli(registry)

        input_file = tmp_path / "test.yaml"
        input_file.write_text("apiVersion: v1\n")

        runner = CliRunner()
        result = runner.invoke(app, ["analyze", "cli-stub", str(input_file), "--output", "json"])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["analyzer_name"] == "cli-stub"
        assert len(parsed["findings"]) == 1

    def test_analyze_command_markdown_output(self, tmp_path):
        registry = AnalyzerRegistry()
        registry.register(StubCLIAnalyzer())
        app = build_cli(registry)

        input_file = tmp_path / "test.yaml"
        input_file.write_text("apiVersion: v1\n")

        runner = CliRunner()
        result = runner.invoke(app, ["analyze", "cli-stub", str(input_file), "--output", "markdown"])
        assert result.exit_code == 0
        assert "Migration Report" in result.output

    def test_analyze_unknown_analyzer(self):
        registry = AnalyzerRegistry()
        app = build_cli(registry)

        runner = CliRunner()
        result = runner.invoke(app, ["analyze", "nonexistent", "/tmp/test.yaml"])
        assert result.exit_code != 0

    def test_list_analyzers_command(self):
        registry = AnalyzerRegistry()
        registry.register(StubCLIAnalyzer())
        app = build_cli(registry)

        runner = CliRunner()
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "cli-stub" in result.output
