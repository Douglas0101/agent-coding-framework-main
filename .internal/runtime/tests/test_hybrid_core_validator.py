"""Tests for Hybrid Core Validator rollout behavior."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hybrid_core_config import reset_config
from hybrid_core_validator import HybridCoreValidator


def _base_1x_output() -> dict:
    return {
        "execution_profile": "default_1x",
        "scope_classification": "tier_1_universal",
        "summary": "Implement the requested change.",
        "code_changes": [{"file": "app.py", "action": "modify"}],
        "compliance_notes": [{"dimension": "testing", "status": "pass"}],
        "tests": ["pytest"],
        "risks": ["None"],
    }


class TestHybridCoreValidatorRollout:
    def test_rollout_disabled_forces_default_1x(self, monkeypatch):
        monkeypatch.delenv("OPENCODE_HYBRID_CORE", raising=False)
        reset_config()

        validator = HybridCoreValidator(enable_observability=False)
        result = validator.validate(
            code_output=_base_1x_output(),
            task="Range minimum query with updates, n=200000",
        )

        assert result.profile == "default_1x"
        assert result.tier == "tier_1_universal"
        assert result.passed

    def test_rollout_enabled_keeps_2x_requirements(self, monkeypatch):
        monkeypatch.setenv("OPENCODE_HYBRID_CORE", "enabled")
        reset_config()

        validator = HybridCoreValidator(enable_observability=False)
        result = validator.validate(
            code_output=_base_1x_output(),
            task="Range minimum query with updates, n=200000",
        )

        assert result.profile == "performance_2x"
        assert result.tier == "tier_2_algorithmic"
        assert not result.passed
        assert any(
            "Missing required fields" in reason for reason in result.rejection_reasons
        )
