#!/usr/bin/env python3
"""Deep syntax validation beyond what ruff catches.

Runs three layers of syntax checking:

    1. ``py_compile`` — catches hard syntax errors
    2. ``ast.parse``  — ensures well-formed AST
    3. Custom checks  — encoding, indentation mix, etc.
"""

from __future__ import annotations

import ast
import py_compile
import re
import tokenize
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from typing import Any


@dataclass
class SyntaxIssue:
    """A single syntax-level issue."""

    file: str
    line: int
    col: int
    code: str
    message: str
    severity: str = "error"

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
class SyntaxResult:
    """Aggregated syntax validation results."""

    issues: list[SyntaxIssue] = field(default_factory=list)
    files_scanned: int = 0

    @property
    def total(self) -> int:
        """Total issue count."""
        return len(self.issues)

    @property
    def passed(self) -> bool:
        """True when zero issues."""
        return self.total == 0

    def to_dict(self) -> dict[str, Any]:
        """Serialise to plain dict."""
        return {
            "files_scanned": self.files_scanned,
            "total_issues": self.total,
            "passed": self.passed,
            "issues": [i.to_dict() for i in self.issues],
        }


# ──────────────────────────────────────────────
# Individual checks
# ──────────────────────────────────────────────


def _check_compile(filepath: Path) -> list[SyntaxIssue]:
    """py_compile check for hard syntax errors."""
    try:
        py_compile.compile(
            str(filepath),
            doraise=True,
        )
    except py_compile.PyCompileError as exc:
        line = 0
        col = 0
        msg = str(exc)
        # Try to extract line number
        match = re.search(r"line (\d+)", msg)
        if match:
            line = int(match.group(1))
        return [
            SyntaxIssue(
                file=str(filepath),
                line=line,
                col=col,
                code="RPA-S001",
                message=f"Compile error: {msg}",
            )
        ]
    return []


def _check_ast_parse(
    filepath: Path,
    source: str,
) -> list[SyntaxIssue]:
    """ast.parse check for well-formed AST."""
    try:
        ast.parse(source, filename=str(filepath))
    except SyntaxError as exc:
        return [
            SyntaxIssue(
                file=str(filepath),
                line=exc.lineno or 0,
                col=exc.offset or 0,
                code="RPA-S002",
                message=f"AST parse error: {exc.msg}",
            )
        ]
    return []


def _check_mixed_indentation(
    filepath: Path,
    source: str,
) -> list[SyntaxIssue]:
    """Detect mixed tabs and spaces in indentation."""
    issues: list[SyntaxIssue] = []
    in_multiline = False

    for lineno, line in enumerate(
        source.splitlines(),
        start=1,
    ):
        stripped = line.lstrip()

        # Track multi-line strings roughly
        triple_count = line.count('"""') + line.count("'''")
        if triple_count % 2 != 0:
            in_multiline = not in_multiline
        if in_multiline:
            continue

        if not stripped or stripped.startswith("#"):
            continue

        indent = line[: len(line) - len(stripped)]
        if "\t" in indent and " " in indent:
            issues.append(
                SyntaxIssue(
                    file=str(filepath),
                    line=lineno,
                    col=0,
                    code="RPA-S003",
                    message="Mixed tabs and spaces in indentation",
                )
            )
    return issues


def _check_encoding_declaration(
    filepath: Path,
    source: str,
) -> list[SyntaxIssue]:
    """Python 3 uses UTF-8 by default (PEP 3120), so this is a no-op."""
    _ = filepath
    _ = source
    return []


def _check_token_errors(
    filepath: Path,
    source: str,
) -> list[SyntaxIssue]:
    """Tokenize to find broken strings, bad escapes."""
    issues: list[SyntaxIssue] = []
    try:
        tokens = list(
            tokenize.generate_tokens(
                StringIO(source).readline,
            )
        )
        # Check for deprecated string escapes
        for tok in tokens:
            if tok.type == tokenize.STRING:
                val = tok.string
                # Raw strings don't have escape issues
                if val.startswith(("r'", 'r"', "R'", 'R"')):
                    continue
                # Check for invalid escape sequences
                if re.search(
                    r"(?<!\\)\\[^\\\"'abfnrtvx0-7NuU\n]",
                    val,
                ):
                    issues.append(
                        SyntaxIssue(
                            file=str(filepath),
                            line=tok.start[0],
                            col=tok.start[1],
                            code="RPA-S005",
                            message="Possible invalid "
                            "escape sequence in string",
                            severity="warning",
                        )
                    )
    except tokenize.TokenError as exc:
        issues.append(
            SyntaxIssue(
                file=str(filepath),
                line=0,
                col=0,
                code="RPA-S006",
                message=f"Tokenization error: {exc}",
            )
        )
    return issues


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────


def validate_file(
    filepath: str | Path,
) -> list[SyntaxIssue]:
    """Run all syntax checks on a single Python file."""
    path = Path(filepath)
    all_issues: list[SyntaxIssue] = []

    # Layer 1: compile check
    all_issues.extend(_check_compile(path))
    if all_issues:
        return all_issues  # Fatal — skip other checks

    # Read source
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [
            SyntaxIssue(
                file=str(path),
                line=0,
                col=0,
                code="RPA-SF01",
                message=f"Cannot read file: {exc}",
            )
        ]

    # Layer 2: AST parse
    all_issues.extend(_check_ast_parse(path, source))
    if all_issues:
        return all_issues  # Fatal — skip other checks

    # Layer 3: custom checks
    all_issues.extend(
        _check_mixed_indentation(path, source),
    )
    all_issues.extend(
        _check_encoding_declaration(path, source),
    )
    all_issues.extend(
        _check_token_errors(path, source),
    )

    return all_issues


def validate_directory(
    directory: str | Path,
    *,
    exclude: frozenset[str] | None = None,
) -> SyntaxResult:
    """Validate all .py files in a directory."""
    result = SyntaxResult()
    _exclude = exclude or frozenset(
        {"__pycache__", ".git", ".mypy_cache", ".ruff_cache"}
    )
    root = Path(directory)

    for py_file in sorted(root.rglob("*.py")):
        if any(part in _exclude for part in py_file.parts):
            continue
        result.files_scanned += 1
        issues = validate_file(py_file)
        result.issues.extend(issues)

    return result
