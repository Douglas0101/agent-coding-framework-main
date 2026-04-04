"""
Skill: budget_allocator (orchestrator mode)

Manages hierarchical budget allocation across workflow steps.
Enforces conservation law: sum(children) <= parent.
Provides real-time tracking, utilization metrics, and overflow prevention.
"""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any

BUDGET_DIMENSIONS = [
    "max_input_tokens",
    "max_output_tokens",
    "max_context_tokens",
    "max_iterations",
    "max_handoffs",
    "timeout_seconds",
]


@dataclass
class StepBudget:
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

    def consume(self, dimension: str, amount: int) -> tuple[bool, str]:
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
class BudgetAllocationReport:
    run_id: str
    timestamp: str
    parent_budget: dict[str, int] = field(default_factory=dict)
    children: list[StepBudget] = field(default_factory=list)
    total_allocated: dict[str, int] = field(default_factory=dict)
    conservation_violations: list[str] = field(default_factory=list)
    overall_status: str = "valid"  # valid, warning, violated
    integrity_hash: str = ""

    @property
    def is_valid(self) -> bool:
        return len(self.conservation_violations) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "parent_budget": self.parent_budget,
            "children": [c.to_dict() for c in self.children],
            "total_allocated": self.total_allocated,
            "conservation_violations": self.conservation_violations,
            "overall_status": self.overall_status,
            "is_valid": self.is_valid,
            "integrity_hash": self.integrity_hash,
        }


class BudgetAllocator:
    """Hierarchical budget allocation with conservation enforcement."""

    def __init__(self, run_id: str | None = None) -> None:
        self.run_id = (
            run_id or f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        )
        self._parent_budget: dict[str, int] = {}
        self._children: dict[str, StepBudget] = {}
        self._violations: list[str] = []

    def set_parent_budget(self, budget: dict[str, int]) -> None:
        self._parent_budget = budget

    def allocate_children(
        self, children: list[dict[str, Any]], overhead_pct: float = 0.10
    ) -> BudgetAllocationReport:
        self._violations = []
        self._children = {}

        total_allocated: dict[str, int] = {}
        for dim in BUDGET_DIMENSIONS:
            total_allocated[dim] = 0

        for child in children:
            step_id = child["step_id"]
            mode = child["mode"]
            child_budget = child.get("budget", {})

            step_budget = StepBudget(
                step_id=step_id,
                mode=mode,
                allocated=child_budget,
            )
            self._children[step_id] = step_budget

            for dim in BUDGET_DIMENSIONS:
                total_allocated[dim] = total_allocated.get(dim, 0) + child_budget.get(
                    dim, 0
                )

        for dim in BUDGET_DIMENSIONS:
            parent_val = self._parent_budget.get(dim, 0)
            child_total = total_allocated.get(dim, 0)
            threshold = parent_val * (1 + overhead_pct) if parent_val > 0 else 0

            if parent_val > 0 and child_total > threshold:
                self._violations.append(
                    f"Conservation violated for {dim}: children={child_total} > parent*1.10={threshold}"
                )

        overall_status = "valid"
        if self._violations:
            overall_status = "violated"
        elif any(
            total_allocated.get(d, 0) > self._parent_budget.get(d, 0) * 0.9
            for d in BUDGET_DIMENSIONS
            if self._parent_budget.get(d, 0) > 0
        ):
            overall_status = "warning"

        report = BudgetAllocationReport(
            run_id=self.run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            parent_budget=self._parent_budget,
            children=list(self._children.values()),
            total_allocated=total_allocated,
            conservation_violations=self._violations,
            overall_status=overall_status,
        )
        report.integrity_hash = self._compute_hash(report)
        return report

    def consume(self, step_id: str, dimension: str, amount: int) -> tuple[bool, str]:
        if step_id not in self._children:
            return False, f"Unknown step: {step_id}"
        return self._children[step_id].consume(dimension, amount)

    def get_status(self, step_id: str) -> dict[str, Any] | None:
        if step_id not in self._children:
            return None
        return self._children[step_id].to_dict()

    def get_utilization_summary(self) -> dict[str, Any]:
        summary = {}
        for step_id, budget in self._children.items():
            summary[step_id] = {
                "mode": budget.mode,
                "status": budget.status,
                "utilization": budget.utilization,
            }
        return summary

    def _compute_hash(self, report: BudgetAllocationReport) -> str:
        content = json.dumps(
            {
                "run_id": report.run_id,
                "parent_budget": report.parent_budget,
                "children_count": len(report.children),
                "violations": report.conservation_violations,
            },
            sort_keys=True,
            default=str,
        )
        return f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"


def allocate_budget(
    parent_budget: dict[str, int],
    children: list[dict[str, Any]],
    run_id: str | None = None,
    overhead_pct: float = 0.10,
) -> dict[str, Any]:
    allocator = BudgetAllocator(run_id=run_id)
    allocator.set_parent_budget(parent_budget)
    report = allocator.allocate_children(children, overhead_pct)
    return report.to_dict()


if __name__ == "__main__":
    import sys

    run_id = sys.argv[1] if len(sys.argv) > 1 else None
    parent = {
        "max_input_tokens": 32000,
        "max_output_tokens": 48000,
        "max_context_tokens": 64000,
        "max_iterations": 50,
        "max_handoffs": 10,
        "timeout_seconds": 3600,
    }
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

    result = allocate_budget(parent, children, run_id=run_id)
    status = "VALID" if result["is_valid"] else "VIOLATED"
    print(f"[{status}] Budget allocation: {result['run_id']}")
    print(f"  Parent budget: {result['parent_budget']}")
    print(f"  Children: {len(result['children'])}")
    print(f"  Violations: {len(result['conservation_violations'])}")
    for v in result["conservation_violations"]:
        print(f"    - {v}")
