#!/usr/bin/env python3
"""AST-based deep logic error analyzer.

Detects logic bugs that ruff/mypy cannot catch by walking
the full AST of every Python file:

    - Mutable default arguments
    - Bare ``except:`` clauses
    - Unreachable code after return/raise/break/continue
    - ``is`` / ``is not`` with literals
    - ``assert (tuple,)`` — always True
    - Missing ``else`` return (implicit ``None``)
    - f-string without placeholders
    - Shadowed builtin names
    - ``global`` in nested scope
    - Deeply nested try/except (depth > 2)
"""

from __future__ import annotations

import ast
import builtins
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ── Builtin names set ─────────────────────────────────
_BUILTINS: frozenset[str] = frozenset(dir(builtins))

# Mutable types in default values
_MUTABLE_TYPES: tuple[type, ...] = (
    ast.List,
    ast.Dict,
    ast.Set,
    ast.Call,
)

# Statements that unconditionally terminate control flow
_TERMINAL_STMTS: tuple[type, ...] = (
    ast.Return,
    ast.Raise,
    ast.Break,
    ast.Continue,
)


@dataclass
class Issue:
    """A single detected logic issue."""

    file: str
    line: int
    col: int
    code: str
    message: str
    severity: str = "warning"  # warning | error

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
class AnalysisResult:
    """Aggregated results for one or more files."""

    issues: list[Issue] = field(default_factory=list)
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
# AST Visitor
# ──────────────────────────────────────────────


class LogicVisitor(ast.NodeVisitor):
    """Walk an AST and collect logic issues."""

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self.issues: list[Issue] = []
        self._scope_depth = 0
        self._try_depth = 0
        self._in_format_spec = 0

    # -- helpers ------------------------------------------------

    def _add(
        self,
        node: ast.AST,
        code: str,
        msg: str,
        severity: str = "warning",
    ) -> None:
        self.issues.append(
            Issue(
                file=self.filepath,
                line=getattr(node, "lineno", 0),
                col=getattr(node, "col_offset", 0),
                code=code,
                message=msg,
                severity=severity,
            )
        )

    # -- checks -------------------------------------------------

    def _visit_function_node(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        self._check_mutable_defaults(node)
        self._check_missing_return(node)
        self._check_shadowed_builtins_args(node)
        self._scope_depth += 1
        self.generic_visit(node)
        self._scope_depth -= 1

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

    def visit_ExceptHandler(
        self,
        node: ast.ExceptHandler,
    ) -> None:
        if node.type is None:
            self._add(
                node,
                "RPA-E001",
                "Bare 'except:' catches KeyboardInterrupt "
                "and SystemExit — use 'except Exception:'",
                severity="error",
            )
        elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
            has_raise = False
            has_log = False
            for child in ast.walk(node):
                if isinstance(child, ast.Raise):
                    has_raise = True
                if (
                    isinstance(child, ast.Call)
                    and isinstance(child.func, ast.Attribute)
                    and child.func.attr
                    in {
                        "error",
                        "warning",
                        "exception",
                        "critical",
                        "debug",
                        "info",
                    }
                ):
                    has_log = True
            if not (has_raise or has_log):
                self._add(
                    node,
                    "RPA-W007",
                    "Catching 'Exception' without raising or logging "
                    "— silent failure detected",
                )
        self.generic_visit(node)

    def visit_Compare(
        self,
        node: ast.Compare,
    ) -> None:
        for op, comparator in zip(node.ops, node.comparators, strict=False):
            if isinstance(op, (ast.Is, ast.IsNot)) and isinstance(
                comparator,
                (ast.Constant, ast.Num, ast.Str),
            ):
                # is None / is True / is False are
                # idiomatic PEP 8 — skip them
                if isinstance(
                    comparator, ast.Constant
                ) and comparator.value in {
                    None,
                    True,
                    False,
                }:
                    continue
                self._add(
                    node,
                    "RPA-E002",
                    "'is'/'is not' used with a literal"
                    " — use '=='/'!=' instead",
                    severity="error",
                )
        self.generic_visit(node)

    def visit_Assert(
        self,
        node: ast.Assert,
    ) -> None:
        if isinstance(node.test, ast.Tuple) and node.test.elts:
            self._add(
                node,
                "RPA-E003",
                "assert on non-empty tuple is always True "
                "— remove outer parentheses",
                severity="error",
            )
        self.generic_visit(node)

    def visit_JoinedStr(
        self,
        node: ast.JoinedStr,
    ) -> None:
        has_expr = any(isinstance(v, ast.FormattedValue) for v in node.values)
        if not has_expr and self._in_format_spec == 0:
            self._add(
                node,
                "RPA-W001",
                "f-string has no placeholders — use a plain string",
            )
        self.generic_visit(node)

    def visit_FormattedValue(
        self,
        node: ast.FormattedValue,
    ) -> None:
        self.visit(node.value)
        if node.format_spec is not None:
            self._in_format_spec += 1
            self.visit(node.format_spec)
            self._in_format_spec -= 1

    def visit_Call(self, node: ast.Call) -> None:
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "pop"
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == 0
        ):
            self._add(
                node,
                "RPA-E006",
                "list.pop(0) is O(n) overhead — "
                "use collections.deque.popleft() instead",
                severity="error",
            )
        self.generic_visit(node)

    def visit_Assign(
        self,
        node: ast.Assign,
    ) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in _BUILTINS:
                self._add(
                    target,
                    "RPA-W002",
                    f"Assignment shadows builtin '{target.id}'",
                )
        self.generic_visit(node)

    def visit_Global(
        self,
        node: ast.Global,
    ) -> None:
        if self._scope_depth > 0:
            self._add(
                node,
                "RPA-W003",
                "'global' used inside nested function "
                "— consider passing as parameter",
            )
        self.generic_visit(node)

    def visit_Try(
        self,
        node: ast.Try,
    ) -> None:
        self._try_depth += 1
        if self._try_depth > 2:
            self._add(
                node,
                "RPA-W004",
                f"Deeply nested try/except "
                f"(depth={self._try_depth}) — "
                f"refactor for clarity",
            )
        self.generic_visit(node)
        self._try_depth -= 1

    # Also handle TryStar (Python 3.11+ except*)
    def visit_TryStar(
        self,
        node: Any,
    ) -> None:
        self._try_depth += 1
        if self._try_depth > 2:
            ast_node = node if isinstance(node, ast.AST) else ast.Pass()
            self._add(
                ast_node,
                "RPA-W004",
                f"Deeply nested try/except "
                f"(depth={self._try_depth}) - "
                f"refactor for clarity",
            )
        self.generic_visit(node)
        self._try_depth -= 1

    # -- body-level checks (unreachable code) -------------------

    def _visit_body(self, stmts: list[ast.stmt]) -> None:
        for i, stmt in enumerate(stmts):
            if isinstance(stmt, _TERMINAL_STMTS):
                remaining = stmts[i + 1 :]
                real = [
                    s
                    for s in remaining
                    if not isinstance(
                        s,
                        (ast.Pass, ast.Expr),
                    )
                    or (
                        isinstance(s, ast.Expr)
                        and not isinstance(
                            s.value,
                            ast.Constant,
                        )
                    )
                ]
                if real:
                    self._add(
                        real[0],
                        "RPA-E004",
                        "Unreachable code after "
                        f"{type(stmt).__name__.lower()}",
                        severity="error",
                    )
                break

    def _check_loop_for_containers(self, body: list[ast.stmt]) -> None:
        for stmt in body:
            if isinstance(stmt, ast.Assign):
                if isinstance(stmt.value, ast.List) and not stmt.value.elts:
                    self._add(
                        stmt,
                        "RPA-W008",
                        "Empty list created inside loop body — "
                        "avoid recreating if possible",
                    )
                elif isinstance(stmt.value, ast.Dict) and not getattr(
                    stmt.value, "keys", []
                ):
                    self._add(
                        stmt,
                        "RPA-W008",
                        "Empty dict created inside loop body — "
                        "avoid recreating if possible",
                    )

    def visit_If(self, node: ast.If) -> None:
        self._visit_body(node.body)
        self._visit_body(node.orelse)
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self._visit_body(node.body)
        self._check_loop_for_containers(node.body)
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._visit_body(node.body)
        self._check_loop_for_containers(node.body)
        self.generic_visit(node)

    def visit_While(
        self,
        node: ast.While,
    ) -> None:
        self._visit_body(node.body)
        self._check_loop_for_containers(node.body)
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        self._visit_body(node.body)
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self._visit_body(node.body)
        self.generic_visit(node)

    # -- mutable default check ----------------------------------

    def _check_mutable_defaults(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        defaults: list[ast.expr] = list(node.args.defaults)
        defaults.extend(d for d in node.args.kw_defaults if d is not None)
        for default in defaults:
            if default is None:
                continue
            if isinstance(default, _MUTABLE_TYPES):
                self._add(
                    default,
                    "RPA-E005",
                    "Mutable default argument — use None and assign in body",
                    severity="error",
                )

    # -- missing return check -----------------------------------

    def _check_missing_return(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        if not node.body:
            return

        has_return_value = False
        has_bare_return = False

        for child in ast.walk(node):
            if isinstance(child, ast.Return):
                if child.value is not None:
                    has_return_value = True
                else:
                    has_bare_return = True

        if has_return_value and not has_bare_return:
            last = node.body[-1]
            if isinstance(last, ast.If) and not last.orelse:
                self._add(
                    node,
                    "RPA-W005",
                    f"Function '{node.name}' has return "
                    f"values but last branch has no else "
                    f"— may return implicit None",
                )

    # -- shadowed builtins in args ------------------------------

    def _check_shadowed_builtins_args(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        for arg in node.args.args + node.args.kwonlyargs:
            if arg.arg in _BUILTINS:
                self._add(
                    arg,
                    "RPA-W006",
                    f"Parameter '{arg.arg}' shadows builtin name",
                )


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────


def analyze_file(filepath: str | Path) -> list[Issue]:
    """Analyze a single Python file for logic issues."""
    path = Path(filepath)
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [
            Issue(
                file=str(path),
                line=0,
                col=0,
                code="RPA-F001",
                message=f"Cannot read file: {exc}",
                severity="error",
            )
        ]

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        return [
            Issue(
                file=str(path),
                line=exc.lineno or 0,
                col=exc.offset or 0,
                code="RPA-F002",
                message=f"Syntax error: {exc.msg}",
                severity="error",
            )
        ]

    visitor = LogicVisitor(str(path))
    visitor.visit(tree)

    # Body-level unreachable code for module-level
    visitor._visit_body(tree.body)

    return visitor.issues


def analyze_directory(
    directory: str | Path,
    *,
    exclude: frozenset[str] | None = None,
) -> AnalysisResult:
    """Analyze all .py files in a directory recursively."""
    result = AnalysisResult()
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
