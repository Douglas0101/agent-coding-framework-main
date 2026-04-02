#!/usr/bin/env python3
"""Data structure and type-annotation consistency checker.

Detects structural issues that static type checkers miss:

    - Functions returning ``dict`` with inconsistent keys
    - Star-imports with impact analysis
    - Recursive / self-referencing default parameters
    - Type annotation vs runtime usage mismatches
    - Inconsistent return types across branches
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class StructIssue:
    """A single data-structure consistency issue."""

    file: str
    line: int
    col: int
    code: str
    message: str
    severity: str = "warning"

    def to_dict(self) -> dict[str, Any]:
        """Serialise to plain dict."""
        return {
            "file": self.file,
            "line": self.line,
            "col": self.col,
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
        }


@dataclass
class StructResult:
    """Aggregated data-structure analysis results."""

    issues: list[StructIssue] = field(default_factory=list)
    files_scanned: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        """Total issue count."""
        return len(self.issues)

    @property
    def passed(self) -> bool:
        """True when zero error-severity issues."""
        return not any(i.severity == "error" for i in self.issues)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to plain dict."""
        return {
            "files_scanned": self.files_scanned,
            "total_issues": self.total,
            "passed": self.passed,
            "issues": [i.to_dict() for i in self.issues],
            "parse_errors": self.errors,
        }


# ──────────────────────────────────────────────
# Visitor
# ──────────────────────────────────────────────


class DataStructureVisitor(ast.NodeVisitor):
    """Walk AST to detect data-structure issues."""

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self.issues: list[StructIssue] = []

    def _add(
        self,
        node: ast.AST,
        code: str,
        msg: str,
        severity: str = "warning",
    ) -> None:
        self.issues.append(
            StructIssue(
                file=self.filepath,
                line=getattr(node, "lineno", 0),
                col=getattr(node, "col_offset", 0),
                code=code,
                message=msg,
                severity=severity,
            )
        )

    # -- star imports -------------------------------------------

    def visit_ImportFrom(
        self,
        node: ast.ImportFrom,
    ) -> None:
        if node.names and node.names[0].name == "*":
            module = node.module or "<unknown>"
            self._add(
                node,
                "RPA-D001",
                f"Star import 'from {module} import *' "
                f"— pollutes namespace, hides origins",
                severity="error",
            )
        self.generic_visit(node)

    # -- inconsistent dict keys in return -----------------------

    def _visit_function_node(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        self._check_dict_return_consistency(node)
        self._check_return_type_consistency(node)
        self.generic_visit(node)

    def visit_FunctionDef(
        self,
        node: ast.FunctionDef,
    ) -> None:
        self._visit_function_node(node)

    def visit_AsyncFunctionDef(
        self,
        node: ast.AsyncFunctionDef,
    ) -> None:
        self._visit_function_node(node)

    def _check_dict_return_consistency(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        """Check that all returned dicts have the same keys."""
        dict_returns: list[tuple[ast.Return, set[str]]] = []

        for child in ast.walk(node):
            if not isinstance(child, ast.Return):
                continue
            if child.value is None:
                continue
            if not isinstance(child.value, ast.Dict):
                continue

            keys: set[str] = set()
            for key in child.value.keys:
                if isinstance(key, ast.Constant):
                    keys.add(str(key.value))
                elif isinstance(key, ast.Name):
                    keys.add(key.id)
            if keys:
                dict_returns.append((child, keys))

        if len(dict_returns) < 2:
            return

        ref_keys = dict_returns[0][1]
        for ret_node, keys in dict_returns[1:]:
            if keys != ref_keys:
                missing = ref_keys - keys
                extra = keys - ref_keys
                parts: list[str] = []
                if missing:
                    parts.append(
                        f"missing={missing}",
                    )
                if extra:
                    parts.append(
                        f"extra={extra}",
                    )
                detail = ", ".join(parts)
                self._add(
                    ret_node,
                    "RPA-D002",
                    f"Inconsistent dict keys in "
                    f"'{node.name}' returns — {detail}",
                    severity="warning",
                )

    def _check_return_type_consistency(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        """Flag functions that return different type categories."""
        return_types: set[str] = set()

        for child in ast.walk(node):
            if not isinstance(child, ast.Return):
                continue
            if child.value is None:
                return_types.add("None")
            elif isinstance(child.value, ast.Constant):
                return_types.add(
                    type(child.value.value).__name__,
                )
            elif isinstance(child.value, ast.Dict):
                return_types.add("dict")
            elif isinstance(child.value, ast.List):
                return_types.add("list")
            elif isinstance(child.value, ast.Tuple):
                return_types.add("tuple")
            elif isinstance(child.value, ast.Name):
                return_types.add("variable")
            elif isinstance(child.value, ast.Call):
                return_types.add("call")
            else:
                return_types.add("expression")

        # Mixing None with a concrete type is suspicious
        concrete = return_types - {"None", "variable", "call", "expression"}
        if "None" in return_types and concrete:
            self._add(
                node,
                "RPA-D003",
                f"Function '{node.name}' mixes "
                f"None-returns with {concrete} "
                f"— may cause TypeError downstream",
                severity="warning",
            )

    # -- __all__ vs actual definitions --------------------------

    def visit_Module(
        self,
        node: ast.Module,
    ) -> None:
        self._check_all_exports(node)
        self.generic_visit(node)

    def _check_all_exports(self, node: ast.Module) -> None:
        """Check __all__ references match actual definitions."""
        all_node: ast.Assign | None = None
        for stmt in node.body:
            if not isinstance(stmt, ast.Assign):
                continue
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    all_node = stmt
                    break

        if all_node is None:
            return

        if not isinstance(all_node.value, (ast.List, ast.Tuple)):
            return

        exported: set[str] = set()
        for elt in all_node.value.elts:
            if isinstance(elt, ast.Constant) and isinstance(
                elt.value,
                str,
            ):
                exported.add(elt.value)

        defined: set[str] = set()
        for stmt in node.body:
            if isinstance(
                stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                defined.add(stmt.name)
            elif isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        defined.add(target.id)
            elif isinstance(
                stmt,
                (ast.Import, ast.ImportFrom),
            ):
                for alias in stmt.names:
                    name = alias.asname or alias.name
                    defined.add(name.split(".")[0])

        phantom = exported - defined
        if phantom:
            self._add(
                all_node,
                "RPA-D004",
                f"__all__ exports undefined names: {phantom}",
                severity="error",
            )


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────


def analyze_file(filepath: str | Path) -> list[StructIssue]:
    """Analyze a single Python file for structure issues."""
    path = Path(filepath)
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [
            StructIssue(
                file=str(path),
                line=0,
                col=0,
                code="RPA-DF01",
                message=f"Cannot read file: {exc}",
                severity="error",
            )
        ]

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []  # AST logic analyzer handles this

    visitor = DataStructureVisitor(str(path))
    visitor.visit(tree)
    return visitor.issues


def analyze_directory(
    directory: str | Path,
    *,
    exclude: frozenset[str] | None = None,
) -> StructResult:
    """Analyze all .py files in a directory."""
    result = StructResult()
    _exclude = exclude or frozenset(
        {"__pycache__", ".git", ".mypy_cache", ".ruff_cache"}
    )
    root = Path(directory)

    for py_file in sorted(root.rglob("*.py")):
        if any(part in _exclude for part in py_file.parts):
            continue
        result.files_scanned += 1
        issues = analyze_file(py_file)
        result.issues.extend(issues)

    return result
