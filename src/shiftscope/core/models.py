"""Core data models for ShiftScope migration intelligence.

Finding and Report are Pydantic BaseModel (not dataclasses) for:
- JSON Schema generation (MCP tool descriptions)
- Validation (catch typos like severity="critcal")
- Serialization (model_dump_json / model_validate_json)
- FastMCP native integration
"""

from __future__ import annotations

import sys

# StrEnum is native in 3.11+; shim for development on 3.10 systems.
# pyproject.toml targets >=3.12; remove shim when CI enforces that.
if sys.version_info >= (3, 11):  # noqa: UP036
    from enum import StrEnum
else:
    from enum import Enum

    class StrEnum(str, Enum):  # noqa: UP042
        pass
from typing import Any

from pydantic import BaseModel, ConfigDict


class Severity(StrEnum):
    """Severity level of a migration finding."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Finding(BaseModel):
    """Atomic unit of migration analysis output.

    Every finding is traceable to a specific rule, carries evidence,
    and includes an actionable recommendation.
    """

    model_config = ConfigDict(frozen=True)

    rule_id: str
    severity: Severity
    title: str
    detail: str
    evidence: str
    recommendation: str


class Report(BaseModel):
    """Aggregated output of an analyzer run.

    Contains all findings from a single analysis pass, plus metadata
    about the analyzer and input source.
    """

    model_config = ConfigDict(frozen=True)

    analyzer_name: str
    analyzer_version: str
    source: str
    findings: list[Finding]
    metadata: dict[str, Any] = {}
