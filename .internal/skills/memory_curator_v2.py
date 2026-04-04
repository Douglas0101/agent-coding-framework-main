"""
Skill: memory_curator_v2 (orchestrator mode)

Manages the three-tier memory model (operational_context, session_state,
structural_memory) with selective compression, evidence preservation,
and lifecycle management.
"""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass
class MemoryEntry:
    entry_id: str
    tier: str  # operational_context, session_state, structural_memory
    content: str
    producer: str
    timestamp: str
    compressible: bool = True
    evidence_refs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryTier:
    name: str
    entries: list[MemoryEntry] = field(default_factory=list)
    max_entries: int = 100
    total_size: int = 0
    compression_policy: str = "aggressive"  # none, aggressive, conservative

    @property
    def is_full(self) -> bool:
        return len(self.entries) >= self.max_entries

    def add_entry(self, entry: MemoryEntry) -> bool:
        if self.is_full:
            return False
        self.entries.append(entry)
        self.total_size += len(entry.content.encode("utf-8"))
        return True

    def compress(self, max_entries: int | None = None) -> list[MemoryEntry]:
        limit = max_entries or self.max_entries // 2
        if len(self.entries) <= limit:
            return []

        evictable = [e for e in self.entries if e.compressible]
        preserved = [e for e in self.entries if not e.compressible]

        to_remove = evictable[: len(evictable) - (limit - len(preserved))]
        removed = list(to_remove)

        self.entries = preserved + evictable[len(to_remove) :]
        self.total_size = sum(len(e.content.encode("utf-8")) for e in self.entries)
        return removed

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "entry_count": len(self.entries),
            "total_size": self.total_size,
            "max_entries": self.max_entries,
            "is_full": self.is_full,
            "compression_policy": self.compression_policy,
            "entries": [asdict(e) for e in self.entries],
        }


@dataclass
class MemoryCuratorReport:
    run_id: str
    timestamp: str
    tiers: dict[str, MemoryTier] = field(default_factory=dict)
    total_entries: int = 0
    total_size: int = 0
    compressed_entries: int = 0
    evidence_preserved: int = 0
    integrity_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "total_entries": self.total_entries,
            "total_size": self.total_size,
            "compressed_entries": self.compressed_entries,
            "evidence_preserved": self.evidence_preserved,
            "tiers": {k: v.to_dict() for k, v in self.tiers.items()},
            "integrity_hash": self.integrity_hash,
        }


class MemoryCuratorV2:
    """Three-tier memory management with selective compression."""

    def __init__(self, run_id: str | None = None) -> None:
        self.run_id = (
            run_id or f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        )
        self._entry_counter = 0
        self._compressed_count = 0
        self._evidence_count = 0

        self.tiers: dict[str, MemoryTier] = {
            "operational_context": MemoryTier(
                name="operational_context",
                max_entries=50,
                compression_policy="aggressive",
            ),
            "session_state": MemoryTier(
                name="session_state",
                max_entries=100,
                compression_policy="conservative",
            ),
            "structural_memory": MemoryTier(
                name="structural_memory",
                max_entries=200,
                compression_policy="none",
            ),
        }

    def store(
        self,
        tier: str,
        content: str,
        producer: str,
        evidence_refs: list[str] | None = None,
        compressible: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry | None:
        if tier not in self.tiers:
            return None

        self._entry_counter += 1
        entry = MemoryEntry(
            entry_id=f"mem-{self._entry_counter:06d}",
            tier=tier,
            content=content,
            producer=producer,
            timestamp=datetime.now(timezone.utc).isoformat(),
            compressible=compressible,
            evidence_refs=evidence_refs or [],
            metadata=metadata or {},
        )

        if evidence_refs:
            self._evidence_count += len(evidence_refs)

        success = self.tiers[tier].add_entry(entry)
        if not success:
            self._compress_tier(tier)
            success = self.tiers[tier].add_entry(entry)

        return entry if success else None

    def retrieve(self, tier: str, entry_id: str) -> MemoryEntry | None:
        if tier not in self.tiers:
            return None
        for entry in self.tiers[tier].entries:
            if entry.entry_id == entry_id:
                return entry
        return None

    def retrieve_all(self, tier: str) -> list[MemoryEntry]:
        if tier not in self.tiers:
            return []
        return list(self.tiers[tier].entries)

    def compress_tier(
        self, tier: str, max_entries: int | None = None
    ) -> list[MemoryEntry]:
        if tier not in self.tiers:
            return []
        removed = self.tiers[tier].compress(max_entries)
        self._compressed_count += len(removed)
        return removed

    def _compress_tier(self, tier: str) -> list[MemoryEntry]:
        return self.compress_tier(tier)

    def get_evidence_refs(self) -> list[str]:
        refs: list[str] = []
        for tier in self.tiers.values():
            for entry in tier.entries:
                refs.extend(entry.evidence_refs)
        return list(set(refs))

    def generate_report(self) -> MemoryCuratorReport:
        total_entries = sum(len(t.entries) for t in self.tiers.values())
        total_size = sum(t.total_size for t in self.tiers.values())

        report = MemoryCuratorReport(
            run_id=self.run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            tiers=self.tiers,
            total_entries=total_entries,
            total_size=total_size,
            compressed_entries=self._compressed_count,
            evidence_preserved=self._evidence_count,
        )
        report.integrity_hash = self._compute_hash(report)
        return report

    def _compute_hash(self, report: MemoryCuratorReport) -> str:
        content = json.dumps(
            {
                "run_id": report.run_id,
                "total_entries": report.total_entries,
                "compressed_entries": report.compressed_entries,
                "evidence_preserved": report.evidence_preserved,
            },
            sort_keys=True,
            default=str,
        )
        return f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"


def curate_memory(
    run_id: str | None = None,
    operations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    curator = MemoryCuratorV2(run_id=run_id)

    if operations:
        for op in operations:
            curator.store(
                tier=op.get("tier", "operational_context"),
                content=op.get("content", ""),
                producer=op.get("producer", "unknown"),
                evidence_refs=op.get("evidence_refs"),
                compressible=op.get("compressible", True),
                metadata=op.get("metadata"),
            )

    report = curator.generate_report()
    return report.to_dict()


if __name__ == "__main__":
    import sys

    run_id = sys.argv[1] if len(sys.argv) > 1 else None
    curator = MemoryCuratorV2(run_id=run_id)

    curator.store(
        tier="operational_context",
        content="Current task: implement contract verifier",
        producer="orchestrator",
    )
    curator.store(
        tier="session_state",
        content="Run progress: 3 of 5 steps completed",
        producer="orchestrator",
    )
    curator.store(
        tier="structural_memory",
        content="Mode contract: explore v1.2.0",
        producer="system",
        compressible=False,
        evidence_refs=["evidence-001"],
    )

    report = curator.generate_report()
    print(f"[OK] Memory curator: {report.run_id}")
    print(f"  Total entries: {report.total_entries}")
    print(f"  Total size: {report.total_size}B")
    print(f"  Evidence preserved: {report.evidence_preserved}")

    for tier_name, tier in report.tiers.items():
        print(f"  {tier_name}: {tier['entry_count']} entries, {tier['total_size']}B")
