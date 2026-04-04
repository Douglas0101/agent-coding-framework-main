"""
Replay Engine — Minimum replay of critical runs and change classification.

Enables replay of critical runs from stored artifacts, evidence, and handoff logs.
Classifies changes by risk and produces impact matrices.
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
REPLAY_DIR = ARTIFACTS_DIR / "replay"
GOLDEN_DIR = ARTIFACTS_DIR / "golden_traces"
CHANGE_CLASS_DIR = ARTIFACTS_DIR / "change_classification"

for d in (REPLAY_DIR, GOLDEN_DIR, CHANGE_CLASS_DIR):
    d.mkdir(parents=True, exist_ok=True)


@dataclass
class ReplayResult:
    replay_id: str
    original_run_id: str
    timestamp: str
    status: str  # success, partial, failed
    steps_replayed: int = 0
    steps_total: int = 0
    discrepancies: list[str] = field(default_factory=list)
    integrity_match: bool = False
    report_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ChangeClassification:
    classification_id: str
    timestamp: str
    change_description: str
    risk_level: str  # critical, high, medium, low
    affected_contracts: list[str] = field(default_factory=list)
    affected_skills: list[str] = field(default_factory=list)
    affected_packs: list[str] = field(default_factory=list)
    impact_matrix: dict[str, list[str]] = field(default_factory=dict)
    requires_migration: bool = False
    requires_review: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GoldenTrace:
    trace_id: str
    name: str
    description: str
    mode: str
    input_data: dict[str, Any]
    expected_output: dict[str, Any]
    created: str
    version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ReplayEngine:
    """Minimum replay of critical runs from stored artifacts."""

    def __init__(self, run_id: str | None = None) -> None:
        self.run_id = (
            run_id or f"replay-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        )

    def replay_run(self, original_run_id: str) -> ReplayResult:
        conformance_path = ARTIFACTS_DIR / "conformance" / f"{original_run_id}.json"
        if not conformance_path.exists():
            return ReplayResult(
                replay_id=self.run_id,
                original_run_id=original_run_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                status="failed",
                discrepancies=[f"No conformance record found for {original_run_id}"],
            )

        original = json.loads(conformance_path.read_text())
        discrepancies: list[str] = []
        steps_replayed = 0

        cv = original.get("contract_verification", {})
        if cv:
            steps_replayed += 1
            if not cv.get("all_passed", False):
                discrepancies.append("Contract verification had failures")

        ps = original.get("policy_scan", {})
        if ps:
            steps_replayed += 1
            if not ps.get("passed", False):
                discrepancies.append("Policy scan had findings")

        ad = original.get("approval_decision", {})
        if ad:
            steps_replayed += 1
            if not ad.get("approved", False):
                discrepancies.append("Approval gate blocked")

        traces = original.get("traces", [])
        steps_total = len(traces) if traces else steps_replayed

        integrity_match = not discrepancies
        status = (
            "success"
            if integrity_match
            else ("partial" if steps_replayed > 0 else "failed")
        )

        result = ReplayResult(
            replay_id=self.run_id,
            original_run_id=original_run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            status=status,
            steps_replayed=steps_replayed,
            steps_total=steps_total,
            discrepancies=discrepancies,
            integrity_match=integrity_match,
            report_path=str(REPLAY_DIR / f"{self.run_id}.json"),
        )

        replay_path = Path(result.report_path)
        replay_path.write_text(
            json.dumps(result.to_dict(), indent=2, default=str), encoding="utf-8"
        )
        return result


class ChangeClassifier:
    """Classifies changes by risk and produces impact matrices."""

    def __init__(self) -> None:
        self._counter = 0

    def classify(
        self,
        change_description: str,
        affected_files: list[str] | None = None,
    ) -> ChangeClassification:
        self._counter += 1
        affected_files = affected_files or []

        risk_factors: list[str] = []
        affected_contracts: list[str] = []
        affected_skills: list[str] = []
        affected_packs: list[str] = []
        impact_matrix: dict[str, list[str]] = {}

        for f in affected_files:
            if ".internal/specs/" in f:
                affected_contracts.append(f)
                risk_factors.append("contract_change")
            elif ".internal/skills/" in f:
                affected_skills.append(f)
                risk_factors.append("skill_change")
            elif ".internal/domains/" in f:
                affected_packs.append(f)
                risk_factors.append("pack_change")
            elif ".internal/runtime/" in f:
                risk_factors.append("runtime_change")
            elif "opencode.json" in f or ".opencode/" in f:
                risk_factors.append("config_change")

        if not risk_factors:
            risk_factors.append("routine")

        risk_level = self._compute_risk(risk_factors)
        requires_review = risk_level in ("critical", "high")
        requires_migration = "contract_change" in risk_factors

        impact_matrix = {
            "contracts": affected_contracts,
            "skills": affected_skills,
            "packs": affected_packs,
            "risk_factors": risk_factors,
        }

        classification = ChangeClassification(
            classification_id=f"cc-{self._counter:04d}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            change_description=change_description,
            risk_level=risk_level,
            affected_contracts=affected_contracts,
            affected_skills=affected_skills,
            affected_packs=affected_packs,
            impact_matrix=impact_matrix,
            requires_migration=requires_migration,
            requires_review=requires_review,
        )

        self._persist(classification)
        return classification

    def _compute_risk(self, risk_factors: list[str]) -> str:
        if "contract_change" in risk_factors:
            return "critical"
        if "runtime_change" in risk_factors or "config_change" in risk_factors:
            return "high"
        if "skill_change" in risk_factors or "pack_change" in risk_factors:
            return "medium"
        return "low"

    def _persist(self, classification: ChangeClassification) -> Path:
        path = CHANGE_CLASS_DIR / f"{classification.classification_id}.json"
        path.write_text(
            json.dumps(classification.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )
        return path


class GoldenTraceManager:
    """Manages golden traces for regression testing."""

    def __init__(self) -> None:
        self._traces: list[GoldenTrace] = []

    def create_trace(
        self,
        name: str,
        description: str,
        mode: str,
        input_data: dict[str, Any],
        expected_output: dict[str, Any],
        version: str = "1.0.0",
    ) -> GoldenTrace:
        trace = GoldenTrace(
            trace_id=f"gt-{len(self._traces):04d}",
            name=name,
            description=description,
            mode=mode,
            input_data=input_data,
            expected_output=expected_output,
            created=datetime.now(timezone.utc).isoformat(),
            version=version,
        )
        self._traces.append(trace)
        self._persist(trace)
        return trace

    def get_by_mode(self, mode: str) -> list[GoldenTrace]:
        return [t for t in self._traces if t.mode == mode]

    def get_by_name(self, name: str) -> GoldenTrace | None:
        for t in self._traces:
            if t.name == name:
                return t
        return None

    def _persist(self, trace: GoldenTrace) -> Path:
        path = GOLDEN_DIR / f"{trace.trace_id}.json"
        path.write_text(
            json.dumps(trace.to_dict(), indent=2, default=str), encoding="utf-8"
        )
        return path


def create_golden_traces() -> list[dict[str, Any]]:
    """Create initial golden traces for critical workflows."""
    manager = GoldenTraceManager()

    manager.create_trace(
        name="explore_basic",
        description="Basic repository exploration",
        mode="explore",
        input_data={
            "task": "Explore specs directory",
            "target_path": ".internal/specs",
        },
        expected_output={
            "findings": [],
            "file_map": {},
            "summary": "Exploration complete",
        },
    )

    manager.create_trace(
        name="reviewer_contract_check",
        description="Contract compliance review",
        mode="reviewer",
        input_data={"review_scope": {}, "applicable_specs": ["orchestration-contract"]},
        expected_output={"status": "approved", "findings": [], "compliance_report": {}},
    )

    manager.create_trace(
        name="orchestrator_plan",
        description="Multi-agent workflow planning",
        mode="orchestrator",
        input_data={"workflow": {}, "run_id": "test"},
        expected_output={
            "run_result": {},
            "evidence_trail": [],
            "execution_summary": {},
        },
    )

    return [t.to_dict() for t in manager._traces]


if __name__ == "__main__":
    import sys

    command = sys.argv[1] if len(sys.argv) > 1 else "golden"

    if command == "replay":
        run_id = sys.argv[2] if len(sys.argv) > 2 else ""
        engine = ReplayEngine()
        result = engine.replay_run(run_id)
        print(f"[{result.status.upper()}] Replay: {result.replay_id}")
        print(f"  Original: {result.original_run_id}")
        print(f"  Steps: {result.steps_replayed}/{result.steps_total}")
        print(f"  Integrity: {'MATCH' if result.integrity_match else 'MISMATCH'}")
        for d in result.discrepancies:
            print(f"  - {d}")

    elif command == "classify":
        desc = sys.argv[2] if len(sys.argv) > 2 else "Update mode contract"
        files = (
            sys.argv[3:]
            if len(sys.argv) > 3
            else [".internal/specs/modes/explore.yaml"]
        )
        classifier = ChangeClassifier()
        result = classifier.classify(desc, files)
        print(
            f"[{result.risk_level.upper()}] Classification: {result.classification_id}"
        )
        print(f"  Description: {result.change_description}")
        print(f"  Contracts: {result.affected_contracts}")
        print(f"  Skills: {result.affected_skills}")
        print(f"  Requires review: {result.requires_review}")
        print(f"  Requires migration: {result.requires_migration}")

    elif command == "golden":
        traces = create_golden_traces()
        print(f"[OK] Created {len(traces)} golden traces")
        for t in traces:
            print(f"  {t['trace_id']}: {t['name']} ({t['mode']})")

    else:
        print(f"Unknown command: {command}")
        print("Usage: python replay_engine.py [replay|classify|golden] [args...]")
        sys.exit(1)
