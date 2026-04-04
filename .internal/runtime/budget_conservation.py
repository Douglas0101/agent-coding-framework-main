"""
Budget Conservation — Hierarchical enforcement, compression, and rehydration.

Implements budget conservation law (sum(children) <= parent), selective
compression modes, and on-demand rehydration for handoff payloads.
"""

from __future__ import annotations

import json
import hashlib
import zlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INTERNAL_DIR = Path(__file__).resolve().parent.parent


@dataclass
class BudgetAllocation:
    """Budget allocation for a single step or child mode."""

    step_id: str
    mode: str
    allocated: dict[str, int] = field(default_factory=dict)
    consumed: dict[str, int] = field(default_factory=dict)
    status: str = "allocated"  # allocated, in_progress, completed, exceeded, exhausted

    @property
    def remaining(self) -> dict[str, int]:
        return {
            k: self.allocated.get(k, 0) - self.consumed.get(k, 0)
            for k in self.allocated
        }

    @property
    def utilization(self) -> dict[str, float]:
        result = {}
        for k in self.allocated:
            alloc = self.allocated[k]
            cons = self.consumed.get(k, 0)
            result[k] = round(cons / alloc, 3) if alloc > 0 else 0.0
        return result

    @property
    def is_exceeded(self) -> bool:
        return any(
            self.consumed.get(k, 0) > self.allocated.get(k, 0) for k in self.allocated
        )

    @property
    def is_exhausted(self) -> bool:
        return any(
            self.consumed.get(k, 0) >= self.allocated.get(k, 0) * 0.95
            for k in self.allocated
        )

    def consume(self, dimension: str, amount: int) -> tuple[bool, str]:
        """Consume budget. Returns (success, message)."""
        remaining = self.allocated.get(dimension, 0) - self.consumed.get(dimension, 0)
        if amount > remaining:
            return (
                False,
                f"Budget exceeded for {dimension}: need {amount}, have {remaining}",
            )
        self.consumed[dimension] = self.consumed.get(dimension, 0) + amount
        if self.is_exhausted:
            self.status = "exhausted"
        elif self.is_exceeded:
            self.status = "exceeded"
        return True, ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "mode": self.mode,
            "allocated": self.allocated,
            "consumed": self.consumed,
            "remaining": self.remaining,
            "utilization": self.utilization,
            "status": self.status,
        }


@dataclass
class CompressedPayload:
    """Compressed handoff payload."""

    payload_id: str
    compression_mode: str  # none, summary, summary+refs, delta
    original_size: int
    compressed_size: int
    compression_ratio: float
    summary: str = ""
    refs: list[str] = field(default_factory=list)
    delta_from: str = ""
    raw_compressed: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RehydrationResult:
    """Result of rehydrating a compressed payload."""

    payload_id: str
    success: bool
    reconstructed_context: str = ""
    resolved_refs: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


BUDGET_DIMENSIONS = [
    "max_input_tokens",
    "max_output_tokens",
    "max_context_tokens",
    "max_retrieval_chunks",
    "max_iterations",
    "max_handoffs",
    "timeout_seconds",
]

COORDINATION_OVERHEAD = 0.10  # 10% overhead for coordination


class BudgetEnforcer:
    """Enforces hierarchical budget conservation: sum(children) <= parent * (1 - overhead)."""

    def __init__(self, run_id: str | None = None) -> None:
        self.run_id = (
            run_id or f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        )
        self._allocations: dict[str, BudgetAllocation] = {}
        self._parent_budget: dict[str, int] = {}

    def set_parent_budget(self, budget: dict[str, int]) -> None:
        self._parent_budget = budget

    def allocate_children(
        self,
        children: list[dict[str, Any]],
    ) -> tuple[bool, list[str]]:
        """Allocate budget to children. Returns (success, errors)."""
        if not self._parent_budget:
            return False, ["No parent budget set"]

        errors: list[str] = []
        total_consumption: dict[str, int] = {k: 0 for k in self._parent_budget}

        for child in children:
            step_id = child.get("step_id", f"step-{len(self._allocations):04d}")
            mode = child.get("mode", "unknown")
            child_budget = child.get("budget", {})

            allocation = BudgetAllocation(
                step_id=step_id,
                mode=mode,
                allocated={k: child_budget.get(k, 0) for k in BUDGET_DIMENSIONS},
            )
            self._allocations[step_id] = allocation

            for dim in BUDGET_DIMENSIONS:
                total_consumption[dim] = total_consumption.get(
                    dim, 0
                ) + child_budget.get(dim, 0)

        for dim in BUDGET_DIMENSIONS:
            parent_val = self._parent_budget.get(dim, 0)
            child_total = total_consumption.get(dim, 0)
            max_allowed = int(parent_val * (1 - COORDINATION_OVERHEAD))

            if child_total > max_allowed and parent_val > 0:
                errors.append(
                    f"Budget conservation violated for {dim}: "
                    f"children={child_total}, max_allowed={max_allowed} "
                    f"(parent={parent_val}, overhead={COORDINATION_OVERHEAD:.0%})"
                )

        if errors:
            return False, errors
        return True, []

    def consume(self, step_id: str, dimension: str, amount: int) -> tuple[bool, str]:
        """Consume budget for a step. Returns (success, message)."""
        allocation = self._allocations.get(step_id)
        if not allocation:
            return False, f"Unknown step: {step_id}"
        return allocation.consume(dimension, amount)

    def get_status(self, step_id: str) -> dict[str, Any] | None:
        allocation = self._allocations.get(step_id)
        if not allocation:
            return None
        return allocation.to_dict()

    def get_all_status(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "parent_budget": self._parent_budget,
            "children": {
                sid: alloc.to_dict() for sid, alloc in self._allocations.items()
            },
            "coordination_overhead": COORDINATION_OVERHEAD,
        }


class CompressionEngine:
    """Compresses and decompresses handoff payloads."""

    @staticmethod
    def compress(
        content: str,
        mode: str = "summary+refs",
        refs: list[str] | None = None,
        delta_from: str = "",
        previous_content: str = "",
    ) -> CompressedPayload:
        original_size = len(content.encode("utf-8"))
        summary = ""
        raw_compressed = ""

        if mode == "none":
            raw_compressed = content
            summary = content[:500]
        elif mode == "summary":
            summary = CompressionEngine._summarize(content)
            raw_compressed = zlib.compress(summary.encode()).hex()
        elif mode == "summary+refs":
            summary = CompressionEngine._summarize(content)
            raw_compressed = zlib.compress(summary.encode()).hex()
        elif mode == "delta":
            if previous_content:
                delta = CompressionEngine._compute_delta(previous_content, content)
                if delta == "(no changes)":
                    summary = "(no changes)"
                else:
                    summary = delta[:500]
                raw_compressed = zlib.compress(delta.encode()).hex()
            else:
                summary = CompressionEngine._summarize(content)
                raw_compressed = zlib.compress(summary.encode()).hex()

        compressed_size = len(raw_compressed)
        ratio = round(compressed_size / original_size, 4) if original_size > 0 else 0.0

        return CompressedPayload(
            payload_id=f"cp-{hashlib.sha256(content[:100].encode()).hexdigest()[:8]}",
            compression_mode=mode,
            original_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=ratio,
            summary=summary,
            refs=refs or [],
            delta_from=delta_from,
            raw_compressed=raw_compressed,
        )

    @staticmethod
    def decompress(payload: CompressedPayload) -> str:
        if payload.compression_mode == "none":
            return payload.raw_compressed
        try:
            decompressed = zlib.decompress(
                bytes.fromhex(payload.raw_compressed)
            ).decode()
            return decompressed
        except (ValueError, zlib.error) as exc:
            return f"[DECOMPRESSION ERROR: {exc}]"

    @staticmethod
    def rehydrate(
        payload: CompressedPayload,
        ref_resolver: dict[str, str] | None = None,
    ) -> RehydrationResult:
        refs = payload.refs
        resolved: list[str] = []
        errors: list[str] = []

        base_content = CompressionEngine.decompress(payload)

        if ref_resolver is not None:
            for ref in refs:
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


if __name__ == "__main__":
    import sys

    command = sys.argv[1] if len(sys.argv) > 1 else "budget"

    if command == "budget":
        enforcer = BudgetEnforcer(run_id="test-budget-001")
        parent_budget = {
            "max_input_tokens": 32000,
            "max_output_tokens": 48000,
            "max_context_tokens": 64000,
            "max_iterations": 50,
            "max_handoffs": 10,
            "timeout_seconds": 3600,
        }
        enforcer.set_parent_budget(parent_budget)

        children = [
            {
                "step_id": "step-01",
                "mode": "explore",
                "budget": {
                    "max_input_tokens": 8000,
                    "max_output_tokens": 12000,
                    "max_context_tokens": 16000,
                    "max_iterations": 15,
                    "max_handoffs": 2,
                    "timeout_seconds": 300,
                },
            },
            {
                "step_id": "step-02",
                "mode": "autocoder",
                "budget": {
                    "max_input_tokens": 16000,
                    "max_output_tokens": 24000,
                    "max_context_tokens": 32000,
                    "max_iterations": 25,
                    "max_handoffs": 3,
                    "timeout_seconds": 900,
                },
            },
        ]

        success, errors = enforcer.allocate_children(children)
        status = "PASS" if success else "FAIL"
        print(f"[{status}] Budget conservation check")
        for e in errors:
            print(f"  ERROR: {e}")

        if success:
            for step_id in ["step-01", "step-02"]:
                s = enforcer.get_status(step_id)
                if s:
                    print(
                        f"  {step_id} ({s['mode']}): allocated, utilization={s['utilization']}"
                    )

    elif command == "compress":
        engine = CompressionEngine()
        content = "\n".join(
            [f"Line {i}: Some content for testing compression" for i in range(50)]
        )

        for mode in ["none", "summary", "summary+refs", "delta"]:
            payload = engine.compress(content, mode=mode)
            print(
                f"[{mode}] Original: {payload.original_size}B, "
                f"Compressed: {payload.compressed_size}B, "
                f"Ratio: {payload.compression_ratio:.4f}"
            )

    elif command == "rehydrate":
        engine = CompressionEngine()
        content = "Full context with important details about the task."
        payload = engine.compress(
            content, mode="summary+refs", refs=["ref-001", "ref-002"]
        )

        ref_resolver = {
            "ref-001": "Evidence: contract verification passed",
            "ref-002": "Evidence: policy scan clean",
        }
        result = engine.rehydrate(payload, ref_resolver=ref_resolver)
        print(f"[{'OK' if result.success else 'FAIL'}] Rehydration")
        print(f"  Resolved refs: {len(result.resolved_refs)}")
        print(f"  Errors: {result.errors}")
        print(f"  Context preview: {result.reconstructed_context[:100]}...")

    else:
        print(f"Unknown command: {command}")
        print("Usage: python budget_conservation.py [budget|compress|rehydrate]")
        sys.exit(1)
