"""Hybrid Core Engine — Main orchestrator.

Orchestrates the full Hybrid Core 1x/2x execution pipeline:
  Scope Detection → Profile Activation → Gate Execution → Output Validation → Observability

This is the primary entry point for Hybrid Core execution.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from .scope_detector import ScopeDetector, ScopeResult
from .profile_activator import ProfileActivator, ActiveProfile
from .gate_executor import GateExecutor, GateReport
from .output_validator import OutputValidator, ValidationResult
from .hybrid_core_observability import (
    HybridCoreObservability,
    ScopeDetectionRecord,
    GateExecutionRecord,
    ExecutionRecord,
)
from .hybrid_core_config import is_hybrid_core_enabled


@dataclass
class ExecutionResult:
    """Complete result of a Hybrid Core execution."""

    run_id: str
    profile: str
    tier: str
    scope_result: ScopeResult
    active_profile: ActiveProfile
    gate_report: GateReport
    output_validation: ValidationResult
    code_output: dict[str, Any]
    duration_ms: float
    token_usage: dict[str, int] = field(default_factory=dict)
    status: str = "completed"

    @property
    def passed(self) -> bool:
        return self.gate_report.passed and self.output_validation.passed

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "profile": self.profile,
            "tier": self.tier,
            "scope_result": asdict(self.scope_result),
            "gate_report": {
                "overall_status": self.gate_report.overall_status,
                "auto_reject": self.gate_report.auto_reject,
                "rejection_reasons": self.gate_report.rejection_reasons,
                "universal_gates": len(self.gate_report.universal_gates),
                "specialized_gates": len(self.gate_report.specialized_gates),
            },
            "output_validation": {
                "valid": self.output_validation.valid,
                "missing_fields": self.output_validation.missing_fields,
                "warnings": self.output_validation.warnings,
            },
            "duration_ms": self.duration_ms,
            "status": self.status,
        }


class HybridCoreEngine:
    """Main Hybrid Core 1x/2x execution engine.

    Orchestrates scope detection, profile activation, gate execution,
    output validation, and observability in a single pipeline.
    """

    def __init__(
        self,
        scope_detector: ScopeDetector | None = None,
        profile_activator: ProfileActivator | None = None,
        gate_executor: GateExecutor | None = None,
        output_validator: OutputValidator | None = None,
        observability: HybridCoreObservability | None = None,
    ):
        self.scope_detector = scope_detector or ScopeDetector()
        self.profile_activator = profile_activator or ProfileActivator()
        self.gate_executor = gate_executor or GateExecutor()
        self.output_validator = output_validator or OutputValidator()
        self.observability = observability or HybridCoreObservability()

    def execute(
        self,
        task: str,
        code_output: dict[str, Any] | None = None,
        source_code: str = "",
        context: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Execute the full Hybrid Core pipeline.

        Args:
            task: Task description for scope detection.
            code_output: Agent's output dictionary (if already generated).
            source_code: Generated source code for gate analysis.
            context: Additional context for scope detection.

        Returns:
            ExecutionResult with all pipeline results.
        """
        start = time.monotonic()
        run_id = str(uuid.uuid4())[:8]

        # Step 1: Scope Detection
        if is_hybrid_core_enabled():
            scope_result = self.scope_detector.classify(task, context)
        else:
            scope_result = ScopeResult(
                tier="tier_1_universal",
                profile="default_1x",
                confidence=1.0,
                score=0.0,
                rationale="Hybrid Core escalation disabled by feature flag; forcing default_1x.",
            )

        # Step 2: Profile Activation
        active_profile = self.profile_activator.activate(
            scope_result.tier, scope_result.profile
        )

        is_2x = active_profile.is_2x()

        # Step 3: Gate Execution
        output = code_output or {}
        gate_report = self.gate_executor.execute_all(
            code_output=output,
            is_2x=is_2x,
            source_code=source_code,
        )

        # Step 4: Output Validation
        output_validation = self.output_validator.validate(
            output=output,
            profile=active_profile.profile,
            tier=active_profile.tier,
        )

        # Step 5: Profile consistency check
        consistency_issues = self.output_validator.validate_profile_consistency(
            output=output,
            expected_profile=active_profile.profile,
            expected_tier=active_profile.tier,
        )
        if consistency_issues:
            output_validation.warnings.extend(consistency_issues)

        duration_ms = round((time.monotonic() - start) * 1000, 2)

        result = ExecutionResult(
            run_id=run_id,
            profile=active_profile.profile,
            tier=active_profile.tier,
            scope_result=scope_result,
            active_profile=active_profile,
            gate_report=gate_report,
            output_validation=output_validation,
            code_output=output,
            duration_ms=duration_ms,
        )

        # Step 6: Observability
        self._record_observability(result, scope_result, gate_report, duration_ms)

        return result

    def execute_with_verification(
        self,
        task: str,
        code_output: dict[str, Any] | None = None,
        source_code: str = "",
        context: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Execute with strict verification — fails if any gate fails.

        Same as execute() but raises ValueError on gate failure.
        """
        result = self.execute(task, code_output, source_code, context)

        if not result.passed:
            reasons = result.gate_report.rejection_reasons
            missing = result.output_validation.missing_fields
            raise ValueError(
                f"Hybrid Core verification failed for run {result.run_id}: "
                f"gate_reasons={reasons}, missing_fields={missing}"
            )

        return result

    def _record_observability(
        self,
        result: ExecutionResult,
        scope_result: ScopeResult,
        gate_report: GateReport,
        duration_ms: float,
    ) -> None:
        """Record execution metrics to observability layer."""
        import datetime

        ts = datetime.datetime.utcnow().isoformat() + "Z"

        self.observability.record_scope_detection(
            ScopeDetectionRecord(
                timestamp=ts,
                task_summary=result.code_output.get("summary", "")[:100] or result.task
                if hasattr(result, "task")
                else "",
                detected_tier=scope_result.tier,
                detected_profile=scope_result.profile,
                confidence=scope_result.confidence,
                score=scope_result.score,
                triggers_matched=scope_result.triggers_matched,
                suggested_algorithm=scope_result.suggested_algorithm,
                duration_ms=duration_ms,
                anti_false_positive_checked=scope_result.anti_false_positive_checked,
            )
        )

        self.observability.record_gate_execution(
            GateExecutionRecord(
                timestamp=ts,
                profile=result.profile,
                tier=result.tier,
                universal_gates_count=len(gate_report.universal_gates),
                specialized_gates_count=len(gate_report.specialized_gates),
                overall_status=gate_report.overall_status,
                auto_reject=gate_report.auto_reject,
                rejection_reasons=gate_report.rejection_reasons,
                duration_ms=duration_ms,
            )
        )

        self.observability.record_execution(
            ExecutionRecord(
                timestamp=ts,
                run_id=result.run_id,
                task_summary="",
                scope_result=asdict(scope_result),
                active_profile=result.profile,
                active_tier=result.tier,
                quality_threshold=result.active_profile.quality_threshold,
                gate_report={
                    "overall_status": gate_report.overall_status,
                    "auto_reject": gate_report.auto_reject,
                },
                output_validation={
                    "valid": result.output_validation.valid,
                    "missing_fields": result.output_validation.missing_fields,
                },
                total_duration_ms=duration_ms,
                token_usage=result.token_usage,
                status=result.status,
            )
        )
