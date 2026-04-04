"""Hybrid Core Validator — Native validation hook for Autocoder mode.

This module provides the native integration point between OpenCode's
Autocoder mode and the Hybrid Core Execution Engine. It validates all
code outputs against the NOU (Universal Quality) contract and optionally
applies NOE (Specialized) validation when performance_2x profile is active.

This is the CORE CENTER of the framework - ALL LLM outputs pass through here.

Usage:
    from hybrid_core_validator import HybridCoreValidator

    validator = HybridCoreValidator()
    result = validator.validate(output, task_context)

    if not result.passed:
        # Reject output and provide feedback
        return result.feedback_to_llm()
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

try:
    from .gate_executor import GateExecutor, GateReport, GateCheck
    from .scope_detector import ScopeDetector, ScopeResult
    from .profile_activator import ProfileActivator, ActiveProfile
    from .output_validator import (
        OutputValidator,
        ValidationResult as OutputValidationResult,
    )
    from .hybrid_core_observability import (
        HybridCoreObservability,
        ScopeDetectionRecord,
        GateExecutionRecord,
        ExecutionRecord,
    )
    from .hybrid_core_config import is_hybrid_core_enabled
except ImportError:  # pragma: no cover - standalone script/test compatibility
    from gate_executor import GateExecutor, GateReport, GateCheck
    from scope_detector import ScopeDetector, ScopeResult
    from profile_activator import ProfileActivator, ActiveProfile
    from output_validator import (
        OutputValidator,
        ValidationResult as OutputValidationResult,
    )
    from hybrid_core_observability import (
        HybridCoreObservability,
        ScopeDetectionRecord,
        GateExecutionRecord,
        ExecutionRecord,
    )
    from hybrid_core_config import is_hybrid_core_enabled


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SPECS_PATH = REPO_ROOT / ".internal" / "specs"


@dataclass
class ValidationResult:
    """Complete validation result for Hybrid Core."""

    passed: bool
    profile: str
    tier: str
    scope_result: ScopeResult | None = None
    gate_report: GateReport | None = None
    output_validation: OutputValidationResult | None = None
    profile_consistency_issues: list[str] = field(default_factory=list)
    quality_score: float = 0.0
    rejection_reasons: list[str] = field(default_factory=list)
    compliance_notes: list[str] = field(default_factory=list)
    feedback_to_llm: str = ""
    execution_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "profile": self.profile,
            "tier": self.tier,
            "scope_result": self.scope_result.to_dict() if self.scope_result else None,
            "gate_report": {
                "overall_status": self.gate_report.overall_status
                if self.gate_report
                else "unknown",
                "auto_reject": self.gate_report.auto_reject
                if self.gate_report
                else False,
                "rejection_reasons": self.gate_report.rejection_reasons
                if self.gate_report
                else [],
                "universal_gates": len(self.gate_report.universal_gates)
                if self.gate_report
                else 0,
                "specialized_gates": len(self.gate_report.specialized_gates)
                if self.gate_report
                else 0,
            }
            if self.gate_report
            else None,
            "output_validation": {
                "valid": self.output_validation.valid
                if self.output_validation
                else False,
                "missing_fields": self.output_validation.missing_fields
                if self.output_validation
                else [],
            }
            if self.output_validation
            else None,
            "profile_consistency_issues": self.profile_consistency_issues,
            "quality_score": self.quality_score,
            "rejection_reasons": self.rejection_reasons,
            "compliance_notes": self.compliance_notes,
            "feedback_to_llm": self.feedback_to_llm,
            "execution_time_ms": self.execution_time_ms,
        }


class HybridCoreValidator:
    """Native validation hook for Autocoder mode.

    This is the CORE CENTER of the framework. ALL LLM outputs from
    ANY provider (OpenAI, Anthropic, Ollama, etc.) pass through this
    validator before being accepted.

    It enforces:
    - NOU (Universal Quality): typing, null safety, security, etc.
    - FR-013: Over-engineering detection
    - FR-014: Under-engineering detection
    - Optional NOE: When tier_2 or tier_3 is detected
    """

    def __init__(self, enable_observability: bool = True):
        self._scope_detector = ScopeDetector()
        self._profile_activator = ProfileActivator()
        self._gate_executor = GateExecutor()
        self._output_validator = OutputValidator()
        self._enable_observability = enable_observability
        self._observability = (
            HybridCoreObservability() if enable_observability else None
        )

        self._load_specs()

    def _load_specs(self):
        """Load specification files."""
        self._universal_contract = self._load_yaml(
            SPECS_PATH / "core" / "universal-quality-contract.yaml"
        )
        self._algorithmic_contract = self._load_yaml(
            SPECS_PATH / "core" / "algorithmic-frontier-contract.yaml"
        )
        self._execution_profiles = self._load_yaml(
            SPECS_PATH / "core" / "execution-profiles.yaml"
        )

    def _load_yaml(self, path: Path) -> dict | None:
        if not path.exists():
            return None
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    def validate(
        self,
        code_output: dict[str, Any],
        task: str,
        source_code: str = "",
        context: dict[str, Any] | None = None,
    ) -> ValidationResult:
        """Validate LLM output through Hybrid Core.

        This is the MAIN entry point for validation. ALL LLM outputs
        should pass through this method.

        Args:
            code_output: The LLM's output dictionary (from agent response)
            task: The original task description
            source_code: The generated/modified source code
            context: Additional context (constraints, file paths, etc.)

        Returns:
            ValidationResult with pass/fail status and feedback
        """
        start_time = datetime.now()

        task_context = task
        if context:
            if "files_content" in context:
                task_context += "\n" + "\n".join(context["files_content"].values())
            if "constraints" in context:
                task_context += "\n" + str(context["constraints"])

        if is_hybrid_core_enabled():
            scope_result = self._scope_detector.classify(task, context or {})
        else:
            scope_result = ScopeResult(
                tier="tier_1_universal",
                profile="default_1x",
                confidence=1.0,
                score=0.0,
                rationale="Hybrid Core escalation disabled by feature flag; forcing default_1x.",
            )

        is_2x = scope_result.profile == "performance_2x"

        active_profile = self._profile_activator.activate(
            scope_result.tier,  # Pass tier first, not profile
            scope_result.profile,  # profile is optional second arg
        )

        if source_code and isinstance(code_output.get("code_changes"), dict):
            code_output["code_changes"]["code"] = source_code
        elif source_code and isinstance(code_output.get("code_changes"), str):
            pass
        else:
            code_output["code_changes"] = {"code": source_code}

        gate_report = self._gate_executor.execute_all(
            code_output=code_output,
            is_2x=is_2x,
            source_code=source_code,
        )

        output_validation = self._output_validator.validate(
            output=code_output,
            profile=scope_result.profile,
        )
        profile_consistency_issues = (
            self._output_validator.validate_profile_consistency(
                code_output,
                scope_result.profile,
                scope_result.tier,
            )
        )

        overall_passed = (
            gate_report.passed
            and output_validation.valid
            and not gate_report.auto_reject
            and not profile_consistency_issues
        )

        rejection_reasons = []
        if not overall_passed:
            rejection_reasons = list(gate_report.rejection_reasons)
            if output_validation.missing_fields:
                rejection_reasons.append(
                    f"Missing required fields: {', '.join(output_validation.missing_fields)}"
                )
            rejection_reasons.extend(profile_consistency_issues)

        quality_score = self._compute_quality_score(
            gate_report, output_validation, scope_result
        )

        feedback = self._build_feedback(
            overall_passed, gate_report, output_validation, scope_result, quality_score
        )

        compliance_notes = self._build_compliance_notes(
            gate_report, output_validation, scope_result
        )

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        if self._observability:
            self._record_observability(
                task=task,
                scope_result=scope_result,
                gate_report=gate_report,
                output_validation=output_validation,
                execution_time=execution_time,
            )

        return ValidationResult(
            passed=overall_passed,
            profile=scope_result.profile,
            tier=scope_result.tier,
            scope_result=scope_result,
            gate_report=gate_report,
            output_validation=output_validation,
            profile_consistency_issues=profile_consistency_issues,
            quality_score=quality_score,
            rejection_reasons=rejection_reasons,
            compliance_notes=compliance_notes,
            feedback_to_llm=feedback,
            execution_time_ms=execution_time,
        )

    def _compute_quality_score(
        self,
        gate_report: GateReport,
        output_validation: OutputValidationResult,
        scope_result: ScopeResult,
    ) -> float:
        """Compute overall quality score (0.0 to 1.0)."""
        score = 0.0
        components = 0

        if gate_report.universal_gates:
            gate_pass_count = sum(
                1 for g in gate_report.universal_gates if g.status == "pass"
            )
            gate_score = gate_pass_count / len(gate_report.universal_gates)
            score += gate_score
            components += 1

        if gate_report.specialized_gates:
            spec_pass_count = sum(
                1 for g in gate_report.specialized_gates if g.status == "pass"
            )
            spec_score = spec_pass_count / len(gate_report.specialized_gates)
            score += spec_score
            components += 1

        if output_validation.valid:
            score += 1.0
            components += 1

        score += scope_result.confidence
        components += 1

        if components > 0:
            score = score / components

        return round(min(1.0, max(0.0, score)), 3)

    def _build_feedback(
        self,
        passed: bool,
        gate_report: GateReport,
        output_validation: OutputValidationResult,
        scope_result: ScopeResult,
        quality_score: float,
    ) -> str:
        """Build feedback message for LLM."""
        lines = []

        if passed:
            lines.append(f"✅ Validation PASSED (quality: {quality_score:.1%})")
            lines.append(f"Profile: {scope_result.profile}, Tier: {scope_result.tier}")
        else:
            lines.append(f"❌ Validation FAILED (quality: {quality_score:.1%})")
            lines.append(f"Profile: {scope_result.profile}, Tier: {scope_result.tier}")
            lines.append("")
            lines.append("## Issues found:")

            if gate_report.rejection_reasons:
                for reason in gate_report.rejection_reasons:
                    lines.append(f"  - {reason}")

            if output_validation.missing_fields:
                lines.append(
                    f"  - Missing fields: {', '.join(output_validation.missing_fields)}"
                )

        lines.append("")
        lines.append("## Gates executed:")

        for gate in gate_report.universal_gates:
            status_emoji = (
                "✅"
                if gate.status == "pass"
                else "❌"
                if gate.status == "fail"
                else "⚠️"
            )
            lines.append(f"  {status_emoji} {gate.gate_name}: {gate.status}")
            for check in gate.checks:
                if check.status != "pass":
                    lines.append(f"      - {check.check_id}: {check.message}")

        if gate_report.specialized_gates:
            lines.append("")
            lines.append("## Specialized Gates (2x):")
            for gate in gate_report.specialized_gates:
                status_emoji = (
                    "✅"
                    if gate.status == "pass"
                    else "❌"
                    if gate.status == "fail"
                    else "⚠️"
                )
                lines.append(f"  {status_emoji} {gate.gate_name}: {gate.status}")

        return "\n".join(lines)

    def _build_compliance_notes(
        self,
        gate_report: GateReport,
        output_validation: OutputValidationResult,
        scope_result: ScopeResult,
    ) -> list[str]:
        """Build compliance notes list."""
        notes = []

        universal_dims = (
            self._universal_contract.get("dimensions", [])
            if self._universal_contract
            else []
        )
        for dim in universal_dims:
            notes.append(f"universal:{dim}")

        for gate in gate_report.universal_gates:
            if gate.status == "pass":
                notes.append(f"gate:{gate.gate_id}:pass")
            else:
                notes.append(f"gate:{gate.gate_id}:fail")

        if scope_result.profile == "performance_2x":
            algo_dims = (
                self._algorithmic_contract.get("requires", [])
                if self._algorithmic_contract
                else []
            )
            for dim in algo_dims:
                notes.append(f"specialized:{dim}")

        return notes

    def validate_simple(
        self,
        code_output: dict[str, Any],
        task: str,
    ) -> bool:
        """Simple boolean validation for quick checks.

        Use this for quick pass/fail checks. For detailed feedback,
        use the full validate() method.
        """
        result = self.validate(code_output, task)
        return result.passed

    def enforce_nou(self, source_code: str) -> tuple[bool, list[str]]:
        """Enforce NOU (Universal Quality) only.

        Use this when you need to validate basic quality without
        the full Hybrid Core pipeline.
        """
        code_output = {"code_changes": {"code": source_code}}

        gate_report = self._gate_executor.execute_universal_gates(
            code_output, source_code
        )

        failed = []
        for gate in gate_report:
            if gate.status == "fail":
                for check in gate.checks:
                    if check.status == "fail":
                        failed.append(f"[{gate.gate_id}] {check.message}")

        return len(failed) == 0, failed

    def _record_observability(
        self,
        task: str,
        scope_result: ScopeResult,
        gate_report: GateReport,
        output_validation: OutputValidationResult,
        execution_time: float,
    ) -> None:
        """Record observability data after validation."""
        if not self._observability:
            return

        run_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().isoformat()

        scope_record = ScopeDetectionRecord(
            timestamp=timestamp,
            task_summary=task[:100],
            detected_tier=scope_result.tier,
            detected_profile=scope_result.profile,
            confidence=scope_result.confidence,
            score=scope_result.score,
            triggers_matched=scope_result.triggers_matched,
            suggested_algorithm=scope_result.suggested_algorithm,
            duration_ms=execution_time,
            anti_false_positive_checked=scope_result.anti_false_positive_checked,
        )
        self._observability.record_scope_detection(scope_record)

        gate_record = GateExecutionRecord(
            timestamp=timestamp,
            profile=scope_result.profile,
            tier=scope_result.tier,
            universal_gates_count=len(gate_report.universal_gates),
            specialized_gates_count=len(gate_report.specialized_gates),
            overall_status=gate_report.overall_status,
            auto_reject=gate_report.auto_reject,
            rejection_reasons=gate_report.rejection_reasons,
            duration_ms=execution_time,
        )
        self._observability.record_gate_execution(gate_record)

    def persist_observability(self) -> Path | None:
        """Persist observability data to disk."""
        if self._observability:
            return self._observability.persist()
        return None


def create_validator() -> HybridCoreValidator:
    """Factory function to create a validator instance."""
    return HybridCoreValidator()


def create_validator_with_observability() -> HybridCoreValidator:
    """Factory function to create a validator with observability enabled."""
    return HybridCoreValidator(enable_observability=True)


def validate_and_enforce(
    code_output: dict, task: str, source_code: str = ""
) -> ValidationResult:
    """Standalone function for quick validation.

    This is the MAIN export - use this function as the entry point
    for all validations.
    """
    validator = HybridCoreValidator()
    return validator.validate(code_output, task, source_code)
