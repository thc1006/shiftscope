"""DRA networking migration analyzer — Device Plugin → DRA.

Analyzes NetworkIntent JSON for DRA migration readiness, alpha feature risks,
and legacy bridge requirements.
"""

from __future__ import annotations

from typing import Any

from analyzers.dra_network.parser import load_intent
from analyzers.dra_network.rules import build_rules

from shiftscope.core.analyzer import Analyzer
from shiftscope.core.models import Report
from shiftscope.core.rule import Rule


class DRANetworkAnalyzer(Analyzer):
    """Analyzes NetworkIntent JSON for DRA migration readiness."""

    name = "dra-network"
    version = "0.1.0"
    description = "Device Plugin → DRA networking migration intelligence"

    def __init__(self) -> None:
        self._rules = build_rules()

    def analyze(self, input_path: str, **kwargs: Any) -> Report:
        """Analyze a NetworkIntent JSON file."""
        context = load_intent(input_path)
        findings = self.run_rules(context)

        return Report(
            analyzer_name=self.name,
            analyzer_version=self.version,
            source=input_path,
            findings=findings,
            metadata={"intent_name": context["name"]},
        )

    def list_rules(self) -> list[Rule]:
        return list(self._rules)
