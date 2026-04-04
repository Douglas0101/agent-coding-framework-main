"""
Skill: explicit_planner (orchestrator mode)

Produces structured execution plans with step decomposition, budget allocation,
dependency graphs, and risk assessment.
"""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INTERNAL_DIR = Path(__file__).resolve().parent.parent.parent
MODES_DIR = INTERNAL_DIR / "specs" / "modes"


@dataclass
class PlanStep:
    step_id: str
    mode: str
    task: str
    pre_conditions: list[str] = field(default_factory=list)
    post_conditions: list[str] = field(default_factory=list)
    budget: dict[str, int] = field(default_factory=dict)
    fallback_mode: str | None = None


@dataclass
class StepDependency:
    from_step: str
    to_step: str
    dependency_type: str  # sequential, parallel, conditional


@dataclass
class ExecutionPlan:
    plan_id: str
    run_id: str
    timestamp: str
    task: str
    steps: list[PlanStep] = field(default_factory=list)
    dependencies: list[StepDependency] = field(default_factory=list)
    budget_allocation: dict[str, dict[str, int]] = field(default_factory=dict)
    risk_assessment: dict[str, Any] = field(default_factory=dict)
    total_budget: dict[str, int] = field(default_factory=dict)
    integrity_hash: str = ""

    @property
    def is_valid(self) -> bool:
        if not self.steps:
            return False
        step_ids = {s.step_id for s in self.steps}
        for dep in self.dependencies:
            if dep.from_step not in step_ids or dep.to_step not in step_ids:
                return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "task": self.task,
            "is_valid": self.is_valid,
            "steps": [asdict(s) for s in self.steps],
            "dependencies": [asdict(d) for d in self.dependencies],
            "budget_allocation": self.budget_allocation,
            "risk_assessment": self.risk_assessment,
            "total_budget": self.total_budget,
            "integrity_hash": self.integrity_hash,
        }


VALID_MODES = {"explore", "reviewer", "orchestrator", "autocoder"}


class ExplicitPlanner:
    """Produces structured execution plans with budget and dependencies."""

    def __init__(self, run_id: str | None = None) -> None:
        self.run_id = (
            run_id or f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        )
        self._plan_counter = 0

    def plan(
        self,
        task: str,
        available_modes: list[str] | None = None,
        parent_budget: dict[str, int] | None = None,
        constraints: list[str] | None = None,
    ) -> ExecutionPlan:
        self._plan_counter += 1
        plan_id = f"plan-{self._plan_counter:04d}"

        if available_modes is None:
            available_modes = list(VALID_MODES)
        if parent_budget is None:
            parent_budget = {
                "max_input_tokens": 32000,
                "max_output_tokens": 48000,
                "max_context_tokens": 64000,
                "max_iterations": 50,
                "max_handoffs": 10,
                "timeout_seconds": 3600,
            }
        if constraints is None:
            constraints = []

        steps = self._decompose_task(task, available_modes, constraints)
        dependencies = self._build_dependencies(steps)
        budget_allocation = self._allocate_budget(steps, parent_budget)
        risk_assessment = self._assess_risk(steps, constraints)

        total_budget = {
            k: sum(b.get(k, 0) for b in budget_allocation.values())
            for k in parent_budget
        }

        plan = ExecutionPlan(
            plan_id=plan_id,
            run_id=self.run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            task=task,
            steps=steps,
            dependencies=dependencies,
            budget_allocation=budget_allocation,
            risk_assessment=risk_assessment,
            total_budget=total_budget,
        )
        plan.integrity_hash = self._compute_hash(plan)
        return plan

    def _decompose_task(
        self, task: str, available_modes: list[str], constraints: list[str]
    ) -> list[PlanStep]:
        steps: list[PlanStep] = []
        task_lower = task.lower()

        needs_explore = any(
            w in task_lower for w in ["explore", "analyze", "understand", "map", "find"]
        )
        needs_code = any(
            w in task_lower
            for w in ["code", "implement", "create", "modify", "fix", "add", "update"]
        )
        needs_review = any(
            w in task_lower for w in ["review", "check", "validate", "verify", "audit"]
        )

        step_num = 0

        if needs_explore and "explore" in available_modes:
            step_num += 1
            steps.append(
                PlanStep(
                    step_id=f"step-{step_num:02d}",
                    mode="explore",
                    task=f"Explore and analyze: {task}",
                    pre_conditions=["task defined", "workspace accessible"],
                    post_conditions=["findings produced", "file map created"],
                    budget={
                        "max_input_tokens": 8000,
                        "max_output_tokens": 12000,
                        "max_iterations": 15,
                    },
                )
            )

        if needs_code and "autocoder" in available_modes:
            step_num += 1
            pre_conds = ["exploration complete"] if needs_explore else ["task defined"]
            steps.append(
                PlanStep(
                    step_id=f"step-{step_num:02d}",
                    mode="autocoder",
                    task=f"Implement: {task}",
                    pre_conditions=pre_conds,
                    post_conditions=["code changes made", "evidence trail produced"],
                    budget={
                        "max_input_tokens": 16000,
                        "max_output_tokens": 24000,
                        "max_iterations": 25,
                    },
                    fallback_mode="orchestrator",
                )
            )

        if needs_review and "reviewer" in available_modes:
            step_num += 1
            steps.append(
                PlanStep(
                    step_id=f"step-{step_num:02d}",
                    mode="reviewer",
                    task=f"Review and validate: {task}",
                    pre_conditions=[
                        "changes produced" if needs_code else "analysis complete"
                    ],
                    post_conditions=["review report produced", "compliance verified"],
                    budget={
                        "max_input_tokens": 12000,
                        "max_output_tokens": 16000,
                        "max_iterations": 20,
                    },
                )
            )

        if not steps:
            step_num = 1
            if "autocoder" in available_modes:
                steps.append(
                    PlanStep(
                        step_id="step-01",
                        mode="autocoder",
                        task=task,
                        pre_conditions=["task defined"],
                        post_conditions=["task completed"],
                        budget={
                            "max_input_tokens": 16000,
                            "max_output_tokens": 24000,
                            "max_iterations": 25,
                        },
                    )
                )
            elif "explore" in available_modes:
                steps.append(
                    PlanStep(
                        step_id="step-01",
                        mode="explore",
                        task=task,
                        pre_conditions=["task defined"],
                        post_conditions=["findings produced"],
                        budget={
                            "max_input_tokens": 8000,
                            "max_output_tokens": 12000,
                            "max_iterations": 15,
                        },
                    )
                )

        return steps

    def _build_dependencies(self, steps: list[PlanStep]) -> list[StepDependency]:
        deps: list[StepDependency] = []
        for i in range(len(steps) - 1):
            deps.append(
                StepDependency(
                    from_step=steps[i].step_id,
                    to_step=steps[i + 1].step_id,
                    dependency_type="sequential",
                )
            )
        return deps

    def _allocate_budget(
        self, steps: list[PlanStep], parent_budget: dict[str, int]
    ) -> dict[str, dict[str, int]]:
        allocation: dict[str, dict[str, int]] = {}
        n = max(len(steps), 1)

        for step in steps:
            allocation[step.step_id] = {}
            for key, total in parent_budget.items():
                allocation[step.step_id][key] = total // n

        return allocation

    def _assess_risk(
        self, steps: list[PlanStep], constraints: list[str]
    ) -> dict[str, Any]:
        risk_factors: list[str] = []
        risk_level = "low"

        if len(steps) > 3:
            risk_factors.append("complex workflow (more than 3 steps)")
            risk_level = "medium"

        if any(s.fallback_mode for s in steps):
            risk_factors.append("fallback modes configured")

        if any("security" in c.lower() for c in constraints):
            risk_factors.append("security constraints present")
            risk_level = "high"

        if any("contract" in c.lower() for c in constraints):
            risk_factors.append("contract changes involved")
            risk_level = "high"

        return {
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "mitigation": "Use verifier gate after each step"
            if risk_level != "low"
            else "Standard execution",
        }

    def _compute_hash(self, plan: ExecutionPlan) -> str:
        content = json.dumps(
            {
                "plan_id": plan.plan_id,
                "task": plan.task,
                "steps": [asdict(s) for s in plan.steps],
            },
            sort_keys=True,
            default=str,
        )
        return f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"


def create_plan(
    task: str,
    run_id: str | None = None,
    available_modes: list[str] | None = None,
    parent_budget: dict[str, int] | None = None,
    constraints: list[str] | None = None,
) -> dict[str, Any]:
    planner = ExplicitPlanner(run_id=run_id)
    plan = planner.plan(task, available_modes, parent_budget, constraints)
    return plan.to_dict()


if __name__ == "__main__":
    import sys

    task = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "Explore and implement contract verifier runtime"
    )
    run_id = sys.argv[2] if len(sys.argv) > 2 else None

    result = create_plan(task, run_id=run_id)

    print(f"[OK] Execution plan: {result['plan_id']}")
    print(f"  Task: {result['task']}")
    print(f"  Valid: {result['is_valid']}")
    print(f"  Steps: {len(result['steps'])}")
    print(f"  Dependencies: {len(result['dependencies'])}")
    print(f"  Risk: {result['risk_assessment'].get('risk_level', 'unknown')}")

    for step in result["steps"]:
        print(f"    {step['step_id']}: [{step['mode']}] {step['task'][:60]}")

    for dep in result["dependencies"]:
        print(f"    {dep['from_step']} -> {dep['to_step']} ({dep['dependency_type']})")
