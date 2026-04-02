#!/usr/bin/env python3
"""Design pattern governance gate for swarm execution."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterable


SEVERITY_ORDER = ("critical", "high", "medium", "low", "info")
HTTP_METHOD_DECORATORS = {
    "get",
    "post",
    "put",
    "patch",
    "delete",
    "options",
    "head",
}
DEFAULT_REPORT_JSON = Path(
    "artifacts/design_patterns/design_patterns_summary.json"
)
DEFAULT_REPORT_TXT = Path(
    "artifacts/design_patterns/design_patterns_report.txt"
)


@dataclass(slots=True)
class Finding:
    id: str
    severity: str
    message: str
    file: str | None = None
    line: int | None = None


class PatternVisitor(ast.NodeVisitor):
    """Detect structural issues that should be solved with design patterns."""

    def __init__(
        self,
        *,
        file_path: Path,
        source_lines: list[str],
        max_method_lines: int,
        max_class_lines: int,
        max_class_methods: int,
        max_if_chain: int,
    ) -> None:
        self.file_path = file_path
        self.source_lines = source_lines
        self.max_method_lines = max_method_lines
        self.max_class_lines = max_class_lines
        self.max_class_methods = max_class_methods
        self.max_if_chain = max_if_chain
        self.findings: list[Finding] = []
        self._parent_stack: list[ast.AST] = []

    def visit(self, node: ast.AST) -> None:  # type: ignore[override]
        self._parent_stack.append(node)
        super().visit(node)
        self._parent_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_long_method(node)
        self._check_endpoint_logic(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_long_method(node)
        self._check_endpoint_logic(node)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        class_lines = _node_line_span(node)
        method_count = sum(
            1
            for item in node.body
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        )

        too_many_lines = class_lines > self.max_class_lines
        too_many_methods = method_count > self.max_class_methods
        if too_many_lines or too_many_methods:
            reasons: list[str] = []
            if too_many_lines:
                reasons.append(
                    f"{class_lines} lines exceeds {self.max_class_lines}"
                )
            if too_many_methods:
                reasons.append(
                    f"{method_count} methods exceeds {self.max_class_methods}"
                )
            self._add_finding(
                finding_id="DP002",
                severity="high",
                line=getattr(node, "lineno", None),
                message=(
                    "Large Class smell detected in "
                    f"'{node.name}': {', '.join(reasons)}. "
                    "Apply Extract Class/Facade boundaries."
                ),
            )

        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        if self._is_elif_branch(node):
            self.generic_visit(node)
            return

        chain_length = self._if_chain_length(node)
        if chain_length >= self.max_if_chain:
            self._add_finding(
                finding_id="DP003",
                severity="critical",
                line=getattr(node, "lineno", None),
                message=(
                    f"if/elif chain length {chain_length} exceeds "
                    f"allowed {self.max_if_chain - 1}. "
                    "Use Strategy/Polymorphism instead of conditional growth."
                ),
            )
        self.generic_visit(node)

    def _check_long_method(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        method_lines = _node_line_span(node)
        if method_lines <= self.max_method_lines:
            return

        self._add_finding(
            finding_id="DP001",
            severity="high",
            line=getattr(node, "lineno", None),
            message=(
                f"Long Method '{node.name}' has {method_lines} lines "
                f"(limit {self.max_method_lines}). "
                "Apply Extract Method and split responsibilities."
            ),
        )

    def _check_endpoint_logic(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        if not _is_http_endpoint(node):
            return

        reasons: list[str] = []
        if _has_inline_control_flow(node):
            reasons.append("inline control flow")
        if _has_sensitive_inline_calls(node):
            reasons.append("inline validation/cache/auth calls")
        if _node_line_span(node) > 25:
            reasons.append("handler longer than 25 lines")

        if not reasons:
            return

        self._add_finding(
            finding_id="DP004",
            severity="medium",
            line=getattr(node, "lineno", None),
            message=(
                f"Endpoint '{node.name}' contains {', '.join(reasons)}. "
                "Keep router thin and move business rules to service/use-case."
            ),
        )

    def _if_chain_length(self, node: ast.If) -> int:
        length = 1
        cursor = node
        while (
            cursor.orelse
            and len(cursor.orelse) == 1
            and isinstance(cursor.orelse[0], ast.If)
        ):
            length += 1
            cursor = cursor.orelse[0]
        return length

    def _is_elif_branch(self, node: ast.If) -> bool:
        if len(self._parent_stack) < 2:
            return False
        parent = self._parent_stack[-2]
        if not isinstance(parent, ast.If):
            return False
        return bool(parent.orelse) and parent.orelse[0] is node

    def _add_finding(
        self,
        *,
        finding_id: str,
        severity: str,
        message: str,
        line: int | None,
    ) -> None:
        self.findings.append(
            Finding(
                id=finding_id,
                severity=severity,
                message=message,
                file=str(self.file_path),
                line=line,
            )
        )


def _node_line_span(node: ast.AST) -> int:
    start = getattr(node, "lineno", None)
    end = getattr(node, "end_lineno", None)
    if not isinstance(start, int) or not isinstance(end, int):
        return 0
    return max(0, end - start + 1)


def _is_http_endpoint(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for decorator in node.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue
        func = decorator.func
        if isinstance(func, ast.Attribute):
            method_name = func.attr.lower()
            if method_name in HTTP_METHOD_DECORATORS:
                return True
    return False


def _has_inline_control_flow(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    flow_nodes = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try)
    return any(
        isinstance(child, flow_nodes)
        for child in ast.walk(node)
        if child is not node
    )


def _resolve_call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _resolve_call_name(node.value)
        if parent:
            return f"{parent}.{node.attr}"
        return node.attr
    return None


def _has_sensitive_inline_calls(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    patterns = (
        "validate",
        "cache",
        "auth",
        "security",
        "token",
        "api_key",
        "apikey",
    )
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        call_name = _resolve_call_name(child.func)
        if not call_name:
            continue
        lowered = call_name.lower()
        if any(pattern in lowered for pattern in patterns):
            return True
    return False


def _has_git_metadata(start: Path | None = None) -> bool:
    cursor = (start or Path.cwd()).resolve()
    for candidate in (cursor, *cursor.parents):
        if (candidate / ".git").exists():
            return True
    return False


def _is_truthy_env(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _collect_python_files(paths: Iterable[str]) -> list[Path]:
    discovered: list[Path] = []
    seen: set[Path] = set()
    for raw in paths:
        candidate = Path(raw)
        if candidate.is_file() and candidate.suffix == ".py":
            resolved = candidate.resolve()
            if resolved not in seen:
                seen.add(resolved)
                discovered.append(resolved)
            continue

        if candidate.is_dir():
            for py_file in candidate.rglob("*.py"):
                if ".venv" in py_file.parts or "__pycache__" in py_file.parts:
                    continue
                resolved = py_file.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                discovered.append(resolved)
    return sorted(discovered)


def _run_git_lines(cmd: list[str]) -> tuple[list[str], bool]:
    try:
        completed = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return [], False

    if completed.returncode != 0:
        return [], False
    return (
        [
            line.strip()
            for line in completed.stdout.splitlines()
            if line.strip()
        ],
        True,
    )


def _discover_deleted_python_files() -> tuple[set[Path], bool]:
    deleted: set[Path] = set()
    supported = False
    commands = [
        ["git", "diff", "--name-only", "--diff-filter=D", "--", "src"],
        [
            "git",
            "diff",
            "--cached",
            "--name-only",
            "--diff-filter=D",
            "--",
            "src",
        ],
    ]
    for command in commands:
        lines, command_supported = _run_git_lines(command)
        supported = supported or command_supported
        for line in lines:
            if line.endswith(".py"):
                deleted.add(Path(line))
    return deleted, supported


def _module_candidates(path: Path) -> set[str]:
    parts = list(path.with_suffix("").parts)
    if not parts:
        return set()

    if parts[-1] == "__init__":
        parts = parts[:-1]
    if not parts:
        return set()

    dotted = ".".join(parts)
    variants = {dotted}
    if parts[0] == "src" and len(parts) > 1:
        variants.add(".".join(parts[1:]))
    return variants


def _search_module_references(
    *,
    module_names: set[str],
    files: list[Path],
) -> list[tuple[Path, int, str]]:
    if not module_names:
        return []

    escaped = [re.escape(module) for module in sorted(module_names)]
    pattern = re.compile(r"\b(?:from|import)\s+(" + "|".join(escaped) + r")\b")
    fallback = re.compile(r"\b(" + "|".join(escaped) + r")\b")

    hits: list[tuple[Path, int, str]] = []
    for file_path in files:
        text = file_path.read_text(encoding="utf-8", errors="replace")
        for idx, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line) or fallback.search(line):
                hits.append((file_path, idx, line.strip()))
    return hits


def _summarize_findings(findings: list[Finding]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for finding in findings:
        counter[finding.severity] += 1
    return {severity: counter.get(severity, 0) for severity in SEVERITY_ORDER}


def _write_report(report_path: Path, findings: list[Finding]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["DESIGN PATTERN GATE REPORT", ""]
    if not findings:
        lines.append("No findings.")
    else:
        for finding in findings:
            location = ""
            if finding.file:
                location = finding.file
                if finding.line is not None:
                    location += f":{finding.line}"
            lines.append(
                f"[{finding.severity.upper()}] {finding.id} {location} - {finding.message}".strip()
            )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Design pattern governance gate"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Emit report artifacts",
    )
    parser.add_argument(
        "--scan-path",
        action="append",
        default=None,
        help="Path to scan (repeatable, default: src)",
    )
    parser.add_argument(
        "--max-method-lines",
        type=int,
        default=50,
        help="Maximum method/function lines before DP001",
    )
    parser.add_argument(
        "--max-class-lines",
        type=int,
        default=300,
        help="Maximum class lines before DP002",
    )
    parser.add_argument(
        "--max-class-methods",
        type=int,
        default=20,
        help="Maximum number of class methods before DP002",
    )
    parser.add_argument(
        "--max-if-chain",
        type=int,
        default=4,
        help="if/elif chain threshold for DP003",
    )
    parser.add_argument(
        "--deleted-python-file",
        action="append",
        default=None,
        help="Optional deleted file override for deletion impact checks",
    )

    args = parser.parse_args(argv)
    for flag, value in (
        ("--max-method-lines", args.max_method_lines),
        ("--max-class-lines", args.max_class_lines),
        ("--max-class-methods", args.max_class_methods),
        ("--max-if-chain", args.max_if_chain),
    ):
        if value < 1:
            parser.error(f"{flag} must be >= 1")
    return args


def run(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    scan_paths = args.scan_path or ["src"]
    files = _collect_python_files(scan_paths)

    findings: list[Finding] = []
    for file_path in files:
        source = file_path.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            findings.append(
                Finding(
                    id="DP901",
                    severity="high",
                    message=f"Syntax error blocks design-pattern analysis: {exc.msg}",
                    file=str(file_path),
                    line=exc.lineno,
                )
            )
            continue

        visitor = PatternVisitor(
            file_path=file_path,
            source_lines=source.splitlines(),
            max_method_lines=args.max_method_lines,
            max_class_lines=args.max_class_lines,
            max_class_methods=args.max_class_methods,
            max_if_chain=args.max_if_chain,
        )
        visitor.visit(tree)
        findings.extend(visitor.findings)

    deleted_paths = {
        Path(item)
        for item in (args.deleted_python_file or [])
        if item.endswith(".py")
    }
    deletion_check_supported = True
    if not deleted_paths:
        discovered, deletion_check_supported = _discover_deleted_python_files()
        deleted_paths = {
            path for path in discovered if str(path).startswith("src/")
        }

    if deleted_paths and files:
        for deleted in sorted(deleted_paths):
            module_names = _module_candidates(deleted)
            hits = _search_module_references(
                module_names=module_names, files=files
            )
            for hit_path, line_no, line in hits:
                findings.append(
                    Finding(
                        id="DP900",
                        severity="critical",
                        message=(
                            f"Deleted module impact unresolved for '{deleted}': "
                            f"reference still exists -> {line}"
                        ),
                        file=str(hit_path),
                        line=line_no,
                    )
                )
    elif (
        _is_truthy_env(os.getenv("CI"))
        and not deletion_check_supported
        and _has_git_metadata()
    ):
        findings.append(
            Finding(
                id="DP900",
                severity="critical",
                message=(
                    "CI fail-closed: deletion impact could not be evaluated. "
                    "Run from a git checkout with accessible diff metadata."
                ),
            )
        )

    summary = _summarize_findings(findings)
    breaches: list[str] = []
    if summary["critical"] > 0:
        breaches.append(f"critical findings {summary['critical']} must be 0")
    if summary["high"] > 0:
        breaches.append(f"high findings {summary['high']} must be 0")

    payload = {
        "scan_paths": scan_paths,
        "python_file_count": len(files),
        "summary": summary,
        "findings": [asdict(item) for item in findings],
        "breaches": breaches,
        "pass": not breaches,
    }

    DEFAULT_REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_REPORT_JSON.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    _write_report(DEFAULT_REPORT_TXT, findings)

    return 1 if breaches else 0


def main(argv: list[str] | None = None) -> int:
    try:
        return run(argv)
    except Exception as exc:  # pragma: no cover - defensive guard
        payload = {
            "pass": False,
            "error": str(exc),
            "summary": dict.fromkeys(SEVERITY_ORDER, 0),
            "findings": [],
            "breaches": ["execution error"],
        }
        DEFAULT_REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_REPORT_JSON.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        DEFAULT_REPORT_TXT.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_REPORT_TXT.write_text(
            f"Execution error: {exc}\n", encoding="utf-8"
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
