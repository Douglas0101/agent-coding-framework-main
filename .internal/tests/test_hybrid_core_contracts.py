"""Tests for Hybrid Core contracts — execution profiles, NOU, NOE, scope detection."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SPECS_CORE = REPO_ROOT / ".internal" / "specs" / "core"

EXECUTION_PROFILES = SPECS_CORE / "execution-profiles.yaml"
UNIVERSAL_QUALITY = SPECS_CORE / "universal-quality-contract.yaml"
ALGORITHMIC_FRONTIER = SPECS_CORE / "algorithmic-frontier-contract.yaml"
SCOPE_DETECTION = SPECS_CORE / "scope-detection-engine.yaml"

ADAPTERS_DIR = REPO_ROOT / ".internal" / "modes" / "autocoder" / "adapters"


def _load_yaml(path: Path) -> dict:
    assert path.exists(), f"File missing: {path}"
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise AssertionError(f"Invalid YAML in {path}: {exc}") from exc


# ── Execution Profiles ──────────────────────────────────────────


class TestExecutionProfiles:
    def test_file_exists(self):
        assert EXECUTION_PROFILES.exists()

    def test_parseable_yaml(self):
        data = _load_yaml(EXECUTION_PROFILES)
        assert data is not None

    def test_has_profiles_section(self):
        data = _load_yaml(EXECUTION_PROFILES)
        assert "profiles" in data

    def test_default_1x_profile(self):
        data = _load_yaml(EXECUTION_PROFILES)
        profile = data["profiles"]["default_1x"]
        assert "universal_quality_core" in profile["activates"]
        assert profile["early_exit"] is True
        assert profile["quality_threshold"] <= 0.85

    def test_performance_2x_profile(self):
        data = _load_yaml(EXECUTION_PROFILES)
        profile = data["profiles"]["performance_2x"]
        assert "universal_quality_core" in profile["activates"]
        assert "algorithmic_frontier_core" in profile["activates"]
        assert profile["early_exit"] is False
        assert profile["quality_threshold"] >= 0.90

    def test_precedence_rules(self):
        data = _load_yaml(EXECUTION_PROFILES)
        assert "precedence" in data
        assert "rules" in data["precedence"]
        assert len(data["precedence"]["rules"]) >= 4

    def test_activation_policy(self):
        data = _load_yaml(EXECUTION_PROFILES)
        policy = data["activation_policy"]
        assert policy["default_profile"] == "default_1x"
        assert policy["no_opt_out"]["from_universal_core"] is True


# ── Universal Quality Contract (NOU) ────────────────────────────


class TestUniversalQualityContract:
    def test_file_exists(self):
        assert UNIVERSAL_QUALITY.exists()

    def test_parseable_yaml(self):
        data = _load_yaml(UNIVERSAL_QUALITY)
        assert data is not None

    def test_mandatory_flag(self):
        data = _load_yaml(UNIVERSAL_QUALITY)
        assert data["mandatory"] is True

    def test_has_dimensions(self):
        data = _load_yaml(UNIVERSAL_QUALITY)
        assert "dimensions" in data
        assert len(data["dimensions"]) >= 8

    def test_required_dimensions_present(self):
        data = _load_yaml(UNIVERSAL_QUALITY)
        dim_ids = {d["id"] for d in data["dimensions"]}
        required = {
            "type_safety",
            "null_safety",
            "architecture_invariants",
            "code_clarity",
            "security",
            "error_handling",
            "testing",
            "project_conventions",
            "change_justification",
        }
        assert required.issubset(dim_ids), f"Missing dimensions: {required - dim_ids}"

    def test_enforcement_fail_on(self):
        data = _load_yaml(UNIVERSAL_QUALITY)
        fail_on = data["enforcement"]["fail_on"]
        assert "missing_typing" in fail_on
        assert "missing_error_strategy" in fail_on
        assert "missing_tests_for_business_logic" in fail_on


# ── Algorithmic Frontier Contract (NOE) ─────────────────────────


class TestAlgorithmicFrontierContract:
    def test_file_exists(self):
        assert ALGORITHMIC_FRONTIER.exists()

    def test_parseable_yaml(self):
        data = _load_yaml(ALGORITHMIC_FRONTIER)
        assert data is not None

    def test_mandatory_when(self):
        data = _load_yaml(ALGORITHMIC_FRONTIER)
        assert "mandatory_when" in data
        assert any("performance_2x" in str(m) for m in data["mandatory_when"])

    def test_has_requires(self):
        data = _load_yaml(ALGORITHMIC_FRONTIER)
        req_ids = {r["id"] for r in data["requires"]}
        required = {
            "algorithm_selection_rationale",
            "complexity_certificate",
            "invariant_documentation",
            "edge_case_analysis",
            "stress_test_plan",
            "memory_bound_estimate",
        }
        assert required.issubset(req_ids), f"Missing requirements: {required - req_ids}"

    def test_frontier_tiers(self):
        data = _load_yaml(ALGORITHMIC_FRONTIER)
        tiers = data["frontier_tiers"]
        assert "tier_2_algorithmic" in tiers
        assert "tier_3_competitive" in tiers

    def test_tier_2_techniques(self):
        data = _load_yaml(ALGORITHMIC_FRONTIER)
        tiers = data["frontier_tiers"]
        techniques = tiers["tier_2_algorithmic"]["techniques"]
        assert len(techniques) >= 10

    def test_tier_3_techniques(self):
        data = _load_yaml(ALGORITHMIC_FRONTIER)
        tiers = data["frontier_tiers"]
        techniques = tiers["tier_3_competitive"]["techniques"]
        assert len(techniques) >= 5

    def test_precedence_nou_over_noe(self):
        data = _load_yaml(ALGORITHMIC_FRONTIER)
        assert "precedence" in data


# ── Scope Detection Engine ──────────────────────────────────────


class TestScopeDetectionEngine:
    def test_file_exists(self):
        assert SCOPE_DETECTION.exists()

    def test_parseable_yaml(self):
        data = _load_yaml(SCOPE_DETECTION)
        assert data is not None

    def test_has_triggers(self):
        data = _load_yaml(SCOPE_DETECTION)
        assert "triggers" in data
        triggers = data["triggers"]
        assert "complexity_indicators" in triggers
        assert "constraints" in triggers

    def test_escalation_thresholds(self):
        data = _load_yaml(SCOPE_DETECTION)
        constraints = data["triggers"]["constraints"]
        assert constraints["max_n_for_escalation"] >= 100000
        assert constraints["max_q_for_escalation"] >= 100000

    def test_classification_tiers(self):
        data = _load_yaml(SCOPE_DETECTION)
        classification = data["classification"]
        assert "tier_1_universal" in classification
        assert "tier_2_algorithmic" in classification
        assert "tier_3_competitive" in classification

    def test_tier_1_maps_to_1x(self):
        data = _load_yaml(SCOPE_DETECTION)
        assert data["classification"]["tier_1_universal"]["profile"] == "default_1x"

    def test_tier_2_maps_to_2x(self):
        data = _load_yaml(SCOPE_DETECTION)
        assert (
            data["classification"]["tier_2_algorithmic"]["profile"] == "performance_2x"
        )

    def test_tier_3_maps_to_2x(self):
        data = _load_yaml(SCOPE_DETECTION)
        assert (
            data["classification"]["tier_3_competitive"]["profile"] == "performance_2x"
        )

    def test_anti_false_positive_rules(self):
        data = _load_yaml(SCOPE_DETECTION)
        assert "anti_false_positive" in data
        assert len(data["anti_false_positive"]["rules"]) >= 3

    def test_output_fields(self):
        data = _load_yaml(SCOPE_DETECTION)
        output = data["output"]
        assert "required_fields" in output


# ── Autocoder Adapters ──────────────────────────────────────────


class TestAutocoderAdapters:
    def test_default_1x_adapter_exists(self):
        assert (ADAPTERS_DIR / "default-1x.yaml").exists()

    def test_performance_2x_tier_2_adapter_exists(self):
        assert (ADAPTERS_DIR / "performance-2x-tier-2.yaml").exists()

    def test_performance_2x_tier_3_adapter_exists(self):
        assert (ADAPTERS_DIR / "performance-2x-tier-3.yaml").exists()

    def test_default_1x_profile_value(self):
        data = _load_yaml(ADAPTERS_DIR / "default-1x.yaml")
        assert data["profile"] == "default_1x"
        assert data["tier"] == "tier_1_universal"

    def test_tier_2_profile_value(self):
        data = _load_yaml(ADAPTERS_DIR / "performance-2x-tier-2.yaml")
        assert data["profile"] == "performance_2x"
        assert data["tier"] == "tier_2_algorithmic"

    def test_tier_3_profile_value(self):
        data = _load_yaml(ADAPTERS_DIR / "performance-2x-tier-3.yaml")
        assert data["profile"] == "performance_2x"
        assert data["tier"] == "tier_3_competitive"

    def test_adapters_reference_specs_core_paths(self):
        """All adapters must reference .internal/specs/core/ not .internal/core/"""
        for adapter_file in ADAPTERS_DIR.glob("*.yaml"):
            content = adapter_file.read_text(encoding="utf-8")
            assert ".internal/core/" not in content, (
                f"{adapter_file.name} references deprecated .internal/core/ — "
                f"use .internal/specs/core/"
            )

    def test_tier_2_context_includes_noe(self):
        data = _load_yaml(ADAPTERS_DIR / "performance-2x-tier-2.yaml")
        contracts = data["context_injection"]["contracts"]
        assert any("algorithmic-frontier" in c for c in contracts)

    def test_tier_3_context_includes_noe(self):
        data = _load_yaml(ADAPTERS_DIR / "performance-2x-tier-3.yaml")
        contracts = data["context_injection"]["contracts"]
        assert any("algorithmic-frontier" in c for c in contracts)


# ── Cross-Contract Consistency ──────────────────────────────────


class TestCrossContractConsistency:
    def test_execution_profiles_match_scope_detection(self):
        profiles = _load_yaml(EXECUTION_PROFILES)
        scope = _load_yaml(SCOPE_DETECTION)
        tier1_profile = scope["classification"]["tier_1_universal"]["profile"]
        tier2_profile = scope["classification"]["tier_2_algorithmic"]["profile"]
        assert tier1_profile in profiles["profiles"]
        assert tier2_profile in profiles["profiles"]

    def test_noe_references_nou(self):
        noe = _load_yaml(ALGORITHMIC_FRONTIER)
        assert "precedence" in noe
        prec = noe["precedence"]
        text = (
            str(prec.get("description", ""))
            + " "
            + " ".join(str(r) for r in prec.get("rules", []))
        )
        assert "NOU" in text or "Universal" in text

    def test_adapter_output_schemas_match_profiles(self):
        for adapter_file in ADAPTERS_DIR.glob("*.yaml"):
            data = _load_yaml(adapter_file)
            schema_fields = [
                f["name"] for f in data["output_schema"]["required_fields"]
            ]
            assert "execution_profile" in schema_fields
            assert data["execution_profile"] if "execution_profile" in data else True
