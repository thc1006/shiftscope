"""Tests for eval harness."""

from __future__ import annotations

from shiftscope.core.models import Report
from shiftscope.eval.harness import EvalCase, EvalHarness
from tests.stubs import StubAnalyzer


class TestEvalCase:
    def test_eval_case_creation(self):
        case = EvalCase(name="basic", input_path="/tmp/test.yaml", golden_path="/tmp/golden.json")
        assert case.name == "basic"


class TestEvalHarness:
    def test_run_single_case_pass(self, tmp_path):
        analyzer = StubAnalyzer()
        input_file = tmp_path / "input.yaml"
        input_file.write_text("apiVersion: v1\nkind: ConfigMap\n")

        expected = analyzer.analyze(str(input_file))
        golden_file = tmp_path / "golden.json"
        golden_file.write_text(expected.model_dump_json(indent=2))

        case = EvalCase(name="basic", input_path=str(input_file), golden_path=str(golden_file))
        harness = EvalHarness(analyzer=analyzer)
        result = harness.run_case(case)
        assert result.passed is True
        assert result.case_name == "basic"

    def test_run_single_case_fail(self, tmp_path):
        analyzer = StubAnalyzer()
        input_file = tmp_path / "input.yaml"
        input_file.write_text("apiVersion: v1\nkind: ConfigMap\n")

        wrong_report = Report(
            analyzer_name="wrong", analyzer_version="0.0.0", source="wrong", findings=[]
        )
        golden_file = tmp_path / "golden.json"
        golden_file.write_text(wrong_report.model_dump_json(indent=2))

        case = EvalCase(name="mismatch", input_path=str(input_file), golden_path=str(golden_file))
        harness = EvalHarness(analyzer=analyzer)
        result = harness.run_case(case)
        assert result.passed is False
        assert result.diff is not None
        assert len(result.diff) > 0

    def test_run_all_cases(self, tmp_path):
        analyzer = StubAnalyzer()
        cases = []
        for i in range(3):
            input_file = tmp_path / f"input_{i}.yaml"
            input_file.write_text(f"# case {i}\n")
            expected = analyzer.analyze(str(input_file))
            golden_file = tmp_path / f"golden_{i}.json"
            golden_file.write_text(expected.model_dump_json(indent=2))
            cases.append(
                EvalCase(name=f"case-{i}", input_path=str(input_file), golden_path=str(golden_file))
            )

        harness = EvalHarness(analyzer=analyzer)
        results = harness.run_all(cases)
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_update_golden(self, tmp_path):
        analyzer = StubAnalyzer()
        input_file = tmp_path / "input.yaml"
        input_file.write_text("test content\n")
        golden_file = tmp_path / "golden.json"
        golden_file.write_text("{}")

        case = EvalCase(
            name="update-test", input_path=str(input_file), golden_path=str(golden_file)
        )
        harness = EvalHarness(analyzer=analyzer)
        harness.update_golden(case)

        result = harness.run_case(case)
        assert result.passed is True

    def test_run_case_golden_not_found(self, tmp_path):
        """Golden file doesn't exist — should raise FileNotFoundError."""
        analyzer = StubAnalyzer()
        input_file = tmp_path / "input.yaml"
        input_file.write_text("test\n")

        case = EvalCase(
            name="missing", input_path=str(input_file), golden_path=str(tmp_path / "nope.json")
        )
        harness = EvalHarness(analyzer=analyzer)
        import pytest

        with pytest.raises(FileNotFoundError):
            harness.run_case(case)
