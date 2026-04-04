"""Tests for Output Validator runtime."""

from __future__ import annotations

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from output_validator import (
    OutputValidator,
    ValidationResult,
    REQUIRED_1X_FIELDS,
    REQUIRED_2X_FIELDS,
)


@pytest.fixture
def validator():
    return OutputValidator()


class TestOutputValidatorBasics:
    def test_returns_validation_result(self, validator):
        result = validator.validate({}, "default_1x")
        assert isinstance(result, ValidationResult)

    def test_all_1x_fields_present(self, validator):
        output = {
            "execution_profile": "default_1x",
            "scope_classification": "tier_1_universal",
            "summary": "Test summary",
            "code_changes": ["change1"],
            "compliance_notes": ["all good"],
            "tests": ["pytest"],
            "risks": ["none"],
        }
        result = validator.validate(output, "default_1x")
        assert result.valid is True
        assert result.missing_fields == []

    def test_missing_1x_fields(self, validator):
        result = validator.validate({}, "default_1x")
        assert result.valid is False
        assert len(result.missing_fields) == len(REQUIRED_1X_FIELDS)

    def test_all_2x_fields_present(self, validator):
        output = {
            "execution_profile": "performance_2x",
            "scope_classification": "tier_2_algorithmic",
            "summary": "Test",
            "code_changes": ["change1"],
            "compliance_notes": ["ok"],
            "tests": ["pytest"],
            "risks": ["none"],
            "problem_analysis": "Analysis here",
            "algorithm_selection_rationale": "Rationale here",
            "complexity_certificate": {"time": "O(n log n)", "space": "O(n)"},
            "edge_case_analysis": {"empty": "handled"},
            "stress_test_plan": "Plan here",
            "memory_bound_estimate": "Estimate here",
        }
        result = validator.validate(output, "performance_2x")
        assert result.valid is True
        assert result.missing_fields == []

    def test_missing_2x_fields(self, validator):
        output = {"execution_profile": "performance_2x", "summary": "Test"}
        result = validator.validate(output, "performance_2x")
        assert result.valid is False
        assert "algorithm_selection_rationale" in result.missing_fields
        assert "complexity_certificate" in result.missing_fields


class TestEmptyFieldDetection:
    def test_detects_none_fields(self, validator):
        output = {
            "execution_profile": "default_1x",
            "scope_classification": "tier_1_universal",
            "summary": "Test",
            "code_changes": ["change1"],
            "compliance_notes": None,
            "tests": ["pytest"],
            "risks": ["none"],
        }
        result = validator.validate(output, "default_1x")
        assert "compliance_notes" in result.empty_fields

    def test_detects_empty_strings(self, validator):
        output = {
            "execution_profile": "default_1x",
            "scope_classification": "tier_1_universal",
            "summary": "",
            "code_changes": ["change1"],
            "compliance_notes": ["ok"],
            "tests": ["pytest"],
            "risks": ["none"],
        }
        result = validator.validate(output, "default_1x")
        assert "summary" in result.empty_fields


class Test2xSpecificValidation:
    def test_warns_on_missing_time_complexity(self, validator):
        output = {
            "execution_profile": "performance_2x",
            "scope_classification": "tier_2_algorithmic",
            "summary": "Test",
            "code_changes": ["change1"],
            "compliance_notes": ["ok"],
            "tests": ["pytest"],
            "risks": ["none"],
            "problem_analysis": "Analysis",
            "algorithm_selection_rationale": "Rationale with enough text here",
            "complexity_certificate": {"space": "O(n)"},
            "edge_case_analysis": {"empty": "handled"},
            "stress_test_plan": "Plan with enough text here to pass",
            "memory_bound_estimate": "Estimate with enough text here",
        }
        result = validator.validate(output, "performance_2x")
        assert any("time complexity" in w for w in result.warnings)

    def test_warns_on_short_rationale(self, validator):
        output = {
            "execution_profile": "performance_2x",
            "scope_classification": "tier_2_algorithmic",
            "summary": "Test",
            "code_changes": ["change1"],
            "compliance_notes": ["ok"],
            "tests": ["pytest"],
            "risks": ["none"],
            "problem_analysis": "Analysis",
            "algorithm_selection_rationale": "Short",
            "complexity_certificate": {"time": "O(n)", "space": "O(n)"},
            "edge_case_analysis": {"empty": "handled"},
            "stress_test_plan": "Plan with enough text here to pass",
            "memory_bound_estimate": "Estimate with enough text here",
        }
        result = validator.validate(output, "performance_2x")
        assert any("too short" in w for w in result.warnings)


class TestProfileConsistency:
    def test_matching_profile_and_tier(self, validator):
        output = {
            "execution_profile": "default_1x",
            "scope_classification": "tier_1_universal",
        }
        issues = validator.validate_profile_consistency(
            output, "default_1x", "tier_1_universal"
        )
        assert issues == []

    def test_mismatched_profile(self, validator):
        output = {
            "execution_profile": "performance_2x",
            "scope_classification": "tier_1_universal",
        }
        issues = validator.validate_profile_consistency(
            output, "default_1x", "tier_1_universal"
        )
        assert len(issues) == 1
        assert "Profile mismatch" in issues[0]

    def test_mismatched_tier(self, validator):
        output = {
            "execution_profile": "default_1x",
            "scope_classification": "tier_3_competitive",
        }
        issues = validator.validate_profile_consistency(
            output, "default_1x", "tier_1_universal"
        )
        assert len(issues) == 1
        assert "Tier mismatch" in issues[0]

    def test_no_declared_fields(self, validator):
        output = {"summary": "Test"}
        issues = validator.validate_profile_consistency(
            output, "default_1x", "tier_1_universal"
        )
        assert issues == []


class TestPassedProperty:
    def test_passed_when_valid(self, validator):
        output = {
            "execution_profile": "default_1x",
            "scope_classification": "tier_1_universal",
            "summary": "Test",
            "code_changes": ["change1"],
            "compliance_notes": ["ok"],
            "tests": ["pytest"],
            "risks": ["none"],
        }
        result = validator.validate(output, "default_1x")
        assert result.passed is True

    def test_not_passed_when_missing_fields(self, validator):
        result = validator.validate({}, "default_1x")
        assert result.passed is False
