#!/usr/bin/env python3
"""Data structures and algorithmic rigor checker."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


SEVERITY_ORDER = ("critical", "high", "medium", "low", "info")
DEFAULT_REPORT_JSON = Path("artifacts/data_structures/ds_rigor_report.json")
DEFAULT_HOTSPOTS_TXT = Path("artifacts/data_structures/ds_hotspots.txt")


@dataclass(slots=True)
class Finding:
    id: str
    severity: str
    message: str
    file: str | None = None
    line: int | None = None


class ComplexityVisitor(ast.NodeVisitor):
    def __init__(self, file_path: Path, max_loop_depth: int) -> None:
        self.file_path = file_path
        self.max_loop_depth = max_loop_depth
        self.loop_depth = 0
        self.findings: list[Finding] = []
        self._seen: set[tuple[str, int | None]] = set()

    def _add(
        self, finding_id: str, severity: str, message: str, line: int | None
    ) -> None:
        key = (finding_id, line)
        if key in self._seen:
            return
        self._seen.add(key)
        self.findings.append(
            Finding(
                id=finding_id,
                severity=severity,
                message=message,
                file=str(self.file_path),
                line=line,
            )
        )

    def _enter_loop(self, node: ast.For | ast.While) -> None:
        self.loop_depth += 1

        if self.loop_depth > self.max_loop_depth:
            self._add(
                "DS100",
                "critical",
                f"Loop nesting depth {self.loop_depth} exceeds allowed {self.max_loop_depth}",
                getattr(node, "lineno", None),
            )

        if self.loop_depth >= 2:
            self._add(
                "DS110",
                "high",
                "Potential O(n^2) pattern: nested loop detected",
                getattr(node, "lineno", None),
            )

    def _exit_loop(self) -> None:
        self.loop_depth -= 1

    def visit_For(self, node: ast.For) -> None:
        self._enter_loop(node)
        self.generic_visit(node)
        self._exit_loop()

    def visit_While(self, node: ast.While) -> None:
        self._enter_loop(node)
        self.generic_visit(node)
        self._exit_loop()

    def visit_Compare(self, node: ast.Compare) -> None:
        if self.loop_depth > 0 and any(
            isinstance(op, (ast.In, ast.NotIn)) for op in node.ops
        ):
            comparator = node.comparators[0] if node.comparators else None
            if isinstance(comparator, (ast.Name, ast.List, ast.Tuple)):
                self._add(
                    "DS200",
                    "medium",
                    "Membership check inside loop can be optimized with set/dict",
                    getattr(node, "lineno", None),
                )
        self.generic_visit(node)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Data structures rigor checks"
    )
    parser.add_argument(
        "--report", action="store_true", help="Emit report artifacts"
    )
    parser.add_argument(
        "--scan-path",
        action="append",
        default=None,
        help="Python path inspected by the checker (repeatable)",
    )
    parser.add_argument(
        "--max-loop-depth",
        type=int,
        default=3,
        help="Maximum allowed nested loop depth",
    )
    parser.add_argument(
        "--max-critical",
        type=int,
        default=None,
        help="Maximum allowed critical findings",
    )
    parser.add_argument(
        "--max-high",
        type=int,
        default=None,
        help="Maximum allowed high findings",
    )

    args = parser.parse_args(argv)
    if args.max_loop_depth < 1:
        parser.error("--max-loop-depth must be >= 1")
    for flag, value in (
        ("--max-critical", args.max_critical),
        ("--max-high", args.max_high),
    ):
        if value is not None and value < 0:
            parser.error(f"{flag} must be >= 0")
    return args


def _collect_python_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_file() and path.suffix == ".py":
            files.append(path)
            continue
        if path.is_dir():
            files.extend(path.rglob("*.py"))
    return sorted(set(files))


def _summarize(findings: list[Finding]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for finding in findings:
        counter[finding.severity] += 1
    return {severity: counter.get(severity, 0) for severity in SEVERITY_ORDER}


def _breaches(
    summary: dict[str, int], max_critical: int | None, max_high: int | None
) -> list[str]:
    breaches: list[str] = []
    if max_critical is not None and summary["critical"] > max_critical:
        breaches.append(
            f"critical findings {summary['critical']} exceed threshold {max_critical}"
        )
    if max_high is not None and summary["high"] > max_high:
        breaches.append(
            f"high findings {summary['high']} exceed threshold {max_high}"
        )
    return breaches


def _write_hotspots(path: Path, findings: list[Finding]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not findings:
        path.write_text("No hotspots.\n", encoding="utf-8")
        return

    lines = ["DATA STRUCTURES HOTSPOTS", ""]
    for finding in findings:
        location = ""
        if finding.file:
            location = finding.file
            if finding.line is not None:
                location += f":{finding.line}"
        lines.append(
            f"[{finding.severity.upper()}] {finding.id} {location} - {finding.message}".strip()
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    scan_paths = args.scan_path or ["src/engineering", "src/data"]
    files = _collect_python_files(scan_paths)

    findings: list[Finding] = []
    if not files:
        findings.append(
            Finding(
                id="DS001",
                severity="high",
                message="No Python files discovered in provided scan paths",
            )
        )

    for file_path in files:
        source = file_path.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            findings.append(
                Finding(
                    id="DS010",
                    severity="high",
                    message=f"Syntax error during analysis: {exc.msg}",
                    file=str(file_path),
                    line=exc.lineno,
                )
            )
            continue

        visitor = ComplexityVisitor(
            file_path=file_path, max_loop_depth=args.max_loop_depth
        )
        visitor.visit(tree)
        findings.extend(visitor.findings)

    summary = _summarize(findings)
    breaches = _breaches(summary, args.max_critical, args.max_high)

    payload: dict[str, Any] = {
        "scan_paths": scan_paths,
        "python_file_count": len(files),
        "max_loop_depth": args.max_loop_depth,
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
    _write_hotspots(DEFAULT_HOTSPOTS_TXT, findings)

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
        DEFAULT_HOTSPOTS_TXT.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_HOTSPOTS_TXT.write_text(
            f"Execution error: {exc}\n", encoding="utf-8"
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
