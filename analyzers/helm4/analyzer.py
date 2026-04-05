"""Helm 4 / Charts v3 readiness analyzer."""

from __future__ import annotations

from typing import Any

from shiftscope.core.analyzer import Analyzer
from shiftscope.core.models import Report
from shiftscope.core.rule import Rule

from analyzers.helm4.parser import parse_chart
from analyzers.helm4.rules import build_rules


class Helm4ReadinessAnalyzer(Analyzer):
    """Analyzes Helm charts for Helm 4 / Charts v3 migration readiness."""

    name = "helm4-readiness"
    version = "0.1.0"
    description = "Helm 3 → Helm 4 / Charts v3 readiness analysis"

    def __init__(self) -> None:
        self._rules = build_rules()

    def analyze(self, input_path: str, **kwargs: Any) -> Report:
        """Analyze a Helm chart directory."""
        context = parse_chart(input_path)
        findings = self.run_rules(context)

        return Report(
            analyzer_name=self.name,
            analyzer_version=self.version,
            source=input_path,
            findings=findings,
            metadata={
                "chart_name": context["name"],
                "chart_api_version": context["api_version"],
            },
        )

    def list_rules(self) -> list[Rule]:
        return list(self._rules)
