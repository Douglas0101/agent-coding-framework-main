"""
Metrics Collector + KPI Tracker — Runtime metrics aggregation.

Collects, aggregates, and reports KPIs for the framework:
- tokens médios por run
- custo por modo
- custo por handoff
- taxa de compressão de contexto
- taxa de verifier_pass
- taxa de budget_exceeded
- taxa de partial_success
- taxa de handoff inválido
"""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INTERNAL_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = INTERNAL_DIR / "artifacts"
METRICS_DIR = ARTIFACTS_DIR / "metrics"
METRICS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class RunMetrics:
    run_id: str
    timestamp: str
    mode: str
    input_tokens: int = 0
    output_tokens: int = 0
    context_tokens: int = 0
    handoff_count: int = 0
    handoff_tokens: int = 0
    duration_seconds: float = 0.0
    verifier_passed: bool = True
    budget_exceeded: bool = False
    compression_ratio: float = 1.0
    status: str = "success"  # success, partial_success, failed
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens + self.context_tokens

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "total_tokens": self.total_tokens,
        }


@dataclass
class KPIReport:
    run_id: str
    timestamp: str
    total_runs: int = 0
    avg_tokens_per_run: float = 0.0
    cost_by_mode: dict[str, dict[str, Any]] = field(default_factory=dict)
    cost_by_handoff: dict[str, float] = field(default_factory=dict)
    avg_compression_ratio: float = 1.0
    verifier_pass_rate: float = 0.0
    budget_exceeded_rate: float = 0.0
    partial_success_rate: float = 0.0
    invalid_handoff_rate: float = 0.0
    integrity_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "total_runs": self.total_runs,
            "avg_tokens_per_run": round(self.avg_tokens_per_run, 2),
            "cost_by_mode": self.cost_by_mode,
            "cost_by_handoff": self.cost_by_handoff,
            "avg_compression_ratio": round(self.avg_compression_ratio, 4),
            "verifier_pass_rate": round(self.verifier_pass_rate, 4),
            "budget_exceeded_rate": round(self.budget_exceeded_rate, 4),
            "partial_success_rate": round(self.partial_success_rate, 4),
            "invalid_handoff_rate": round(self.invalid_handoff_rate, 4),
            "integrity_hash": self.integrity_hash,
        }


class MetricsCollector:
    """Collects per-run metrics."""

    def __init__(self) -> None:
        self._metrics: list[RunMetrics] = []

    def record(self, metrics: RunMetrics) -> None:
        self._metrics.append(metrics)

    def get_all(self) -> list[RunMetrics]:
        return list(self._metrics)

    def get_by_mode(self, mode: str) -> list[RunMetrics]:
        return [m for m in self._metrics if m.mode == mode]

    def get_by_run(self, run_id: str) -> RunMetrics | None:
        for m in self._metrics:
            if m.run_id == run_id:
                return m
        return None

    def _persist(self, metrics: RunMetrics) -> Path:
        path = METRICS_DIR / f"{metrics.run_id}.json"
        path.write_text(
            json.dumps(metrics.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )
        return path


class KPITracker:
    """Aggregates metrics into KPI reports."""

    def __init__(self, run_id: str | None = None) -> None:
        self.run_id = (
            run_id or f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        )
        self.collector = MetricsCollector()

    def record_run(self, metrics: RunMetrics) -> None:
        self.collector.record(metrics)
        self.collector._persist(metrics)

    def generate_kpi_report(self) -> KPIReport:
        all_metrics = self.collector.get_all()
        total_runs = len(all_metrics)

        if total_runs == 0:
            report = KPIReport(
                run_id=self.run_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            report.integrity_hash = self._compute_hash(report)
            return report

        total_tokens = sum(m.total_tokens for m in all_metrics)
        avg_tokens = total_tokens / total_runs

        cost_by_mode: dict[str, dict[str, Any]] = {}
        for m in all_metrics:
            if m.mode not in cost_by_mode:
                cost_by_mode[m.mode] = {
                    "run_count": 0,
                    "total_tokens": 0,
                    "avg_tokens": 0.0,
                    "avg_handoff_tokens": 0.0,
                }
            cost_by_mode[m.mode]["run_count"] += 1
            cost_by_mode[m.mode]["total_tokens"] += m.total_tokens
            cost_by_mode[m.mode]["avg_handoff_tokens"] += m.handoff_tokens

        for mode_data in cost_by_mode.values():
            count = mode_data["run_count"]
            mode_data["avg_tokens"] = round(mode_data["total_tokens"] / count, 2)
            mode_data["avg_handoff_tokens"] = round(
                mode_data["avg_handoff_tokens"] / count, 2
            )

        cost_by_handoff: dict[str, float] = {}
        handoff_runs = [m for m in all_metrics if m.handoff_count > 0]
        if handoff_runs:
            for m in handoff_runs:
                key = f"{m.mode}-handoff"
                if key not in cost_by_handoff:
                    cost_by_handoff[key] = 0.0
                cost_by_handoff[key] += m.handoff_tokens / max(m.handoff_count, 1)

        avg_compression = sum(m.compression_ratio for m in all_metrics) / total_runs

        verifier_passes = sum(1 for m in all_metrics if m.verifier_passed)
        budget_exceeded = sum(1 for m in all_metrics if m.budget_exceeded)
        partial_success = sum(1 for m in all_metrics if m.status == "partial_success")
        failed = sum(1 for m in all_metrics if m.status == "failed")

        report = KPIReport(
            run_id=self.run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_runs=total_runs,
            avg_tokens_per_run=avg_tokens,
            cost_by_mode=cost_by_mode,
            cost_by_handoff=cost_by_handoff,
            avg_compression_ratio=avg_compression,
            verifier_pass_rate=verifier_passes / total_runs,
            budget_exceeded_rate=budget_exceeded / total_runs,
            partial_success_rate=partial_success / total_runs,
            invalid_handoff_rate=failed / total_runs,
        )
        report.integrity_hash = self._compute_hash(report)
        return report

    def _compute_hash(self, report: KPIReport) -> str:
        content = json.dumps(
            {
                "run_id": report.run_id,
                "total_runs": report.total_runs,
                "avg_tokens_per_run": report.avg_tokens_per_run,
                "verifier_pass_rate": report.verifier_pass_rate,
            },
            sort_keys=True,
            default=str,
        )
        return f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"


def track_kpis(
    run_metrics: list[dict[str, Any]],
    run_id: str | None = None,
) -> dict[str, Any]:
    tracker = KPITracker(run_id=run_id)
    for rm in run_metrics:
        tracker.record_run(
            RunMetrics(
                run_id=rm["run_id"],
                timestamp=rm.get("timestamp", datetime.now(timezone.utc).isoformat()),
                mode=rm["mode"],
                input_tokens=rm.get("input_tokens", 0),
                output_tokens=rm.get("output_tokens", 0),
                context_tokens=rm.get("context_tokens", 0),
                handoff_count=rm.get("handoff_count", 0),
                handoff_tokens=rm.get("handoff_tokens", 0),
                duration_seconds=rm.get("duration_seconds", 0.0),
                verifier_passed=rm.get("verifier_passed", True),
                budget_exceeded=rm.get("budget_exceeded", False),
                compression_ratio=rm.get("compression_ratio", 1.0),
                status=rm.get("status", "success"),
                metadata=rm.get("metadata", {}),
            )
        )
    report = tracker.generate_kpi_report()
    return report.to_dict()


if __name__ == "__main__":
    import sys

    run_id = sys.argv[1] if len(sys.argv) > 1 else None

    tracker = KPITracker(run_id=run_id)

    sample_metrics = [
        {
            "run_id": "run-001",
            "mode": "explore",
            "input_tokens": 8000,
            "output_tokens": 4000,
            "context_tokens": 16000,
            "handoff_count": 2,
            "handoff_tokens": 3000,
            "verifier_passed": True,
            "compression_ratio": 0.45,
            "status": "success",
        },
        {
            "run_id": "run-002",
            "mode": "reviewer",
            "input_tokens": 12000,
            "output_tokens": 6000,
            "context_tokens": 24000,
            "handoff_count": 1,
            "handoff_tokens": 2000,
            "verifier_passed": True,
            "compression_ratio": 0.38,
            "status": "success",
        },
        {
            "run_id": "run-003",
            "mode": "autocoder",
            "input_tokens": 16000,
            "output_tokens": 24000,
            "context_tokens": 32000,
            "handoff_count": 3,
            "handoff_tokens": 5000,
            "verifier_passed": False,
            "compression_ratio": 0.52,
            "status": "partial_success",
        },
    ]

    for sm in sample_metrics:
        tracker.record_run(
            RunMetrics(
                run_id=sm["run_id"],
                timestamp=datetime.now(timezone.utc).isoformat(),
                mode=sm["mode"],
                input_tokens=sm["input_tokens"],
                output_tokens=sm["output_tokens"],
                context_tokens=sm["context_tokens"],
                handoff_count=sm["handoff_count"],
                handoff_tokens=sm["handoff_tokens"],
                verifier_passed=sm["verifier_passed"],
                compression_ratio=sm["compression_ratio"],
                status=sm["status"],
            )
        )

    report = tracker.generate_kpi_report()
    print(f"[OK] KPI report: {report.run_id}")
    print(f"  Total runs: {report.total_runs}")
    print(f"  Avg tokens/run: {report.avg_tokens_per_run:.0f}")
    print(f"  Verifier pass rate: {report.verifier_pass_rate:.2%}")
    print(f"  Budget exceeded rate: {report.budget_exceeded_rate:.2%}")
    print(f"  Partial success rate: {report.partial_success_rate:.2%}")
    print(f"  Avg compression ratio: {report.avg_compression_ratio:.4f}")

    for mode, data in report.cost_by_mode.items():
        print(
            f"  {mode}: {data['run_count']} runs, avg {data['avg_tokens']:.0f} tokens"
        )
