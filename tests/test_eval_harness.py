"""Tests for eval harness — TDD RED phase."""

from __future__ import annotations

import json

from shiftscope.core.analyzer import Analyzer
from shiftscope.core.models import Finding, Report, Severity
from shiftscope.core.rule import Rule
from shiftscope.eval.harness import EvalCase, EvalHarness, EvalResult


# --- Stub analyzer for testing ---

class StubRule(Rule):
    rule_id = "stub-always"
    severity = Severity.INFO

    def applies_to(self, context: dict) -> bool:
        return True

    def evaluate(self, context: dict) -> Finding | None:
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            title="Stub finding",
            detail="Always fires.",
            evidence="N/A",
            recommendation="None.",
        )


class StubEvalAnalyzer(Analyzer):
    name = "stub-eval"
    version = "0.1.0"
    description = "Stub for eval testing."

    def __init__(self):
        self._rules = [StubRule()]

    def analyze(self, input_path: str, **kwargs) -> Report:
        findings = self.run_rules({"input_path": input_path})
        return Report(
            analyzer_name=self.name,
            analyzer_version=self.version,
            source=input_path,
            findings=findings,
        )

    def list_rules(self) -> list[Rule]:
        return list(self._rules)


# --- Tests ---

class TestEvalCase:
    def test_eval_case_creation(self):
        case = EvalCase(name="basic", input_path="/tmp/test.yaml", golden_path="/tmp/golden.json")
        assert case.name == "basic"


class TestEvalHarness:
    def test_run_single_case_pass(self, tmp_path):
        analyzer = StubEvalAnalyzer()

        # Create a dummy input file
        input_file = tmp_path / "input.yaml"
        input_file.write_text("apiVersion: v1\nkind: ConfigMap\n")

        # Run analyzer to get expected output, save as golden
        expected = analyzer.analyze(str(input_file))
        golden_file = tmp_path / "golden.json"
        golden_file.write_text(expected.model_dump_json(indent=2))

        case = EvalCase(
            name="basic",
            input_path=str(input_file),
            golden_path=str(golden_file),
        )

        harness = EvalHarness(analyzer=analyzer)
        result = harness.run_case(case)
        assert result.passed is True
        assert result.case_name == "basic"

    def test_run_single_case_fail(self, tmp_path):
        analyzer = StubEvalAnalyzer()

        input_file = tmp_path / "input.yaml"
        input_file.write_text("apiVersion: v1\nkind: ConfigMap\n")

        # Write a golden file that doesn't match
        golden_file = tmp_path / "golden.json"
        wrong_report = Report(
            analyzer_name="wrong",
            analyzer_version="0.0.0",
            source="wrong",
            findings=[],
        )
        golden_file.write_text(wrong_report.model_dump_json(indent=2))

        case = EvalCase(
            name="mismatch",
            input_path=str(input_file),
            golden_path=str(golden_file),
        )

        harness = EvalHarness(analyzer=analyzer)
        result = harness.run_case(case)
        assert result.passed is False
        assert result.diff is not None

    def test_run_all_cases(self, tmp_path):
        analyzer = StubEvalAnalyzer()

        cases = []
        for i in range(3):
            input_file = tmp_path / f"input_{i}.yaml"
            input_file.write_text(f"# case {i}\n")
            expected = analyzer.analyze(str(input_file))
            golden_file = tmp_path / f"golden_{i}.json"
            golden_file.write_text(expected.model_dump_json(indent=2))
            cases.append(EvalCase(
                name=f"case-{i}",
                input_path=str(input_file),
                golden_path=str(golden_file),
            ))

        harness = EvalHarness(analyzer=analyzer)
        results = harness.run_all(cases)
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_update_golden(self, tmp_path):
        analyzer = StubEvalAnalyzer()

        input_file = tmp_path / "input.yaml"
        input_file.write_text("test content\n")

        golden_file = tmp_path / "golden.json"
        golden_file.write_text("{}")  # Stale golden

        case = EvalCase(
            name="update-test",
            input_path=str(input_file),
            golden_path=str(golden_file),
        )

        harness = EvalHarness(analyzer=analyzer)
        harness.update_golden(case)

        # Golden should now match current output
        result = harness.run_case(case)
        assert result.passed is True
