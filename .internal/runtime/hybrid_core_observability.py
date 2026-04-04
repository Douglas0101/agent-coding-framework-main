"""Hybrid Core Observability — Runtime implementation.

Extends the existing observability infrastructure to track Hybrid Core
1x/2x specific metrics: scope detection results, profile activations,
gate executions, and classification accuracy.

Integrates with: .internal/runtime/observability.py
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ARTIFACTS_DIR = REPO_ROOT / ".internal" / "artifacts" / "hybrid-core"


@dataclass
class ScopeDetectionRecord:
    """Record of a single scope detection event."""

    timestamp: str
    task_summary: str
    detected_tier: str
    detected_profile: str
    confidence: float
    score: float
    triggers_matched: list[str]
    suggested_algorithm: str | None
    duration_ms: float
    anti_false_positive_checked: bool


@dataclass
class GateExecutionRecord:
    """Record of a single gate execution."""

    timestamp: str
    profile: str
    tier: str
    universal_gates_count: int
    specialized_gates_count: int
    overall_status: str
    auto_reject: bool
    rejection_reasons: list[str]
    duration_ms: float


@dataclass
class ExecutionRecord:
    """Complete record of a Hybrid Core execution."""

    timestamp: str
    run_id: str
    task_summary: str
    scope_detection: dict[str, Any]
    active_profile: str
    active_tier: str
    quality_threshold: float
    gate_report: dict[str, Any]
    output_validation: dict[str, Any]
    total_duration_ms: float
    token_usage: dict[str, int] = field(default_factory=dict)
    status: str = "completed"


class HybridCoreObservability:
    """Tracks and persists Hybrid Core 1x/2x execution metrics."""

    def __init__(self, artifacts_dir: Path | None = None):
        self._artifacts_dir = artifacts_dir or ARTIFACTS_DIR
        self._scope_log: list[ScopeDetectionRecord] = []
        self._gate_log: list[GateExecutionRecord] = []
        self._execution_log: list[ExecutionRecord] = []
        self._classification_stats: dict[str, int] = {
            "tier_1_universal": 0,
            "tier_2_algorithmic": 0,
            "tier_3_competitive": 0,
        }
        self._profile_stats: dict[str, int] = {
            "default_1x": 0,
            "performance_2x": 0,
        }

    def record_scope_detection(self, record: ScopeDetectionRecord) -> None:
        """Record a scope detection event."""
        self._scope_log.append(record)
        self._classification_stats[record.detected_tier] = (
            self._classification_stats.get(record.detected_tier, 0) + 1
        )
        self._profile_stats[record.detected_profile] = (
            self._profile_stats.get(record.detected_profile, 0) + 1
        )

    def record_gate_execution(self, record: GateExecutionRecord) -> None:
        """Record a gate execution event."""
        self._gate_log.append(record)

    def record_execution(self, record: ExecutionRecord) -> None:
        """Record a complete execution event."""
        self._execution_log.append(record)

    def persist(self) -> Path:
        """Persist all records to the artifacts directory.

        Returns:
            Path to the persisted directory.
        """
        self._artifacts_dir.mkdir(parents=True, exist_ok=True)

        timestamp = time.strftime("%Y%m%d-%H%M%S")
        run_dir = self._artifacts_dir / timestamp
        run_dir.mkdir(exist_ok=True)

        (run_dir / "scope_detections.jsonl").write_text(
            "\n".join(json.dumps(asdict(r)) for r in self._scope_log) + "\n",
            encoding="utf-8",
        )
        (run_dir / "gate_executions.jsonl").write_text(
            "\n".join(json.dumps(asdict(r)) for r in self._gate_log) + "\n",
            encoding="utf-8",
        )
        (run_dir / "executions.jsonl").write_text(
            "\n".join(json.dumps(asdict(r)) for r in self._execution_log) + "\n",
            encoding="utf-8",
        )
        (run_dir / "summary.json").write_text(
            json.dumps(self.get_summary(), indent=2),
            encoding="utf-8",
        )

        return run_dir

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all recorded metrics."""
        total_executions = len(self._execution_log)
        total_scope_detections = len(self._scope_log)
        total_gate_executions = len(self._gate_log)

        gate_pass_rate = 0.0
        if total_gate_executions > 0:
            passed = sum(1 for g in self._gate_log if g.overall_status == "pass")
            gate_pass_rate = round(passed / total_gate_executions, 3)

        rejection_rate = 0.0
        if total_gate_executions > 0:
            rejected = sum(1 for g in self._gate_log if g.auto_reject)
            rejection_rate = round(rejected / total_gate_executions, 3)

        avg_confidence = 0.0
        if total_scope_detections > 0:
            avg_confidence = round(
                sum(s.confidence for s in self._scope_log) / total_scope_detections,
                3,
            )

        return {
            "total_executions": total_executions,
            "total_scope_detections": total_scope_detections,
            "total_gate_executions": total_gate_executions,
            "classification_distribution": dict(self._classification_stats),
            "profile_distribution": dict(self._profile_stats),
            "gate_pass_rate": gate_pass_rate,
            "rejection_rate": rejection_rate,
            "avg_scope_confidence": avg_confidence,
        }

    def get_classification_distribution(self) -> dict[str, int]:
        """Get the distribution of tier classifications."""
        return dict(self._classification_stats)

    def get_profile_distribution(self) -> dict[str, int]:
        """Get the distribution of profile activations."""
        return dict(self._profile_stats)

    def get_gate_pass_rate(self) -> float:
        """Get the overall gate pass rate."""
        if not self._gate_log:
            return 0.0
        passed = sum(1 for g in self._gate_log if g.overall_status == "pass")
        return round(passed / len(self._gate_log), 3)

    def get_rejection_rate(self) -> float:
        """Get the auto-rejection rate."""
        if not self._gate_log:
            return 0.0
        rejected = sum(1 for g in self._gate_log if g.auto_reject)
        return round(rejected / len(self._gate_log), 3)

    def get_recent_scope_detections(self, n: int = 10) -> list[ScopeDetectionRecord]:
        """Get the most recent scope detection records."""
        return self._scope_log[-n:]

    def get_recent_gate_executions(self, n: int = 10) -> list[GateExecutionRecord]:
        """Get the most recent gate execution records."""
        return self._gate_log[-n:]

    def clear(self) -> None:
        """Clear all in-memory records."""
        self._scope_log.clear()
        self._gate_log.clear()
        self._execution_log.clear()
        self._classification_stats = {
            "tier_1_universal": 0,
            "tier_2_algorithmic": 0,
            "tier_3_competitive": 0,
        }
        self._profile_stats = {
            "default_1x": 0,
            "performance_2x": 0,
        }
