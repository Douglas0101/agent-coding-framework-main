#!/usr/bin/env python3
"""
Hybrid Core CLI — Entry point for Hybrid Core validation.

This module provides CLI access to the HybridCoreValidator, allowing
integration with OpenCode's pipeline or standalone usage.

Usage:
    python -m runtime.hybrid_core_cli validate --task "task description" --output json
    python -m runtime.hybrid_core_cli classify --task "task description"
    python -m runtime.hybrid_core_cli gates --code "source code" --profile 1x
    python -m runtime.hybrid_core_cli run-autocode "task description"
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from textwrap import dedent
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

sys.path.insert(0, str(Path(__file__).parent))

FIELD_DESCRIPTIONS = {
    "execution_profile": "string; must match the resolved Hybrid Core profile",
    "scope_classification": "string; must match the resolved Hybrid Core tier",
    "summary": "string; concise summary of the implemented change",
    "problem_analysis": "string; required in 2x, explains the performance/problem constraints",
    "algorithm_selection_rationale": "string; required in 2x, justify the chosen algorithm or data structure",
    "complexity_certificate": "object; required in 2x, include at least time and space complexity",
    "edge_case_analysis": "object; required in 2x, list important edge cases and how they are handled",
    "stress_test_plan": "string; required in 2x, describe stress or brute-force validation strategy",
    "memory_bound_estimate": "string; required in 2x, describe memory/performance tradeoffs",
    "code_changes": "array; each item should include file, action, and summary keys",
    "compliance_notes": "array of strings describing NOU/NOE compliance",
    "tests": "array of strings with executed or proposed verification commands",
    "risks": "array of strings describing residual risks or caveats",
}


def _classify_task(task: str, context: dict[str, Any] | None = None):
    """Classify task using the same rollout logic as the validator."""
    from hybrid_core_config import is_hybrid_core_enabled
    from scope_detector import ScopeDetector

    detector = ScopeDetector()

    if is_hybrid_core_enabled():
        return detector.classify(task, context or {})

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
    return result


def _build_structured_output_prompt(task: str, active_profile) -> str:
    """Build the runtime prompt that requires a structured final payload."""
    required_fields = active_profile.output_schema or active_profile.required_artifacts
    field_lines = "\n".join(
        f"- {field}: {FIELD_DESCRIPTIONS.get(field, 'required field')}"
        for field in required_fields
    )

    adapter_instructions = active_profile.instructions.strip()
    adapter_block = (
        f"\nAdapter instructions:\n{adapter_instructions}\n"
        if adapter_instructions
        else ""
    )

    return dedent(
        f"""
        Execute the repository task and apply the necessary code changes.

        Original task:
        {task}

        Hybrid Core execution contract:
        - execution_profile must be \"{active_profile.profile}\"
        - scope_classification must be \"{active_profile.tier}\"
        - your final answer must be exactly one valid JSON object
        - do not wrap the JSON in markdown fences
        - do not add explanation before or after the JSON object
        - do not omit required fields; use an empty string, empty array, or empty object only when you truly have nothing to report

        Required JSON fields:
        {field_lines}

        Required field rules:
        - code_changes must be an array of objects with at least file, action, and summary
        - compliance_notes must be an array of strings
        - tests must be an array of strings
        - risks must be an array of strings
        - complexity_certificate should include time and space when performance_2x is active
        - edge_case_analysis should be an object keyed by edge-case name when performance_2x is active
        {adapter_block}
        """
    ).strip()


def _extract_final_text_from_events(raw_output: str) -> str:
    """Extract the final text payload from OpenCode's JSON event stream."""
    final_parts: list[str] = []
    fallback_parts: list[str] = []

    for raw_line in raw_output.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        if event.get("type") != "text":
            continue

        part = event.get("part", {})
        text = part.get("text")
        if not isinstance(text, str):
            continue

        metadata = part.get("metadata", {})
        openai_metadata = metadata.get("openai", {})
        if openai_metadata.get("phase") == "final_answer":
            final_parts.append(text)
        else:
            fallback_parts.append(text)

    combined = "".join(final_parts or fallback_parts).strip()
    if not combined:
        raise ValueError("OpenCode JSON stream did not contain a final text payload")
    return combined


def _extract_json_payload(final_text: str) -> dict[str, Any]:
    """Extract a JSON object from the final assistant text."""
    stripped = final_text.strip()
    candidates = [stripped]

    fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", stripped, re.DOTALL)
    if fenced_match:
        candidates.insert(0, fenced_match.group(1).strip())

    decoder = json.JSONDecoder()
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            return parsed

        for index, char in enumerate(candidate):
            if char != "{":
                continue
            try:
                parsed, _ = decoder.raw_decode(candidate[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed

    raise ValueError("Could not parse a JSON object from the final autocode output")


def _extract_source_code(payload: dict[str, Any]) -> str:
    """Extract source code when the payload exposes it."""
    code_changes = payload.get("code_changes")

    if isinstance(code_changes, dict):
        code = code_changes.get("code")
        return code if isinstance(code, str) else ""

    if isinstance(code_changes, list):
        snippets = []
        for change in code_changes:
            if isinstance(change, dict) and isinstance(change.get("code"), str):
                snippets.append(change["code"])
        return "\n\n".join(snippets)

    return ""


def _merge_string_lists(existing: Any, generated: list[str]) -> list[str]:
    """Merge user/model notes with validator-generated notes."""
    merged: list[str] = []
    for value in existing if isinstance(existing, list) else []:
        if isinstance(value, str) and value not in merged:
            merged.append(value)
    for value in generated:
        if value not in merged:
            merged.append(value)
    return merged


def _relativize(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _build_evidence_trail(
    validation_result, observability_path: Path | None
) -> list[dict[str, Any]]:
    """Build an auditable evidence trail for the final runtime output."""
    evidence = [
        {
            "kind": "scope_detection",
            "profile": validation_result.profile,
            "tier": validation_result.tier,
            "confidence": validation_result.scope_result.confidence
            if validation_result.scope_result
            else None,
            "triggers_matched": validation_result.scope_result.triggers_matched
            if validation_result.scope_result
            else [],
        },
        {
            "kind": "gate_execution",
            "overall_status": validation_result.gate_report.overall_status
            if validation_result.gate_report
            else "unknown",
            "auto_reject": validation_result.gate_report.auto_reject
            if validation_result.gate_report
            else False,
        },
    ]

    if observability_path is not None:
        evidence.append(
            {
                "kind": "observability_artifact",
                "path": _relativize(observability_path),
            }
        )

    return evidence


def run_autocode_task(
    task: str,
    project_root: Path | None = None,
    print_logs: bool = False,
) -> tuple[int, dict[str, Any]]:
    """Run native autocode, parse the final payload, and validate it."""
    from hybrid_core_validator import HybridCoreValidator
    from profile_activator import ProfileActivator

    root = project_root or REPO_ROOT
    scope_result = _classify_task(task)
    active_profile = ProfileActivator().activate(
        scope_result.tier, scope_result.profile
    )
    prompt = _build_structured_output_prompt(task, active_profile)

    command = [
        "opencode",
        "run",
        "--command",
        "autocode",
        "--format",
        "json",
        "--dir",
        str(root),
    ]
    if print_logs:
        command.append("--print-logs")
    command.append(prompt)

    completed = subprocess.run(
        command,
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )

    if print_logs and completed.stderr:
        sys.stderr.write(completed.stderr)

    if completed.returncode != 0:
        return completed.returncode, {
            "error": "OpenCode runtime failed before Hybrid Core validation",
            "command": "opencode run --command autocode --format json",
            "returncode": completed.returncode,
            "stderr": completed.stderr,
            "stdout": completed.stdout,
        }

    try:
        final_text = _extract_final_text_from_events(completed.stdout)
        payload = _extract_json_payload(final_text)
    except ValueError as exc:
        return 1, {
            "error": str(exc),
            "command": "opencode run --command autocode --format json",
            "raw_output": completed.stdout,
        }

    if "execution_profile" not in payload:
        payload["execution_profile"] = active_profile.profile
    if "scope_classification" not in payload:
        payload["scope_classification"] = active_profile.tier

    validator = HybridCoreValidator()
    validation_result = validator.validate(
        code_output=payload,
        task=task,
        source_code=_extract_source_code(payload),
    )
    observability_path = validator.persist_observability()

    output = dict(payload)
    output["compliance_notes"] = _merge_string_lists(
        payload.get("compliance_notes"),
        validation_result.compliance_notes,
    )
    output["gate_results"] = validation_result.to_dict().get("gate_report") or {
        "overall_status": "unknown"
    }
    output["hybrid_core_validation"] = validation_result.to_dict()
    output["evidence_trail"] = _build_evidence_trail(
        validation_result,
        observability_path,
    )
    if observability_path is not None:
        output["observability_artifact"] = _relativize(observability_path)

    return (0 if validation_result.passed else 1), output


def cmd_validate(args):
    """Validate LLM output through Hybrid Core."""
    from hybrid_core_validator import HybridCoreValidator

    validator = HybridCoreValidator()

    context = {}
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            if args.file.endswith(".json"):
                context = json.load(f)
            else:
                context["files_content"] = {"file": f.read()}

    if args.context:
        context.update(json.loads(args.context))

    code_output = {}
    if args.code_file:
        with open(args.code_file, "r", encoding="utf-8") as f:
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
    context = {}
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            if args.file.endswith(".json"):
                context = json.load(f)

    result = _classify_task(args.task, context)

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
        return 0

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

    source_code = args.code
    if args.code_file:
        with open(args.code_file, "r", encoding="utf-8") as f:
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
                            "gate_id": gate.gate_id,
                            "gate_name": gate.gate_name,
                            "status": gate.status,
                            "checks": [
                                {
                                    "check_id": check.check_id,
                                    "status": check.status,
                                    "message": check.message,
                                }
                                for check in gate.checks
                            ],
                        }
                        for gate in report.universal_gates
                    ],
                    "specialized_gates": [
                        {
                            "gate_id": gate.gate_id,
                            "gate_name": gate.gate_name,
                            "status": gate.status,
                            "checks": [
                                {
                                    "check_id": check.check_id,
                                    "status": check.status,
                                    "message": check.message,
                                }
                                for check in gate.checks
                            ],
                        }
                        for gate in report.specialized_gates
                    ],
                },
                indent=2,
                default=str,
            )
        )
        return 0 if report.passed else 1

    print(f"Overall: {'PASS' if report.passed else 'FAIL'}")
    print(f"Auto-reject: {report.auto_reject}")
    print()
    print("Universal Gates:")
    for gate in report.universal_gates:
        status = (
            "✅" if gate.status == "pass" else "❌" if gate.status == "fail" else "⚠️"
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


def cmd_run_autocode(args):
    """Run native autocode and validate the final structured output."""
    task = " ".join(args.task).strip()
    exit_code, output = run_autocode_task(
        task=task,
        project_root=REPO_ROOT,
        print_logs=args.print_logs,
    )

    if args.output_format == "text":
        if isinstance(output, dict) and "summary" in output:
            print(output["summary"])
            print()
            print(f"Profile: {output.get('execution_profile', 'unknown')}")
            print(f"Tier: {output.get('scope_classification', 'unknown')}")
            validation = output.get("hybrid_core_validation", {})
            print(f"Validation passed: {validation.get('passed', False)}")
        else:
            print(json.dumps(output, indent=2, default=str))
        return exit_code

    print(json.dumps(output, indent=2, default=str))
    return exit_code


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

    autocode_parser = subparsers.add_parser(
        "run-autocode",
        help="Run native autocode and enforce Hybrid Core validation on the final output",
    )
    autocode_parser.add_argument(
        "--print-logs",
        action="store_true",
        help="Forward OpenCode runtime logs to stderr after execution",
    )
    autocode_parser.add_argument(
        "--output-format", choices=["json", "text"], default="json"
    )
    autocode_parser.add_argument("task", nargs="+", help="Task to execute via autocode")

    args = parser.parse_args()

    if args.command == "validate":
        return cmd_validate(args)
    if args.command == "classify":
        return cmd_classify(args)
    if args.command == "gates":
        return cmd_gates(args)
    if args.command == "run-autocode":
        return cmd_run_autocode(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
