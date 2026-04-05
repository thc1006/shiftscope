"""Tests for Rule ABC."""

from __future__ import annotations

import pytest

from shiftscope.core.models import Finding, Severity
from shiftscope.core.rule import Rule


class AnnotationCheckRule(Rule):
    """Concrete rule for testing: checks if a specific annotation exists."""

    rule_id = "test-annotation-check"
    severity = Severity.WARNING

    def __init__(self, target_annotation: str):
        self.target_annotation = target_annotation

    def applies_to(self, context: dict) -> bool:
        return "annotations" in context

    def evaluate(self, context: dict) -> Finding | None:
        annotations = context.get("annotations", {})
        if self.target_annotation in annotations:
            return Finding(
                rule_id=self.rule_id,
                severity=self.severity,
                title=f"Annotation '{self.target_annotation}' detected",
                detail="This annotation requires manual review during migration.",
                evidence=f"annotations['{self.target_annotation}'] = '{annotations[self.target_annotation]}'",
                recommendation="Review Gateway API equivalent.",
            )
        return None


class TestRuleABC:
    def test_cannot_instantiate_abstract_rule(self):
        with pytest.raises(TypeError):
            Rule()

    def test_concrete_rule_has_required_attributes(self):
        rule = AnnotationCheckRule("nginx.ingress.kubernetes.io/enable-cors")
        assert rule.rule_id == "test-annotation-check"
        assert rule.severity == Severity.WARNING

    def test_applies_to_returns_true_when_relevant(self):
        rule = AnnotationCheckRule("nginx.ingress.kubernetes.io/enable-cors")
        ctx = {"annotations": {"nginx.ingress.kubernetes.io/enable-cors": "true"}}
        assert rule.applies_to(ctx) is True

    def test_applies_to_returns_false_when_irrelevant(self):
        rule = AnnotationCheckRule("nginx.ingress.kubernetes.io/enable-cors")
        ctx = {"name": "test", "namespace": "default"}
        assert rule.applies_to(ctx) is False

    def test_evaluate_returns_finding_when_match(self):
        rule = AnnotationCheckRule("nginx.ingress.kubernetes.io/enable-cors")
        ctx = {"annotations": {"nginx.ingress.kubernetes.io/enable-cors": "true"}}
        finding = rule.evaluate(ctx)
        assert finding is not None
        assert isinstance(finding, Finding)
        assert finding.rule_id == "test-annotation-check"
        assert finding.severity == Severity.WARNING

    def test_evaluate_returns_none_when_no_match(self):
        rule = AnnotationCheckRule("nginx.ingress.kubernetes.io/enable-cors")
        ctx = {"annotations": {"other-annotation": "value"}}
        assert rule.evaluate(ctx) is None

    def test_rule_with_parameters(self):
        rule1 = AnnotationCheckRule("annotation-a")
        rule2 = AnnotationCheckRule("annotation-b")
        assert rule1.target_annotation != rule2.target_annotation

    def test_rule_short_circuit_pattern(self):
        rule = AnnotationCheckRule("nginx.ingress.kubernetes.io/enable-cors")
        ctx = {"name": "test"}
        if rule.applies_to(ctx):
            finding = rule.evaluate(ctx)
        else:
            finding = None
        assert finding is None

    def test_subclass_missing_rule_id_raises(self):
        """CR-35: __init_subclass__ should catch missing class attributes."""
        with pytest.raises(TypeError, match="must define class attribute 'rule_id'"):

            class BadRule(Rule):
                severity = Severity.INFO

                def applies_to(self, context: dict) -> bool:
                    return True

                def evaluate(self, context: dict) -> Finding | None:
                    return None

    def test_subclass_missing_severity_raises(self):
        with pytest.raises(TypeError, match="must define class attribute 'severity'"):

            class BadRule(Rule):
                rule_id = "bad"

                def applies_to(self, context: dict) -> bool:
                    return True

                def evaluate(self, context: dict) -> Finding | None:
                    return None
