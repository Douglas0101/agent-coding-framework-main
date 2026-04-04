#!/usr/bin/env python3
"""Mode contract budget validator and instrumentation helper.

Validates mode contracts against the schema specification and
produces a budget summary for CI enforcement.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MODES_DIR = REPO_ROOT / ".internal" / "specs" / "modes"
SCHEMA_FILE = REPO_ROOT / ".internal" / "specs" / "core" / "agent-mode-contract.yaml"


@dataclass
class BudgetSummary:
    """Aggregated budget summary for a mode contract."""

    mode_name: str
    version: str
    max_input_tokens: int = 0
    max_output_tokens: int = 0
    max_context_tokens: int = 0
    max_retrieval_chunks: int = 0
    max_iterations: int = 0
    max_handoffs: int = 0
    timeout_seconds: int = 0
    handoff_payload_budget: int = 0
    satisficing_mode: str = ""
    quality_threshold: float = 0.0
    skills: list[dict] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def total_token_budget(self) -> int:
        return self.max_input_tokens + self.max_output_tokens + self.max_context_tokens

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode_name,
            "version": self.version,
            "budget": {
                "input_tokens": self.max_input_tokens,
                "output_tokens": self.max_output_tokens,
                "context_tokens": self.max_context_tokens,
                "retrieval_chunks": self.max_retrieval_chunks,
                "iterations": self.max_iterations,
                "handoffs": self.max_handoffs,
                "timeout_seconds": self.timeout_seconds,
                "handoff_payload_budget": self.handoff_payload_budget,
                "total_tokens": self.total_token_budget(),
            },
            "satisficing": {
                "mode": self.satisficing_mode,
                "quality_threshold": self.quality_threshold,
            },
            "violations": self.violations,
            "warnings": self.warnings,
        }


def load_mode_contract(name: str) -> dict:
    path = MODES_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Mode contract not found: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def validate_budget(contract: dict) -> BudgetSummary:
    root = contract["agent_mode_contract"]
    meta = root["metadata"]
    resources = root["resources"]
    memory = root["memory"]
    satisficing = root["satisficing"]

    summary = BudgetSummary(
        mode_name=meta["name"],
        version=meta["version"],
        max_input_tokens=resources["max_input_tokens"],
        max_output_tokens=resources["max_output_tokens"],
        max_context_tokens=resources["max_context_tokens"],
        max_retrieval_chunks=resources["max_retrieval_chunks"],
        max_iterations=resources["max_iterations"],
        max_handoffs=resources["max_handoffs"],
        timeout_seconds=resources["timeout_seconds"],
        handoff_payload_budget=memory["handoff_payload_budget"]["max_tokens"],
        satisficing_mode=satisficing["mode"],
        quality_threshold=satisficing["quality_threshold"],
    )

    # Rule MC-003: All budget values must be positive
    for key in (
        "max_input_tokens",
        "max_output_tokens",
        "max_context_tokens",
        "max_retrieval_chunks",
        "max_iterations",
        "max_handoffs",
        "timeout_seconds",
    ):
        if resources[key] <= 0:
            summary.violations.append(
                f"MC-003: {key} must be positive, got {resources[key]}"
            )

    # Rule MC-008: handoff_payload_budget <= max_context_tokens
    if summary.handoff_payload_budget > summary.max_context_tokens:
        summary.violations.append(
            f"MC-008: handoff_payload_budget ({summary.handoff_payload_budget}) "
            f"exceeds max_context_tokens ({summary.max_context_tokens})"
        )

    # Rule MC-009: retry_max <= 3
    retry_max = root["error_policy"]["retry_max"]
    if retry_max > 3:
        summary.violations.append(
            f"MC-009: retry_max ({retry_max}) exceeds maximum of 3"
        )

    # Rule MC-010: quality_threshold in [0.0, 1.0]
    if not (0.0 <= summary.quality_threshold <= 1.0):
        summary.violations.append(
            f"MC-010: quality_threshold ({summary.quality_threshold}) out of range [0.0, 1.0]"
        )

    # Rule MC-011/013: Skills budget_share validation
    skills = root.get("skills", [])
    summary.skills = skills
    total_skill_budget = sum(s.get("budget_share", 0) for s in skills)
    if total_skill_budget > 1.0:
        summary.violations.append(
            f"MC-013: Sum of skill budget_share ({total_skill_budget:.2f}) exceeds 1.0"
        )
    for skill in skills:
        share = skill.get("budget_share", 0)
        if not (0.0 < share <= 1.0):
            summary.violations.append(
                f"MC-011: Skill '{skill['name']}' budget_share={share} out of (0.0, 1.0]"
            )

    # Warning: high iteration count
    if summary.max_iterations > 25:
        summary.warnings.append(
            f"High iteration count ({summary.max_iterations}) may lead to excessive token usage"
        )

    # Warning: low quality threshold for critical modes
    if summary.quality_threshold < 0.75:
        summary.warnings.append(
            f"Low quality threshold ({summary.quality_threshold}) may produce subpar results"
        )

    return summary


def validate_all_modes() -> list[BudgetSummary]:
    summaries = []
    for mode_file in sorted(MODES_DIR.glob("*.yaml")):
        if mode_file.name == "README.yaml":
            continue
        mode_name = mode_file.stem
        try:
            contract = load_mode_contract(mode_name)
            summary = validate_budget(contract)
            summaries.append(summary)
        except Exception as exc:
            summaries.append(
                BudgetSummary(
                    mode_name=mode_name,
                    version="unknown",
                    violations=[f"Failed to load/validate: {exc}"],
                )
            )
    return summaries


def print_budget_report(summaries: list[BudgetSummary], fmt: str = "text") -> str:
    if fmt == "json":
        return json.dumps(
            {
                "mode_budgets": [s.to_dict() for s in summaries],
                "total_violations": sum(len(s.violations) for s in summaries),
                "total_warnings": sum(len(s.warnings) for s in summaries),
            },
            indent=2,
        )

    lines = []
    lines.append("=" * 70)
    lines.append("MODE CONTRACT BUDGET REPORT")
    lines.append("=" * 70)
    lines.append("")

    for s in summaries:
        lines.append(f"Mode: {s.mode_name} (v{s.version})")
        lines.append(
            f"  Satisficing: {s.satisficing_mode} | Quality: {s.quality_threshold:.2f}"
        )
        lines.append(f"  Input Tokens:     {s.max_input_tokens:>8,}")
        lines.append(f"  Output Tokens:    {s.max_output_tokens:>8,}")
        lines.append(f"  Context Tokens:   {s.max_context_tokens:>8,}")
        lines.append(f"  Retrieval Chunks: {s.max_retrieval_chunks:>8,}")
        lines.append(f"  Max Iterations:   {s.max_iterations:>8,}")
        lines.append(f"  Max Handoffs:     {s.max_handoffs:>8,}")
        lines.append(f"  Timeout (sec):    {s.timeout_seconds:>8,}")
        lines.append(f"  Handoff Budget:   {s.handoff_payload_budget:>8,}")
        lines.append(f"  Total Token Budget: {s.total_token_budget():>6,}")

        if s.skills:
            lines.append(f"  Skills ({len(s.skills)}):")
            for skill in s.skills:
                lines.append(
                    f"    - {skill['name']} (budget: {skill['budget_share']:.0%}, "
                    f"verifier: {'yes' if skill['verifier_required'] else 'no'})"
                )

        if s.violations:
            lines.append(f"  VIOLATIONS ({len(s.violations)}):")
            for v in s.violations:
                lines.append(f"    - {v}")
        if s.warnings:
            lines.append(f"  WARNINGS ({len(s.warnings)}):")
            for w in s.warnings:
                lines.append(f"    - {w}")
        lines.append("")

    total_violations = sum(len(s.violations) for s in summaries)
    total_warnings = sum(len(s.warnings) for s in summaries)
    lines.append("-" * 70)
    lines.append(f"Total modes: {len(summaries)}")
    lines.append(f"Total violations: {total_violations}")
    lines.append(f"Total warnings: {total_warnings}")
    lines.append("=" * 70)

    return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Mode contract budget validator")
    parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format"
    )
    parser.add_argument("--mode", help="Validate a single mode contract")
    parser.add_argument(
        "--fail-on-violation",
        action="store_true",
        help="Exit with code 1 if any violations found",
    )
    args = parser.parse_args()

    if args.mode:
        contract = load_mode_contract(args.mode)
        summaries = [validate_budget(contract)]
    else:
        summaries = validate_all_modes()

    report = print_budget_report(summaries, fmt=args.format)
    print(report)

    if args.fail_on_violation:
        total_violations = sum(len(s.violations) for s in summaries)
        if total_violations > 0:
            sys.exit(1)


if __name__ == "__main__":
    main()
