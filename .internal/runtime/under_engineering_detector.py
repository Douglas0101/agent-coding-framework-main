"""Under-Engineering Detector — Detects inadequate solutions for constraints.

Detects naive implementations that are inappropriate for the given constraints,
such as O(n²) algorithms for large n, linear searches in sorted data, etc.
Uses AST parsing to detect nested loops and patterns.

Spec: PRD_Hybrid_Core_Agent_Coding.md FR-014
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class GateCheck:
    """Result of a single gate check."""

    check_id: str
    status: str
    message: str = ""


NAIVE_PATTERNS = {
    "nested_loop_quadratic": {
        "description": "Nested loop creating O(n²) complexity",
        "severity_threshold_n": 50000,
        "severity": "fail",
        "alternatives": ["Consider using hash map, sorting, or O(n log n) algorithm"],
    },
    "linear_search_sorted": {
        "description": "Linear search in sorted data",
        "severity_threshold_n": 10000,
        "severity": "warn",
        "alternatives": ["Consider binary search for O(log n) lookup"],
    },
    "string_concat_loop": {
        "description": "String concatenation in loop",
        "severity_threshold_n": 10000,
        "severity": "warn",
        "alternatives": ["Use list + join() for O(n) instead of O(n²)"],
    },
    "prefix_sum_recompute": {
        "description": "Recomputing prefix sum for each query",
        "severity_threshold_q": 10000,
        "severity": "warn",
        "alternatives": ["Pre-compute prefix sums for O(1) per query"],
    },
    "recursion_no_memo": {
        "description": "Recursive solution without memoization",
        "severity_threshold_n": 10000,
        "severity": "warn",
        "alternatives": ["Add memoization (DP) or bottom-up iteration"],
    },
    "nested_dict_lookup": {
        "description": "Nested dictionary lookups in loop",
        "severity_threshold_n": 10000,
        "severity": "warn",
        "alternatives": ["Flatten structure or use single lookup"],
    },
}


@dataclass
class UnderEngineeringCheck:
    """Result of a single under-engineering check."""

    pattern_name: str
    detected_in: str
    severity: str
    message: str
    line: int | None = None


class UnderEngineeringDetector:
    """Detects under-engineering in code using AST parsing.

    Analyzes source code to detect naive implementations that are
    inappropriate for the given constraints.
    """

    def __init__(self):
        self._patterns = NAIVE_PATTERNS

    def detect(
        self,
        source_code: str,
        constraints: dict[str, int] | None = None,
        tier: str = "tier_1_universal",
    ) -> list[GateCheck]:
        """Detect under-engineering in source code.

        Args:
            source_code: The source code to analyze.
            constraints: Detected constraints (n, q, m values).
            tier: The operational tier.

        Returns:
            List of GateCheck results.
        """
        if not source_code:
            return [
                GateCheck(
                    "under_eng_none", "warn", "No source code provided for analysis"
                )
            ]

        constraints = constraints or {}
        max_n = constraints.get("n", 0)
        max_q = constraints.get("q", 0)

        checks = []

        nested_loop_result = self._detect_nested_loops(source_code, max_n)
        checks.extend(nested_loop_result)

        linear_search_result = self._detect_linear_search(source_code, max_n)
        checks.extend(linear_search_result)

        string_concat_result = self._detect_string_concat(source_code, max_n)
        checks.extend(string_concat_result)

        prefix_sum_result = self._detect_prefix_sum_recompute(source_code, max_q)
        checks.extend(prefix_sum_result)

        recursion_result = self._detect_recursion_no_memo(source_code, max_n)
        checks.extend(recursion_result)

        if not checks:
            checks.append(
                GateCheck("under_eng_pass", "pass", "No under-engineering detected")
            )

        return checks

    def _detect_nested_loops(self, source_code: str, max_n: int) -> list[GateCheck]:
        """Detect nested loops that create O(n²) complexity."""
        checks = []

        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return checks

        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                nested = self._find_nested_loop(node)
                if nested:
                    severity = "fail" if max_n >= 50000 else "warn"

                    if max_n >= 50000:
                        message = (
                            f"O(n²) nested loop detected for n={max_n}. "
                            "This is infeasible for large inputs."
                        )
                    elif max_n >= 10000:
                        message = (
                            f"O(n²) nested loop detected for n={max_n}. "
                            "This may be slow for large inputs."
                        )
                    else:
                        message = "Nested loop detected. Consider optimization."

                    checks.append(GateCheck("under_eng_nested_loop", severity, message))
                    break

        return checks

    def _find_nested_loop(self, node: ast.AST) -> bool:
        """Recursively find nested loops."""
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.For):
                return True
            if isinstance(child, (ast.For, ast.While)):
                if self._find_nested_loop(child):
                    return True
        return False

    def _detect_linear_search(self, source_code: str, max_n: int) -> list[GateCheck]:
        """Detect linear search patterns in sorted data."""
        checks = []

        if max_n < 10000:
            return checks

        patterns = [
            (r"for\s+\w+\s+in\s+\w+:.*?if\s+\w+\s*==\s*\w+", "linear_eq_check"),
            (r"while\s+\w+\s*<.*?if\s+\w+\s*==\s*\w+", "while_linear_search"),
        ]

        for pattern, check_id in patterns:
            if re.search(pattern, source_code, re.DOTALL):
                checks.append(
                    GateCheck(
                        f"under_eng_{check_id}",
                        "warn",
                        f"Potential linear search in sorted data. Consider binary search.",
                    )
                )
                break

        return checks

    def _detect_string_concat(self, source_code: str, max_n: int) -> list[GateCheck]:
        """Detect string concatenation in loops."""
        checks = []

        if max_n < 10000:
            return checks

        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return checks

        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                has_string_concat = self._has_string_concat_in_loop(node)
                if has_string_concat:
                    checks.append(
                        GateCheck(
                            "under_eng_string_concat",
                            "warn",
                            "String concatenation in loop detected. Use list + join() for O(n).",
                        )
                    )
                    break

        return checks

    def _has_string_concat_in_loop(self, node: ast.AST) -> bool:
        """Check if loop body has string concatenation."""
        for child in ast.walk(node):
            if isinstance(child, ast.AugAssign):
                if isinstance(child.op, ast.Add):
                    return True
            elif isinstance(child, ast.Assign):
                if isinstance(child.value, ast.BinOp):
                    if isinstance(child.value.op, ast.Add):
                        return True
        return False

    def _detect_prefix_sum_recompute(
        self, source_code: str, max_q: int
    ) -> list[GateCheck]:
        """Detect recomputation of prefix sums."""
        checks = []

        if max_q < 10000:
            return checks

        if re.search(r"sum\s*\(\s*\w+\s*\[\s*i\s*:\s*.*?\]\s*\)", source_code):
            checks.append(
                GateCheck(
                    "under_eng_prefix_recompute",
                    "warn",
                    "Recomputing prefix sum in loop. Pre-compute for O(1) per query.",
                )
            )

        return checks

    def _detect_recursion_no_memo(
        self, source_code: str, max_n: int
    ) -> list[GateCheck]:
        """Detect recursive functions without memoization."""
        checks = []

        if max_n < 10000:
            return checks

        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return checks

        has_recursion = False
        has_memo = False

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_name = node.name
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if (
                            isinstance(child.func, ast.Name)
                            and child.func.id == func_name
                        ):
                            has_recursion = True
                    if isinstance(child, ast.Name):
                        if "memo" in child.id.lower() or "cache" in child.id.lower():
                            has_memo = True

        if has_recursion and not has_memo:
            checks.append(
                GateCheck(
                    "under_eng_recursion_no_memo",
                    "warn",
                    "Recursive function without memoization. Consider DP or bottom-up.",
                )
            )

        return checks

    def detect_from_output(
        self,
        code_output: dict[str, Any],
        tier: str = "tier_1_universal",
    ) -> list[GateCheck]:
        """Detect under-engineering from agent output dictionary.

        Args:
            code_output: The agent's output dictionary.
            tier: The operational tier.

        Returns:
            List of GateCheck results.
        """
        source_code = code_output.get("code_changes", {})
        if isinstance(source_code, dict):
            source_code = source_code.get("code", "")

        constraints = code_output.get("constraints_found", {})

        return self.detect(
            source_code=source_code if isinstance(source_code, str) else "",
            constraints=constraints if isinstance(constraints, dict) else {},
            tier=tier,
        )
