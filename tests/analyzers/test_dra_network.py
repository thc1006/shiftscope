"""Tests for the DRA networking analyzer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shiftscope.core.models import Report, Severity

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples"
EXAMPLE_INTENT = EXAMPLES_DIR / "dra-network-intent.json"


@pytest.fixture
def analyzer():
    from analyzers.dra_network.analyzer import DRANetworkAnalyzer

    return DRANetworkAnalyzer()


# --- Parser tests ---


class TestIntentParser:
    def test_parse_example_intent(self):
        from analyzers.dra_network.parser import load_intent

        intent = load_intent(str(EXAMPLE_INTENT))
        assert intent["name"] == "demo-ai-rdma-job"
        assert intent["gpu_count"] == 4
        assert intent["requires_rdma"] is True

    def test_parse_minimal_intent(self, tmp_path):
        from analyzers.dra_network.parser import load_intent

        minimal = tmp_path / "min.json"
        minimal.write_text(json.dumps({"name": "test", "workload_kind": "Job"}))
        intent = load_intent(str(minimal))
        assert intent["name"] == "test"
        assert intent["gpu_count"] == 0
        assert intent["requires_rdma"] is False

    def test_parse_invalid_json_raises(self, tmp_path):
        from analyzers.dra_network.parser import load_intent

        bad = tmp_path / "bad.json"
        bad.write_text("not json")
        with pytest.raises(json.JSONDecodeError):
            load_intent(str(bad))


# --- Rule tests ---


class TestAlphaFeatureRules:
    def test_alpha_enabled_produces_warning(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "dra-alpha-feature-gate")
        ctx = {
            "name": "test",
            "alpha": {
                "extended_resource_mapping": True,
                "consumable_capacity": False,
                "partitionable_devices": False,
            },
        }
        finding = rule.evaluate(ctx)
        assert finding is not None
        assert finding.severity == Severity.WARNING
        assert "alpha" in finding.title.lower()

    def test_no_alpha_no_finding(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "dra-alpha-feature-gate")
        ctx = {
            "name": "test",
            "alpha": {
                "extended_resource_mapping": False,
                "consumable_capacity": False,
                "partitionable_devices": False,
            },
        }
        assert rule.evaluate(ctx) is None


class TestRDMARules:
    def test_rdma_with_high_bandwidth(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "dra-rdma-bandwidth")
        ctx = {"name": "test", "requires_rdma": True, "min_bandwidth_gbps": 200, "gpu_count": 4}
        finding = rule.evaluate(ctx)
        assert finding is not None
        assert "RDMA" in finding.title or "bandwidth" in finding.title.lower()

    def test_no_rdma_no_finding(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "dra-rdma-bandwidth")
        ctx = {"name": "test", "requires_rdma": False, "min_bandwidth_gbps": None, "gpu_count": 0}
        assert rule.evaluate(ctx) is None


class TestLegacyBridgeRules:
    def test_legacy_bridge_enabled(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "dra-legacy-bridge")
        ctx = {"name": "test", "legacy_bridge": True, "requires_rdma": True, "gpu_count": 2}
        finding = rule.evaluate(ctx)
        assert finding is not None
        assert finding.severity == Severity.INFO
        assert "legacy" in finding.title.lower() or "migration" in finding.detail.lower()

    def test_legacy_bridge_disabled(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "dra-legacy-bridge")
        ctx = {"name": "test", "legacy_bridge": False}
        assert rule.evaluate(ctx) is None


class TestTopologyRules:
    def test_topology_alignment_required(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "dra-topology-alignment")
        ctx = {"name": "test", "require_topology_alignment": True, "gpu_count": 4}
        finding = rule.evaluate(ctx)
        assert finding is not None

    def test_no_topology_no_finding(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "dra-topology-alignment")
        ctx = {"name": "test", "require_topology_alignment": False, "gpu_count": 0}
        assert rule.evaluate(ctx) is None


class TestValidationRules:
    def test_invalid_workload_kind(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "dra-invalid-workload-kind")
        ctx = {"name": "test", "workload_kind": "Deployment"}
        finding = rule.evaluate(ctx)
        assert finding is not None
        assert finding.severity == Severity.CRITICAL

    def test_valid_workload_kind(self, analyzer):
        rule = next(r for r in analyzer.list_rules() if r.rule_id == "dra-invalid-workload-kind")
        ctx = {"name": "test", "workload_kind": "Job"}
        assert rule.evaluate(ctx) is None


# --- Analyzer integration tests ---


class TestDRANetworkAnalyzer:
    def test_analyze_example_intent(self, analyzer):
        report = analyzer.analyze(str(EXAMPLE_INTENT))
        assert isinstance(report, Report)
        assert report.analyzer_name == "dra-network"
        assert len(report.findings) >= 3

    def test_analyze_finding_rule_ids(self, analyzer):
        report = analyzer.analyze(str(EXAMPLE_INTENT))
        rule_ids = {f.rule_id for f in report.findings}
        assert "dra-rdma-bandwidth" in rule_ids
        assert "dra-legacy-bridge" in rule_ids
        assert "dra-topology-alignment" in rule_ids

    def test_analyze_minimal_intent(self, analyzer, tmp_path):
        minimal = tmp_path / "min.json"
        minimal.write_text(
            json.dumps({"name": "bare", "workload_kind": "Job", "legacy_bridge": False})
        )
        report = analyzer.analyze(str(minimal))
        assert report.findings == []

    def test_list_rules_count(self, analyzer):
        rules = analyzer.list_rules()
        assert len(rules) >= 5

    def test_json_roundtrip(self, analyzer):
        report = analyzer.analyze(str(EXAMPLE_INTENT))
        restored = Report.model_validate_json(report.model_dump_json())
        assert len(restored.findings) == len(report.findings)
