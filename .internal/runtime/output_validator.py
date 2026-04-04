"""Output Schema Validator — Runtime implementation.

Validates that agent output contains all required fields for the active
execution profile (1x or 2x). Rejects outputs missing mandatory artifacts.

Spec: .internal/specs/core/execution-profiles.yaml
Adapters: .internal/modes/autocoder/adapters/
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

REQUIRED_1X_FIELDS = {
    "execution_profile",
    "scope_classification",
    "summary",
    "code_changes",
    "compliance_notes",
    "tests",
    "risks",
}

REQUIRED_2X_FIELDS = REQUIRED_1X_FIELDS | {
    "problem_analysis",
    "algorithm_selection_rationale",
    "complexity_certificate",
    "edge_case_analysis",
    "stress_test_plan",
    "memory_bound_estimate",
}


@dataclass
class ValidationResult:
    """Result of output validation."""

    valid: bool
    missing_fields: list[str] = field(default_factory=list)
    empty_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    profile: str = ""
    tier: str = ""

    @property
    def passed(self) -> bool:
        return self.valid and len(self.missing_fields) == 0


class OutputValidator:
    """Validates agent output against the active profile's schema."""

    def validate(
        self,
        output: dict[str, Any],
        profile: str,
        tier: str | None = None,
    ) -> ValidationResult:
        """Validate output against the required fields for the given profile.

        Args:
            output: The agent's output dictionary.
            profile: 'default_1x' or 'performance_2x'.
            tier: Optional tier for more specific validation.

        Returns:
            ValidationResult with missing fields, warnings, and pass/fail status.
        """
        is_2x = profile == "performance_2x"
        required_fields = REQUIRED_2X_FIELDS if is_2x else REQUIRED_1X_FIELDS

        missing = []
        empty = []
        warnings = []

        for field_name in required_fields:
            if field_name not in output:
                missing.append(field_name)
            elif output[field_name] is None:
                empty.append(field_name)
            elif isinstance(output[field_name], str) and not output[field_name].strip():
                empty.append(field_name)
            elif (
                isinstance(output[field_name], (list, dict))
                and len(output[field_name]) == 0
            ):
                warnings.append(f"Field '{field_name}' is present but empty")

        if is_2x:
            self._validate_2x_specifics(output, warnings)

        valid = len(missing) == 0

        return ValidationResult(
            valid=valid,
            missing_fields=missing,
            empty_fields=empty,
            warnings=warnings,
            profile=profile,
            tier=tier or ("tier_1_universal" if not is_2x else "tier_2_algorithmic"),
        )

    def _validate_2x_specifics(
        self, output: dict[str, Any], warnings: list[str]
    ) -> None:
        """Additional validation for 2x-specific fields."""
        cert = output.get("complexity_certificate")
        if cert is not None:
            if isinstance(cert, dict):
                if "time" not in cert and "time_complexity" not in cert:
                    warnings.append("complexity_certificate missing time complexity")
                if "space" not in cert and "space_complexity" not in cert:
                    warnings.append("complexity_certificate missing space complexity")
            elif isinstance(cert, str) and not cert.strip():
                warnings.append("complexity_certificate is empty")

        rationale = output.get("algorithm_selection_rationale")
        if rationale and isinstance(rationale, str) and len(rationale) < 20:
            warnings.append("algorithm_selection_rationale is too short (< 20 chars)")

        stress = output.get("stress_test_plan")
        if stress and isinstance(stress, str) and len(stress) < 20:
            warnings.append("stress_test_plan is too short (< 20 chars)")

    def validate_profile_consistency(
        self, output: dict[str, Any], expected_profile: str, expected_tier: str
    ) -> list[str]:
        """Check that output declares the correct profile and tier.

        Returns a list of inconsistency messages (empty if consistent).
        """
        issues = []

        declared_profile = output.get("execution_profile", "")
        if declared_profile and declared_profile != expected_profile:
            issues.append(
                f"Profile mismatch: declared={declared_profile}, expected={expected_profile}"
            )

        declared_tier = output.get("scope_classification", "")
        if declared_tier and declared_tier != expected_tier:
            issues.append(
                f"Tier mismatch: declared={declared_tier}, expected={expected_tier}"
            )

        return issues
