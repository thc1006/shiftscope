"""Shared pytest fixtures for ShiftScope tests."""

from __future__ import annotations

import pytest

from shiftscope.core.analyzer import AnalyzerRegistry
from tests.stubs import StubAnalyzer


@pytest.fixture
def stub_analyzer() -> StubAnalyzer:
    return StubAnalyzer()


@pytest.fixture
def registry_with_stub() -> AnalyzerRegistry:
    reg = AnalyzerRegistry()
    reg.register(StubAnalyzer())
    return reg
