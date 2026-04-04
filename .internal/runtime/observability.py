"""
Observability — Artifact Ledger, Evidence Store, and Handoff History.

Provides structured storage and retrieval of execution artifacts,
evidence records, and handoff logs for auditability and replay.
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
LEDGER_DIR = ARTIFACTS_DIR / "ledger"
EVIDENCE_DIR = ARTIFACTS_DIR / "evidence"
HANDOFF_DIR = ARTIFACTS_DIR / "handoffs"

for d in (LEDGER_DIR, EVIDENCE_DIR, HANDOFF_DIR):
    d.mkdir(parents=True, exist_ok=True)


@dataclass
class ArtifactRecord:
    artifact_id: str
    run_id: str
    timestamp: str
    artifact_type: str  # code, report, plan, spec, config
    file_path: str
    producer: str
    integrity_hash: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceRecord:
    evidence_id: str
    run_id: str
    timestamp: str
    evidence_type: str  # operational, session, structural, artifact
    producer: str
    content_ref: str
    integrity_hash: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HandoffRecord:
    handoff_id: str
    run_id: str
    timestamp: str
    producer_agent: str
    consumer_agent: str
    spec_id: str
    spec_version: str
    compression_mode: str
    payload_size: int
    evidence_refs: list[str] = field(default_factory=list)
    integrity_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ArtifactLedger:
    """Append-only ledger of execution artifacts."""

    def __init__(self) -> None:
        self._records: list[ArtifactRecord] = []
        self._index_path = LEDGER_DIR / "index.jsonl"

    def record(
        self,
        run_id: str,
        artifact_type: str,
        file_path: str,
        producer: str,
        metadata: dict[str, Any] | None = None,
    ) -> ArtifactRecord:
        content = ""
        fp = Path(file_path)
        if fp.exists():
            content = fp.read_text(encoding="utf-8", errors="replace")

        record = ArtifactRecord(
            artifact_id=f"art-{len(self._records):06d}",
            run_id=run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            artifact_type=artifact_type,
            file_path=file_path,
            producer=producer,
            integrity_hash=f"sha256:{hashlib.sha256(content.encode()).hexdigest()}",
            metadata=metadata or {},
        )
        self._records.append(record)
        self._append_to_index(record)
        return record

    def get_by_run(self, run_id: str) -> list[ArtifactRecord]:
        return [r for r in self._records if r.run_id == run_id]

    def get_by_type(self, artifact_type: str) -> list[ArtifactRecord]:
        return [r for r in self._records if r.artifact_type == artifact_type]

    def _append_to_index(self, record: ArtifactRecord) -> None:
        with open(self._index_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record.to_dict(), default=str) + "\n")


class EvidenceStore:
    """Structured storage for evidence records."""

    def __init__(self) -> None:
        self._records: list[EvidenceRecord] = []
        self._index_path = EVIDENCE_DIR / "index.jsonl"

    def store(
        self,
        run_id: str,
        evidence_type: str,
        producer: str,
        content: str,
        content_ref: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> EvidenceRecord:
        if not content_ref:
            content_ref = f"evidence/{run_id}/{len(self._records):06d}.json"

        ev_path = INTERNAL_DIR / "artifacts" / content_ref
        ev_path.parent.mkdir(parents=True, exist_ok=True)
        ev_path.write_text(
            json.dumps({"content": content, "metadata": metadata or {}}, default=str),
            encoding="utf-8",
        )

        record = EvidenceRecord(
            evidence_id=f"ev-{len(self._records):06d}",
            run_id=run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            evidence_type=evidence_type,
            producer=producer,
            content_ref=content_ref,
            integrity_hash=f"sha256:{hashlib.sha256(content.encode()).hexdigest()}",
            metadata=metadata or {},
        )
        self._records.append(record)
        self._append_to_index(record)
        return record

    def get_by_run(self, run_id: str) -> list[EvidenceRecord]:
        return [r for r in self._records if r.run_id == run_id]

    def get_by_type(self, evidence_type: str) -> list[EvidenceRecord]:
        return [r for r in self._records if r.evidence_type == evidence_type]

    def _append_to_index(self, record: EvidenceRecord) -> None:
        with open(self._index_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record.to_dict(), default=str) + "\n")


class HandoffHistory:
    """Tracks all handoffs between agents during execution."""

    def __init__(self) -> None:
        self._records: list[HandoffRecord] = []
        self._index_path = HANDOFF_DIR / "index.jsonl"

    def log_handoff(
        self,
        run_id: str,
        producer_agent: str,
        consumer_agent: str,
        spec_id: str,
        spec_version: str,
        compression_mode: str = "summary+refs",
        payload_size: int = 0,
        evidence_refs: list[str] | None = None,
    ) -> HandoffRecord:
        record = HandoffRecord(
            handoff_id=f"ho-{len(self._records):06d}",
            run_id=run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            producer_agent=producer_agent,
            consumer_agent=consumer_agent,
            spec_id=spec_id,
            spec_version=spec_version,
            compression_mode=compression_mode,
            payload_size=payload_size,
            evidence_refs=evidence_refs or [],
        )
        record.integrity_hash = hashlib.sha256(
            json.dumps(record.to_dict(), sort_keys=True, default=str).encode()
        ).hexdigest()
        self._records.append(record)
        self._persist(record)
        self._append_to_index(record)
        return record

    def get_by_run(self, run_id: str) -> list[HandoffRecord]:
        return [r for r in self._records if r.run_id == run_id]

    def get_by_agent(self, agent: str) -> list[HandoffRecord]:
        return [
            r
            for r in self._records
            if r.producer_agent == agent or r.consumer_agent == agent
        ]

    def _persist(self, record: HandoffRecord) -> None:
        path = HANDOFF_DIR / f"{record.handoff_id}.json"
        path.write_text(
            json.dumps(record.to_dict(), indent=2, default=str), encoding="utf-8"
        )

    def _append_to_index(self, record: HandoffRecord) -> None:
        with open(self._index_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record.to_dict(), default=str) + "\n")


class ObservabilityHub:
    """Central observability hub combining ledger, evidence, and handoff tracking."""

    def __init__(self, run_id: str | None = None) -> None:
        self.run_id = (
            run_id or f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        )
        self.ledger = ArtifactLedger()
        self.evidence = EvidenceStore()
        self.handoffs = HandoffHistory()

    def record_artifact(
        self,
        artifact_type: str,
        file_path: str,
        producer: str,
        metadata: dict[str, Any] | None = None,
    ) -> ArtifactRecord:
        return self.ledger.record(
            self.run_id, artifact_type, file_path, producer, metadata
        )

    def store_evidence(
        self,
        evidence_type: str,
        producer: str,
        content: str,
        content_ref: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> EvidenceRecord:
        return self.evidence.store(
            self.run_id, evidence_type, producer, content, content_ref, metadata
        )

    def log_handoff(
        self,
        producer_agent: str,
        consumer_agent: str,
        spec_id: str,
        spec_version: str,
        compression_mode: str = "summary+refs",
        payload_size: int = 0,
        evidence_refs: list[str] | None = None,
    ) -> HandoffRecord:
        return self.handoffs.log_handoff(
            self.run_id,
            producer_agent,
            consumer_agent,
            spec_id,
            spec_version,
            compression_mode,
            payload_size,
            evidence_refs,
        )

    def summary(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "artifacts": len(self.ledger._records),
            "evidence_records": len(self.evidence._records),
            "handoffs": len(self.handoffs._records),
            "ledger_path": str(LEDGER_DIR),
            "evidence_path": str(EVIDENCE_DIR),
            "handoff_path": str(HANDOFF_DIR),
        }


if __name__ == "__main__":
    import sys

    run_id = sys.argv[1] if len(sys.argv) > 1 else None
    hub = ObservabilityHub(run_id=run_id)

    hub.record_artifact(
        "report",
        ".internal/artifacts/baseline-tecnico-2026-04-04.md",
        "agent-coding-framework",
    )
    hub.store_evidence(
        "operational",
        "contract_verifier",
        "All 4 mode contracts verified",
        metadata={"checks": 48},
    )
    hub.store_evidence(
        "operational",
        "policy_enforcer",
        "No security findings",
        metadata={"files_scanned": 8},
    )
    hub.log_handoff(
        "explore", "autocoder", "handoff-contract", "1.0.0", payload_size=3000
    )

    s = hub.summary()
    print(f"[OK] Observability hub: {s['run_id']}")
    print(f"  Artifacts: {s['artifacts']}")
    print(f"  Evidence: {s['evidence_records']}")
    print(f"  Handoffs: {s['handoffs']}")
