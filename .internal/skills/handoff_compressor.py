"""
Skill: handoff_compressor (orchestrator mode)

Implements selective compression modes for handoff payloads.
Supports none, summary, summary+refs, delta compression.
Provides rehydration with reference resolution.
"""

from __future__ import annotations

import json
import hashlib
import zlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass
class CompressedPayload:
    payload_id: str
    compression_mode: str  # none, summary, summary+refs, delta
    original_size: int
    compressed_size: int
    compression_ratio: float
    content: str = ""
    refs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "payload_id": self.payload_id,
            "compression_mode": self.compression_mode,
            "original_size": self.original_size,
            "compressed_size": self.compressed_size,
            "compression_ratio": self.compression_ratio,
            "refs_count": len(self.refs),
            "metadata": self.metadata,
        }


@dataclass
class RehydrationResult:
    payload_id: str
    success: bool
    reconstructed_context: str
    resolved_refs: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HandoffCompressionReport:
    run_id: str
    timestamp: str
    payloads: list[CompressedPayload] = field(default_factory=list)
    total_original_size: int = 0
    total_compressed_size: int = 0
    avg_compression_ratio: float = 0.0
    integrity_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "payload_count": len(self.payloads),
            "total_original_size": self.total_original_size,
            "total_compressed_size": self.total_compressed_size,
            "avg_compression_ratio": self.avg_compression_ratio,
            "payloads": [p.to_dict() for p in self.payloads],
            "integrity_hash": self.integrity_hash,
        }


class HandoffCompressor:
    """Selective compression for handoff payloads with rehydration."""

    def __init__(self, run_id: str | None = None) -> None:
        self.run_id = (
            run_id or f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        )
        self._payloads: list[CompressedPayload] = []
        self._payload_counter = 0

    def compress(
        self,
        content: str,
        mode: str = "summary+refs",
        refs: list[str] | None = None,
        max_summary_length: int = 500,
        delta_base: str | None = None,
    ) -> CompressedPayload:
        self._payload_counter += 1
        original_size = len(content.encode("utf-8"))

        if mode == "none":
            compressed_content = content
            compressed_size = original_size
        elif mode == "summary":
            compressed_content = self._summarize(content, max_summary_length)
            compressed_size = len(compressed_content.encode("utf-8"))
        elif mode == "summary+refs":
            compressed_content = self._summarize(content, max_summary_length)
            compressed_size = len(compressed_content.encode("utf-8"))
        elif mode == "delta":
            if delta_base:
                compressed_content = self._compute_delta(delta_base, content)
            else:
                compressed_content = content
            compressed_size = len(compressed_content.encode("utf-8"))
        else:
            compressed_content = content
            compressed_size = original_size

        ratio = compressed_size / original_size if original_size > 0 else 1.0

        payload = CompressedPayload(
            payload_id=f"payload-{self._payload_counter:04d}",
            compression_mode=mode,
            original_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=round(ratio, 4),
            content=compressed_content,
            refs=refs or [],
            metadata={
                "original_length": len(content),
                "compressed_length": len(compressed_content),
                "refs_count": len(refs or []),
            },
        )
        self._payloads.append(payload)
        return payload

    def rehydrate(
        self,
        payload: CompressedPayload,
        ref_resolver: dict[str, str] | None = None,
        delta_base: str | None = None,
    ) -> RehydrationResult:
        errors: list[str] = []
        resolved: list[str] = []

        if payload.compression_mode == "none":
            return RehydrationResult(
                payload_id=payload.payload_id,
                success=True,
                reconstructed_context=payload.content,
            )

        if payload.compression_mode in ("summary", "summary+refs"):
            base_content = payload.content

            if payload.compression_mode == "summary+refs" and payload.refs:
                if ref_resolver:
                    for ref in payload.refs:
                        if ref in ref_resolver:
                            resolved.append(ref_resolver[ref])
                        else:
                            errors.append(f"Unresolvable reference: {ref}")

                reconstructed = base_content
                for ref_content in resolved:
                    reconstructed += f"\n\n--- Reference: {ref_content[:200]}..."
                return RehydrationResult(
                    payload_id=payload.payload_id,
                    success=not errors,
                    reconstructed_context=reconstructed,
                    resolved_refs=resolved,
                    errors=errors,
                )

            return RehydrationResult(
                payload_id=payload.payload_id,
                success=True,
                reconstructed_context=base_content,
            )

        if payload.compression_mode == "delta" and delta_base:
            reconstructed = self._apply_delta(delta_base, payload.content)
            return RehydrationResult(
                payload_id=payload.payload_id,
                success=True,
                reconstructed_context=reconstructed,
            )

        return RehydrationResult(
            payload_id=payload.payload_id,
            success=False,
            reconstructed_context="",
            errors=["Unsupported compression mode or missing delta base"],
        )

    def generate_report(self) -> HandoffCompressionReport:
        total_original = sum(p.original_size for p in self._payloads)
        total_compressed = sum(p.compressed_size for p in self._payloads)
        avg_ratio = total_compressed / total_original if total_original > 0 else 1.0

        report = HandoffCompressionReport(
            run_id=self.run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            payloads=self._payloads,
            total_original_size=total_original,
            total_compressed_size=total_compressed,
            avg_compression_ratio=round(avg_ratio, 4),
        )
        report.integrity_hash = self._compute_hash(report)
        return report

    @staticmethod
    def _summarize(content: str, max_length: int = 500) -> str:
        lines = content.splitlines()
        if len(lines) <= 5:
            return content

        first_lines = lines[:3]
        last_lines = lines[-2:]
        summary = "\n".join(first_lines)
        summary += f"\n\n... [{len(lines) - 5} lines omitted] ...\n\n"
        summary += "\n".join(last_lines)

        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
        return summary

    @staticmethod
    def _compute_delta(original: str, modified: str) -> str:
        orig_lines = set(original.splitlines())
        mod_lines = set(modified.splitlines())
        added = mod_lines - orig_lines
        removed = orig_lines - mod_lines

        delta = ""
        for line in sorted(removed):
            delta += f"- {line}\n"
        for line in sorted(added):
            delta += f"+ {line}\n"
        return delta or "(no changes)"

    @staticmethod
    def _apply_delta(base: str, delta: str) -> str:
        base_lines = base.splitlines()
        result_lines = list(base_lines)

        for line in delta.splitlines():
            if line.startswith("- "):
                content = line[2:]
                if content in result_lines:
                    result_lines.remove(content)
            elif line.startswith("+ "):
                result_lines.append(line[2:])

        return "\n".join(result_lines)

    def _compute_hash(self, report: HandoffCompressionReport) -> str:
        content = json.dumps(
            {
                "run_id": report.run_id,
                "payload_count": report.payload_count,
                "avg_compression_ratio": report.avg_compression_ratio,
            },
            sort_keys=True,
            default=str,
        )
        return f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"


def compress_handoff(
    content: str,
    mode: str = "summary+refs",
    refs: list[str] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    compressor = HandoffCompressor(run_id=run_id)
    payload = compressor.compress(content, mode, refs)
    return payload.to_dict()


if __name__ == "__main__":
    import sys

    run_id = sys.argv[1] if len(sys.argv) > 1 else None
    content = "\n".join(
        [f"Line {i}: Some content for testing compression" for i in range(50)]
    )

    compressor = HandoffCompressor(run_id=run_id)

    for mode in ["none", "summary", "summary+refs", "delta"]:
        payload = compressor.compress(content, mode=mode)
        print(
            f"[{mode}] Original: {payload.original_size}B, "
            f"Compressed: {payload.compressed_size}B, "
            f"Ratio: {payload.compression_ratio:.4f}"
        )

    report = compressor.generate_report()
    print(f"\n[OK] Compression report: {report.run_id}")
    print(f"  Total payloads: {report.payload_count}")
    print(f"  Avg compression ratio: {report.avg_compression_ratio:.4f}")
