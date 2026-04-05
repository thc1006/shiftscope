"""Telco intent provenance analyzer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from shiftscope.analyzers.telco_intent.rules import build_rules
from shiftscope.core.analyzer import Analyzer
from shiftscope.core.models import Report
from shiftscope.core.rule import Rule


class TelcoIntentAnalyzer(Analyzer):
    """Analyzes telco intent configurations for GitOps migration readiness."""

    name = "telco-intent"
    version = "0.1.0"
    description = "Telco YANG→GitOps intent provenance analysis"

    def __init__(self) -> None:
        self._rules = build_rules()

    def analyze(self, input_path: str, **kwargs: Any) -> Report:
        data = json.loads(Path(input_path).read_text(encoding="utf-8"))
        context = {
            "service_name": data.get("service_name", ""),
            "operator": data.get("operator", ""),
            "region": data.get("region", ""),
            "dnn": data.get("dnn", ""),
            "require_ipv4": data.get("require_ipv4", False),
            "latency_profile": data.get("latency_profile", ""),
            "gitops_target": data.get("notes", {}).get("gitops_target", "argocd"),
            "southbound_target": data.get("notes", {}).get("southbound_target", "sdc"),
            "has_hydration": bool(data.get("notes", {}).get("hydration")),
        }
        findings = self.run_rules(context)
        return Report(
            analyzer_name=self.name,
            analyzer_version=self.version,
            source=input_path,
            findings=findings,
            metadata={"service_name": context["service_name"], "operator": context["operator"]},
        )

    def list_rules(self) -> list[Rule]:
        return list(self._rules)
