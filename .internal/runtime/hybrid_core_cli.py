#!/usr/bin/env python3
"""
Hybrid Core CLI — Entry point for Hybrid Core validation.

This module provides CLI access to the HybridCoreValidator, allowing
integration with OpenCode's pipeline or standalone usage.

Usage:
    python -m runtime.hybrid_core_cli validate --task "task description" --output json
    python -m runtime.hybrid_core_cli classify --task "task description"
    python -m runtime.hybrid_core_cli gates --code "source code" --profile 1x
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))


def cmd_validate(args):
    """Validate LLM output through Hybrid Core."""
    from hybrid_core_validator import HybridCoreValidator

    validator = HybridCoreValidator()

    context = {}
    if args.file:
        with open(args.file, "r") as f:
            if args.file.endswith(".json"):
                context = json.load(f)
            else:
                context["files_content"] = {"file": f.read()}

    if args.context:
        context.update(json.loads(args.context))

    code_output = {}
    if args.code_file:
        with open(args.code_file, "r") as f:
            code_output["code_changes"] = {"code": f.read()}

    if args.output_format == "json":
        result = validator.validate(
            code_output=code_output,
            task=args.task,
            source_code=code_output.get("code_changes", {}).get("code", ""),
            context=context,
        )
        print(json.dumps(result.to_dict(), indent=2, default=str))
        return 0 if result.passed else 1
    else:
        result = validator.validate(
            code_output=code_output,
            task=args.task,
            source_code=code_output.get("code_changes", {}).get("code", ""),
            context=context,
        )
        print(result.feedback_to_llm)
        return 0 if result.passed else 1


def cmd_classify(args):
    """Classify a task into tier/profile."""
    from scope_detector import ScopeDetector
    from hybrid_core_config import is_hybrid_core_enabled

    detector = ScopeDetector()

    context = {}
    if args.file:
        with open(args.file, "r") as f:
            if args.file.endswith(".json"):
                context = json.load(f)

    if is_hybrid_core_enabled():
        result = detector.classify(args.task, context)
    else:
        result = detector.classify("", {})
        result.tier = "tier_1_universal"
        result.profile = "default_1x"
        result.confidence = 1.0
        result.score = 0.0
        result.triggers_matched = []
        result.rationale = (
            "Hybrid Core escalation disabled by feature flag; forcing default_1x."
        )
        result.suggested_algorithm = None

    if args.output_format == "json":
        print(
            json.dumps(
                {
                    "tier": result.tier,
                    "profile": result.profile,
                    "confidence": result.confidence,
                    "score": result.score,
                    "triggers_matched": result.triggers_matched,
                    "rationale": result.rationale,
                    "suggested_algorithm": result.suggested_algorithm,
                },
                indent=2,
            )
        )
    else:
        print(f"Tier: {result.tier}")
        print(f"Profile: {result.profile}")
        print(f"Confidence: {result.confidence:.1%}")
        print(f"Score: {result.score}")
        print(f"Triggers: {', '.join(result.triggers_matched) or 'none'}")
        print(f"Suggested Algorithm: {result.suggested_algorithm or 'none'}")
        print(f"\nRationale: {result.rationale}")

    return 0


def cmd_gates(args):
    """Run gate execution on code."""
    from gate_executor import GateExecutor
    from output_validator import OutputValidator
    from scope_detector import ScopeDetector

    source_code = args.code
    if args.code_file:
        with open(args.code_file, "r") as f:
            source_code = f.read()

    is_2x = args.profile == "2x" or args.profile == "performance_2x"

    code_output = {"code_changes": {"code": source_code}}
    executor = GateExecutor()
    report = executor.execute_all(
        code_output=code_output, is_2x=is_2x, source_code=source_code
    )

    if args.output_format == "json":
        print(
            json.dumps(
                {
                    "passed": report.passed,
                    "auto_reject": report.auto_reject,
                    "rejection_reasons": report.rejection_reasons,
                    "universal_gates": [
                        {
                            "gate_id": g.gate_id,
                            "gate_name": g.gate_name,
                            "status": g.status,
                            "checks": [
                                {
                                    "check_id": c.check_id,
                                    "status": c.status,
                                    "message": c.message,
                                }
                                for c in g.checks
                            ],
                        }
                        for g in report.universal_gates
                    ],
                    "specialized_gates": [
                        {
                            "gate_id": g.gate_id,
                            "gate_name": g.gate_name,
                            "status": g.status,
                            "checks": [
                                {
                                    "check_id": c.check_id,
                                    "status": c.status,
                                    "message": c.message,
                                }
                                for c in g.checks
                            ],
                        }
                        for g in report.specialized_gates
                    ],
                },
                indent=2,
                default=str,
            )
        )
    else:
        print(f"Overall: {'PASS' if report.passed else 'FAIL'}")
        print(f"Auto-reject: {report.auto_reject}")
        print()
        print("Universal Gates:")
        for gate in report.universal_gates:
            status = (
                "✅"
                if gate.status == "pass"
                else "❌"
                if gate.status == "fail"
                else "⚠️"
            )
            print(f"  {status} {gate.gate_name}: {gate.status}")
            for check in gate.checks:
                if check.status != "pass":
                    print(f"      - {check.check_id}: {check.message}")

        if report.specialized_gates:
            print()
            print("Specialized Gates (2x):")
            for gate in report.specialized_gates:
                status = (
                    "✅"
                    if gate.status == "pass"
                    else "❌"
                    if gate.status == "fail"
                    else "⚠️"
                )
                print(f"  {status} {gate.gate_name}: {gate.status}")

    return 0 if report.passed else 1


def main():
    parser = argparse.ArgumentParser(
        description="Hybrid Core CLI — Validation and classification for Agent Coding"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    validate_parser = subparsers.add_parser("validate", help="Validate LLM output")
    validate_parser.add_argument("--task", required=True, help="Task description")
    validate_parser.add_argument("--code", help="Source code (inline)")
    validate_parser.add_argument("--code-file", help="Source code file")
    validate_parser.add_argument("--file", help="Context file (JSON or text)")
    validate_parser.add_argument("--context", help="Context as JSON string")
    validate_parser.add_argument(
        "--output-format", choices=["json", "text"], default="text"
    )

    classify_parser = subparsers.add_parser("classify", help="Classify task into tier")
    classify_parser.add_argument("--task", required=True, help="Task description")
    classify_parser.add_argument("--file", help="Context file")
    classify_parser.add_argument(
        "--output-format", choices=["json", "text"], default="text"
    )

    gates_parser = subparsers.add_parser("gates", help="Run gates on code")
    gates_parser.add_argument("--code", help="Source code (inline)")
    gates_parser.add_argument("--code-file", help="Source code file")
    gates_parser.add_argument(
        "--profile", choices=["1x", "2x", "default_1x", "performance_2x"], default="1x"
    )
    gates_parser.add_argument(
        "--output-format", choices=["json", "text"], default="text"
    )

    args = parser.parse_args()

    if args.command == "validate":
        return cmd_validate(args)
    elif args.command == "classify":
        return cmd_classify(args)
    elif args.command == "gates":
        return cmd_gates(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
