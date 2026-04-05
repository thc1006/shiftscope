"""Rule ABC — behavioral contract for migration analysis rules.

Rules are the atomic units of analysis logic. Each rule:
- Has a unique rule_id and severity level
- Can short-circuit via applies_to() (Kyverno-inspired match pattern)
- Produces a Finding or None via evaluate()
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from shiftscope.core.models import Finding, Severity


class Rule(ABC):
    """Abstract base class for migration analysis rules.

    Subclasses must define rule_id, severity, and implement
    applies_to() and evaluate() methods.
    """

    rule_id: str
    severity: Severity

    @abstractmethod
    def applies_to(self, context: dict[str, Any]) -> bool:
        """Check if this rule is relevant to the given context.

        Use for short-circuit evaluation: if False, evaluate() is skipped.
        """

    @abstractmethod
    def evaluate(self, context: dict[str, Any]) -> Finding | None:
        """Evaluate the rule against the context.

        Returns a Finding if the rule fires, None otherwise.
        """
