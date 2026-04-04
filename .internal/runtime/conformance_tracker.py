"""
Conformance Tracker — Runtime tracking of execution compliance.

Records verification results, policy findings, and approval decisions
per execution run, producing structured conformance reports.
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
CONFORMANCE_DIR = ARTIFACTS_DIR / "conformance"
CONFORMANCE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class TraceSpan:
    span_id: str
    parent_span_id: str | None
    run_id: str
    component: str  # contract_verifier, policy_enforcer, approval_gate
    operation: str
    start_time: str
    end_time: str | None = None
    status: str = "pending"  # pending, ok, failed
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ConformanceRecord:
    run_id: str
    timestamp: str
    contract_verification: dict[str, Any] = field(default_factory=dict)
    policy_scan: dict[str, Any] = field(default_factory=dict)
    approval_decision: dict[str, Any] = field(default_factory=dict)
    traces: list[TraceSpan] = field(default_factory=list)
    overall_status: str = "pending"  # pending, compliant, non_compliant, blocked
    integrity_hash: str = ""

    @property
    def compliant(self) -> bool:
        if self.overall_status == "blocked":
            return False
        cv = self.contract_verification
        if cv and not cv.get("all_passed", True):
            return False
        ps = self.policy_scan
        if ps and not ps.get("passed", True):
            return False
        ad = self.approval_decision
        if ad and not ad.get("approved", True):
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "overall_status": self.overall_status,
            "compliant": self.compliant,
            "contract_verification": self.contract_verification,
            "policy_scan": self.policy_scan,
            "approval_decision": self.approval_decision,
            "traces": [t.to_dict() for t in self.traces],
            "integrity_hash": self.integrity_hash,
        }


class ConformanceTracker:
    """Tracks compliance of execution runs across all runtime components."""

    def __init__(self, run_id: str | None = None) -> None:
        self.run_id = (
            run_id or f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        )
        self.record = ConformanceRecord(
            run_id=self.run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._spans: list[TraceSpan] = []

    def record_contract_verification(self, results: dict[str, Any]) -> None:
        self.record.contract_verification = results
        all_passed = all(r.get("passed", False) for r in results.values())
        self.record.contract_verification["all_passed"] = all_passed
        self._add_span(
            "contract_verifier", "verify_all_modes", "ok" if all_passed else "failed"
        )

    def record_policy_scan(self, results: dict[str, Any]) -> None:
        self.record.policy_scan = results
        self._add_span(
            "policy_enforcer",
            "scan",
            "ok" if results.get("passed", False) else "failed",
        )

    def record_approval_decision(self, results: dict[str, Any]) -> None:
        self.record.approval_decision = results
        self._add_span(
            "approval_gate",
            "evaluate",
            "ok" if results.get("approved", False) else "failed",
        )

    def finalize(self) -> ConformanceRecord:
        if self.record.compliant:
            self.record.overall_status = "compliant"
        else:
            ad = self.record.approval_decision
            if ad and not ad.get("approved", True):
                self.record.overall_status = "blocked"
            else:
                self.record.overall_status = "non_compliant"

        self.record.traces = self._spans
        self.record.integrity_hash = self._compute_hash(self.record)
        self._persist()
        return self.record

    def _add_span(self, component: str, operation: str, status: str) -> None:
        span = TraceSpan(
            span_id=f"span-{len(self._spans):04d}",
            parent_span_id=None,
            run_id=self.run_id,
            component=component,
            operation=operation,
            start_time=datetime.now(timezone.utc).isoformat(),
            status=status,
        )
        self._spans.append(span)

    def _compute_hash(self, record: ConformanceRecord) -> str:
        content = json.dumps(record.to_dict(), sort_keys=True, default=str)
        return f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"

    def _persist(self) -> Path:
        output_path = CONFORMANCE_DIR / f"{self.run_id}.json"
        output_path.write_text(
            json.dumps(self.record.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )
        return output_path


def run_full_conformance(
    run_id: str | None = None,
    scan_path: str = ".internal/specs",
) -> dict[str, Any]:
    """Run all runtime checks and produce a conformance report."""
    from contract_verifier import verify_all_modes
    from policy_enforcer import scan_directory
    from approval_gate import evaluate_changes

    tracker = ConformanceTracker(run_id=run_id)

    cv_results = verify_all_modes(run_id=tracker.run_id)
    tracker.record_contract_verification(cv_results)

    ps_results = scan_directory(scan_path, run_id=tracker.run_id)
    tracker.record_policy_scan(ps_results)

    changes = [
        {
            "file_path": ".internal/specs/modes/explore.yaml",
            "change_type": "modification",
            "lines_changed": 0,
        },
    ]
    ad_results = evaluate_changes(
        changes,
        run_id=tracker.run_id,
        policy_passed=ps_results.get("passed", True),
        contract_verified=cv_results.get("all_passed", True),
    )
    tracker.record_approval_decision(ad_results)

    record = tracker.finalize()
    return record.to_dict()


if __name__ == "__main__":
    import sys

    run_id = sys.argv[1] if len(sys.argv) > 1 else None
    result = run_full_conformance(run_id=run_id)

    status = "COMPLIANT" if result["compliant"] else "NON-COMPLIANT"
    print(f"[{status}] Conformance report: {result['run_id']}")
    print(
        f"  Contract verification: {'PASS' if result['contract_verification'].get('all_passed') else 'FAIL'}"
    )
    print(f"  Policy scan: {'PASS' if result['policy_scan'].get('passed') else 'FAIL'}")
    print(
        f"  Approval gate: {'PASS' if result['approval_decision'].get('approved') else 'BLOCKED'}"
    )
    print(f"  Traces: {len(result['traces'])}")
    report_path = CONFORMANCE_DIR / f"{result['run_id']}.json"
    print(f"  Report saved to: {report_path}")

    sys.exit(0 if result["compliant"] else 1)
