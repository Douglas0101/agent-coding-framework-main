"""Tests for Profile Activator runtime."""

from __future__ import annotations

from pathlib import Path

import pytest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from profile_activator import ProfileActivator, ActiveProfile

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SPEC_PATH = REPO_ROOT / ".internal" / "specs" / "core" / "execution-profiles.yaml"
ADAPTERS_DIR = REPO_ROOT / ".internal" / "modes" / "autocoder" / "adapters"


@pytest.fixture
def activator():
    return ProfileActivator(spec_path=SPEC_PATH, adapters_dir=ADAPTERS_DIR)


class TestProfileActivatorBasics:
    def test_spec_file_exists(self):
        assert SPEC_PATH.exists()

    def test_adapters_dir_exists(self):
        assert ADAPTERS_DIR.exists()

    def test_returns_active_profile(self, activator):
        result = activator.activate("tier_1_universal")
        assert isinstance(result, ActiveProfile)

    def test_unknown_tier_raises(self, activator):
        with pytest.raises(ValueError, match="Unknown tier"):
            activator.activate("tier_99")


class TestTier1Activation:
    def test_tier_1_profile(self, activator):
        result = activator.activate("tier_1_universal")
        assert result.profile == "default_1x"
        assert result.tier == "tier_1_universal"

    def test_tier_1_quality_threshold(self, activator):
        result = activator.activate("tier_1_universal")
        assert result.quality_threshold <= 0.85

    def test_tier_1_early_exit(self, activator):
        result = activator.activate("tier_1_universal")
        assert result.early_exit is True

    def test_tier_1_contracts_loaded(self, activator):
        result = activator.activate("tier_1_universal")
        assert len(result.active_contracts) > 0
        assert any("universal-quality" in c for c in result.active_contracts)

    def test_tier_1_no_noe_contracts(self, activator):
        result = activator.activate("tier_1_universal")
        assert not any("algorithmic-frontier" in c for c in result.active_contracts)

    def test_tier_1_is_1x(self, activator):
        result = activator.activate("tier_1_universal")
        assert result.is_1x()
        assert not result.is_2x()


class TestTier2Activation:
    def test_tier_2_profile(self, activator):
        result = activator.activate("tier_2_algorithmic")
        assert result.profile == "performance_2x"
        assert result.tier == "tier_2_algorithmic"

    def test_tier_2_quality_threshold(self, activator):
        result = activator.activate("tier_2_algorithmic")
        assert result.quality_threshold >= 0.90

    def test_tier_2_early_exit(self, activator):
        result = activator.activate("tier_2_algorithmic")
        assert result.early_exit is False

    def test_tier_2_noe_contracts(self, activator):
        result = activator.activate("tier_2_algorithmic")
        assert any("algorithmic-frontier" in c for c in result.active_contracts)
        assert any("ioi-gold-compiler" in c for c in result.active_contracts)

    def test_tier_2_is_2x(self, activator):
        result = activator.activate("tier_2_algorithmic")
        assert result.is_2x()
        assert not result.is_1x()

    def test_tier_2_required_artifacts(self, activator):
        result = activator.activate("tier_2_algorithmic")
        assert "algorithm_selection_rationale" in result.required_artifacts
        assert "complexity_certificate" in result.required_artifacts

    def test_tier_2_instructions_loaded(self, activator):
        result = activator.activate("tier_2_algorithmic")
        assert len(result.instructions) > 0
        assert "NOU" in result.instructions


class TestTier3Activation:
    def test_tier_3_profile(self, activator):
        result = activator.activate("tier_3_competitive")
        assert result.profile == "performance_2x"
        assert result.tier == "tier_3_competitive"

    def test_tier_3_quality_threshold(self, activator):
        result = activator.activate("tier_3_competitive")
        assert result.quality_threshold >= 0.90

    def test_tier_3_noe_contracts(self, activator):
        result = activator.activate("tier_3_competitive")
        assert any("algorithmic-frontier" in c for c in result.active_contracts)
        assert any("frontier-algorithmic-core" in c for c in result.active_contracts)

    def test_tier_3_is_2x(self, activator):
        result = activator.activate("tier_3_competitive")
        assert result.is_2x()


class TestValidation:
    def test_no_violations_tier_1(self, activator):
        result = activator.activate("tier_1_universal")
        violations = activator.validate_activation(result)
        assert len(violations) == 0

    def test_no_violations_tier_2(self, activator):
        result = activator.activate("tier_2_algorithmic")
        violations = activator.validate_activation(result)
        assert len(violations) == 0

    def test_no_violations_tier_3(self, activator):
        result = activator.activate("tier_3_competitive")
        violations = activator.validate_activation(result)
        assert len(violations) == 0

    def test_violation_on_manual_bad_profile(self, activator):
        profile = ActiveProfile(
            profile="performance_2x",
            tier="tier_2_algorithmic",
            quality_threshold=0.50,
            active_contracts=["some-contract"],
        )
        violations = activator.validate_activation(profile)
        assert any("quality_threshold" in v for v in violations)

    def test_violation_on_1x_high_threshold(self, activator):
        profile = ActiveProfile(
            profile="default_1x",
            tier="tier_1_universal",
            quality_threshold=0.95,
            active_contracts=["some-contract"],
        )
        violations = activator.validate_activation(profile)
        assert any("quality_threshold" in v for v in violations)

    def test_violation_on_empty_contracts(self, activator):
        profile = ActiveProfile(
            profile="default_1x",
            tier="tier_1_universal",
            active_contracts=[],
        )
        violations = activator.validate_activation(profile)
        assert any("No contracts" in v for v in violations)


class TestOutputSchema:
    def test_tier_1_output_fields(self, activator):
        result = activator.activate("tier_1_universal")
        assert "execution_profile" in result.output_schema
        assert "compliance_notes" in result.output_schema

    def test_tier_2_output_fields(self, activator):
        result = activator.activate("tier_2_algorithmic")
        assert "algorithm_selection_rationale" in result.output_schema
        assert "complexity_certificate" in result.output_schema
        assert "stress_test_plan" in result.output_schema

    def test_tier_3_output_fields(self, activator):
        result = activator.activate("tier_3_competitive")
        assert "algorithm_selection_rationale" in result.output_schema
        assert "complexity_certificate" in result.output_schema


class TestMetadata:
    def test_available_profiles(self, activator):
        profiles = activator.get_available_profiles()
        assert "default_1x" in profiles
        assert "performance_2x" in profiles

    def test_precedence_rules(self, activator):
        rules = activator.get_precedence_rules()
        assert len(rules) >= 4
        assert any("Security" in r for r in rules)
        assert any("NOU" in r for r in rules)

    def test_activation_policy(self, activator):
        policy = activator.get_activation_policy()
        assert policy["default_profile"] == "default_1x"
        assert policy["no_opt_out"]["from_universal_core"] is True
