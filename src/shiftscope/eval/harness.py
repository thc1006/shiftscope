"""Eval harness — golden-file testing for ShiftScope analyzers.

Provides structured evaluation: load input → run analyzer → diff against golden output.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from shiftscope.core.analyzer import Analyzer
from shiftscope.core.models import Report


@dataclass
class EvalCase:
    """A single evaluation case: input file + expected golden output."""

    name: str
    input_path: str
    golden_path: str


@dataclass
class EvalResult:
    """Result of running a single eval case."""

    case_name: str
    passed: bool
    diff: str | None = None


class EvalHarness:
    """Golden-file evaluation harness for analyzers."""

    def __init__(self, analyzer: Analyzer) -> None:
        self._analyzer = analyzer

    def run_case(self, case: EvalCase) -> EvalResult:
        """Run analyzer on input, compare output against golden file."""
        actual_report = self._analyzer.analyze(case.input_path)
        # Use same serialization path as update_golden() to avoid silent diffs
        actual_json = json.loads(actual_report.model_dump_json(indent=2))

        golden_path = Path(case.golden_path)
        golden_json = json.loads(golden_path.read_text())

        if actual_json == golden_json:
            return EvalResult(case_name=case.name, passed=True)

        diff = _json_diff(golden_json, actual_json)
        return EvalResult(case_name=case.name, passed=False, diff=diff)

    def run_all(self, cases: list[EvalCase]) -> list[EvalResult]:
        """Run all eval cases and return results."""
        return [self.run_case(case) for case in cases]

    def update_golden(self, case: EvalCase) -> None:
        """Regenerate the golden file from current analyzer output."""
        actual_report = self._analyzer.analyze(case.input_path)
        golden_path = Path(case.golden_path)
        golden_path.parent.mkdir(parents=True, exist_ok=True)
        golden_path.write_text(actual_report.model_dump_json(indent=2) + "\n")


def _json_diff(expected: dict, actual: dict) -> str:
    """Simple JSON diff for human-readable output."""
    import difflib

    expected_lines = json.dumps(expected, indent=2, sort_keys=True).splitlines(keepends=True)
    actual_lines = json.dumps(actual, indent=2, sort_keys=True).splitlines(keepends=True)
    diff = difflib.unified_diff(expected_lines, actual_lines, fromfile="golden", tofile="actual")
    return "".join(diff)
