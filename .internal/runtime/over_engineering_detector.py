"""Over-Engineering Detector — Detects unnecessary complexity in code.

Detects usage of advanced data structures and algorithms in contexts where
they are not necessary (Tier 1 / general engineering tasks). Uses AST
parsing to detect imports and usage patterns.

Spec: PRD_Hybrid_Core_Agent_Coding.md FR-013
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


ADVANCED_STRUCTURES = {
    "link_cut_tree": {
        "imports": ["link_cut_tree", "lct", "splay", "linkcut", "link_cut"],
        "contexts_invalid": ["crud", "api", "endpoint", "database", "user", "simple"],
        "min_n_for_use": 100000,
    },
    "wavelet_tree": {
        "imports": ["wavelet_tree", "wavelet", "wt"],
        "contexts_invalid": ["crud", "api", "simple query", "basic"],
        "min_n_for_use": 50000,
    },
    "eertree": {
        "imports": ["eertree", "palindrome_tree", "palindromic_tree"],
        "contexts_invalid": ["crud", "api", "simple"],
        "min_n_for_use": 10000,
    },
    "suffix_automaton": {
        "imports": ["suffix_automaton", "suffixautomaton", "sam"],
        "contexts_invalid": ["crud", "api", "simple"],
        "min_n_for_use": 50000,
    },
    "persistentSegmentTree": {
        "imports": [
            "persistent_segment_tree",
            "persistentsegmenttree",
            "pst",
            "persistent_segtree",
        ],
        "contexts_invalid": ["crud", "api", "simple"],
        "min_n_for_use": 50000,
    },
    "centroid_decomposition": {
        "imports": ["centroid_decomposition", "centroid", "centroid_decomp"],
        "contexts_invalid": ["crud", "api", "simple"],
        "min_n_for_use": 50000,
    },
    "min_cost_max_flow": {
        "imports": ["min_cost_max_flow", "mcmf", "mincostmaxflow", "min_cost_flow"],
        "contexts_invalid": ["crud", "api", "simple", "basic"],
        "min_n_for_use": 1000,
    },
    "segment_tree_adv": {
        "imports": ["segment_tree_adv", "segtree_adv"],
        "contexts_invalid": ["crud", "api", "simple query"],
        "min_n_for_use": 10000,
    },
    "binary_indexed_tree_adv": {
        "imports": ["binary_indexed_tree_adv", "fenwick_adv"],
        "contexts_invalid": ["crud", "api"],
        "min_n_for_use": 10000,
    },
    "sparse_table_adv": {
        "imports": ["sparse_table_adv"],
        "contexts_invalid": ["crud", "api"],
        "min_n_for_use": 50000,
    },
    "dsu_rollback": {
        "imports": ["dsu_rollback", "disjoint_set_rollback", "rollback_dsu"],
        "contexts_invalid": ["crud", "api", "simple"],
        "min_n_for_use": 100000,
    },
    "link_cut_tree_adv": {
        "imports": ["linkcuttree", "dynamic_tree"],
        "contexts_invalid": ["crud", "api", "static"],
        "min_n_for_use": 50000,
    },
}


@dataclass
class OverEngineeringCheck:
    """Result of a single over-engineering check."""

    structure_name: str
    detected_import: str
    severity: str  # fail, warn
    message: str
    line: int | None = None


class OverEngineeringDetector:
    """Detects over-engineering in code using AST parsing.

    Analyzes source code to detect usage of advanced algorithms and data
    structures that are unnecessary for the given context (Tier 1 tasks).
    """

    def __init__(self):
        self._structures = ADVANCED_STRUCTURES

    def detect(
        self,
        source_code: str,
        tier: str = "tier_1_universal",
        task_context: str = "",
        constraints: dict[str, int] | None = None,
    ) -> list[GateCheck]:
        """Detect over-engineering in source code.

        Args:
            source_code: The source code to analyze.
            tier: The operational tier (tier_1_universal, tier_2_algorithmic, tier_3_competitive).
            task_context: Additional context about the task.
            constraints: Detected constraints (n, q, m values).

        Returns:
            List of GateCheck results.
        """
        if tier != "tier_1_universal":
            return []

        if not source_code:
            return [
                GateCheck(
                    "over_eng_none", "warn", "No source code provided for analysis"
                )
            ]

        checks = []
        constraints = constraints or {}
        max_n = constraints.get("n", 0)

        imports_found = self._extract_imports(source_code)
        advanced_usage = self._find_advanced_usage(imports_found)

        for usage in advanced_usage:
            structure_name = usage["structure"]
            structure_info = self._structures.get(structure_name, {})

            has_valid_context = self._check_valid_context(
                task_context, structure_info.get("contexts_invalid", [])
            )

            min_n = structure_info.get("min_n_for_use", 0)
            has_valid_constraints = max_n >= min_n if min_n > 0 else True

            if not has_valid_context or not has_valid_constraints:
                severity = "fail" if not has_valid_context else "warn"
                message = self._build_message(
                    structure_name,
                    has_valid_context,
                    has_valid_constraints,
                    max_n,
                    min_n,
                )
                checks.append(
                    GateCheck(f"over_eng_{structure_name}", severity, message)
                )

        if not checks:
            checks.append(
                GateCheck("over_eng_pass", "pass", "No over-engineering detected")
            )

        return checks

    def _extract_imports(self, source_code: str) -> dict[str, list[str]]:
        """Extract imports from source code using AST."""
        imports = {}

        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return imports

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name.lower()
                    imports.setdefault(name, []).append(f"import {name}")

            elif isinstance(node, ast.ImportFrom):
                module = (node.module or "").lower()
                for alias in node.names:
                    name = alias.name.lower()
                    full_name = f"{module}.{name}" if module else name
                    imports.setdefault(name, []).append(f"from {module} import {name}")
                    imports.setdefault(full_name, []).append(
                        f"from {module} import {name}"
                    )

        return imports

    def _find_advanced_usage(self, imports: dict[str, list[str]]) -> list[dict]:
        """Find usage of advanced structures in imports."""
        usage = []

        for structure_name, structure_info in self._structures.items():
            valid_imports = structure_info.get("imports", [])

            for import_name in valid_imports:
                if import_name in imports:
                    usage.append(
                        {
                            "structure": structure_name,
                            "import_name": import_name,
                            "import_lines": imports[import_name],
                        }
                    )
                    break

        return usage

    def _check_valid_context(
        self, task_context: str, invalid_contexts: list[str]
    ) -> bool:
        """Check if task context is valid for the structure."""
        if not task_context:
            return True

        task_lower = task_context.lower()

        for invalid in invalid_contexts:
            if invalid in task_lower:
                return False

        return True

    def _build_message(
        self,
        structure_name: str,
        has_valid_context: bool,
        has_valid_constraints: bool,
        max_n: int,
        min_n: int,
    ) -> str:
        """Build appropriate error message."""
        if not has_valid_context:
            return (
                f"Advanced structure '{structure_name}' used in general engineering context. "
                f"This structure is unnecessary for the task scope."
            )

        if not has_valid_constraints:
            return (
                f"Advanced structure '{structure_name}' used without sufficient constraints. "
                f"Detected n={max_n}, but this structure typically requires n>={min_n}."
            )

        return (
            f"Advanced structure '{structure_name}' may be unnecessary for this task."
        )

    def detect_from_output(
        self,
        code_output: dict[str, Any],
        tier: str = "tier_1_universal",
    ) -> list[GateCheck]:
        """Detect over-engineering from agent output dictionary.

        Args:
            code_output: The agent's output dictionary.
            tier: The operational tier.

        Returns:
            List of GateCheck results.
        """
        source_code = code_output.get("code_changes", {})
        if isinstance(source_code, dict):
            source_code = source_code.get("code", "")

        task_description = code_output.get("summary", "")
        constraints = code_output.get("constraints_found", {})

        return self.detect(
            source_code=source_code if isinstance(source_code, str) else "",
            tier=tier,
            task_context=task_description,
            constraints=constraints if isinstance(constraints, dict) else {},
        )
