#!/usr/bin/env python3
"""AST-based automatic logic fixer.

Applies deterministic, safe transformations for issues
detected by ``ast_logic_analyzer``:

    - Mutable default args → ``None`` + body guard
    - Bare ``except:`` → ``except Exception:``
    - ``is <literal>`` → ``== <literal>``
    - f-string without placeholders → plain string
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeAlias


EditType: TypeAlias = tuple[int, str, str, str, int, str]


@dataclass
class FixAction:
    """Describes a single fix applied to a file."""

    file: str
    line: int
    code: str
    description: str
    before: str
    after: str

    def to_dict(self) -> dict[str, Any]:
        """Serialise to plain dict."""
        return {
            "file": self.file,
            "line": self.line,
            "code": self.code,
            "description": self.description,
            "before": self.before,
            "after": self.after,
        }


@dataclass
class FixResult:
    """Aggregated fix results."""

    fixes: list[FixAction] = field(default_factory=list)
    files_modified: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        """Total fixes applied."""
        return len(self.fixes)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to plain dict."""
        return {
            "total_fixes": self.total,
            "files_modified": self.files_modified,
            "fixes": [f.to_dict() for f in self.fixes],
            "errors": self.errors,
        }


# ──────────────────────────────────────────────
# Line-based safe fixers
# ──────────────────────────────────────────────


def _fix_bare_except(
    lines: list[str],
    filepath: str,
) -> list[FixAction]:
    """Replace ``except:`` with ``except Exception:``."""
    fixes: list[FixAction] = []
    pattern = re.compile(r"^(\s*)except\s*:\s*$")

    for i, line in enumerate(lines):
        match = pattern.match(line)
        if match:
            indent = match.group(1)
            before = line.rstrip()
            after = f"{indent}except Exception:"
            lines[i] = after + "\n"
            fixes.append(
                FixAction(
                    file=filepath,
                    line=i + 1,
                    code="RPA-E001",
                    description=("Bare except → except Exception"),
                    before=before,
                    after=after,
                )
            )
    return fixes


def _fix_is_literal(
    lines: list[str],
    filepath: str,
) -> list[FixAction]:
    """Replace ``is <literal>`` with ``== <literal>``."""
    fixes: list[FixAction] = []
    # Match `is None` should NOT be replaced
    # Match `is True`, `is False` should NOT be replaced
    # Match `is <number>`, `is "<string>"` should
    pattern = re.compile(
        r"\bis\s+((?!None\b)(?!True\b)(?!False\b)"
        r"(?!not\b)(?:\d+|\"[^\"]*\"|'[^']*'))",
    )
    pattern_not = re.compile(
        r"\bis\s+not\s+((?!None\b)(?!True\b)(?!False\b)"
        r"(?:\d+|\"[^\"]*\"|'[^']*'))",
    )

    for i, line in enumerate(lines):
        before = line.rstrip()
        modified = pattern_not.sub(r"!= \1", line)
        modified = pattern.sub(r"== \1", modified)
        if modified != line:
            lines[i] = modified
            fixes.append(
                FixAction(
                    file=filepath,
                    line=i + 1,
                    code="RPA-E002",
                    description=("'is <literal>' → '== <literal>'"),
                    before=before,
                    after=modified.rstrip(),
                )
            )
    return fixes


def _fix_fstring_no_placeholder(
    lines: list[str],
    filepath: str,
) -> list[FixAction]:
    """Remove f-prefix from f-strings without placeholders."""
    fixes: list[FixAction] = []
    # Simple pattern: f"..." or f'...' without {
    pattern = re.compile(
        r"""((?<!\w))f(["'])([^{]*?)\2""",
    )

    for i, line in enumerate(lines):
        before = line.rstrip()
        modified = pattern.sub(r"\1\2\3\2", line)
        if modified != line:
            lines[i] = modified
            fixes.append(
                FixAction(
                    file=filepath,
                    line=i + 1,
                    code="RPA-W001",
                    description=(
                        "f-string without placeholders → plain string"
                    ),
                    before=before,
                    after=modified.rstrip(),
                )
            )
    return fixes


def _fix_mutable_defaults(
    source: str,
    filepath: str,
) -> tuple[str, list[FixAction]]:
    """Replace mutable defaults with None + body guard.

    Transforms::

        def f(x=[]):    →  def f(x=None):
            ...                if x is None:
                                   x = []
                               ...
    """
    fixes: list[FixAction] = []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source, fixes

    lines = source.splitlines(keepends=True)
    mutable_types = (ast.List, ast.Dict, ast.Set)

    # Collect edits: (default_line, arg_name, literal,
    #                  func_name, body_start_line,
    #                  body_indent)
    edits: list[EditType] = []

    for node in ast.walk(tree):
        if not isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            continue

        # Compute body indent from first statement
        if not node.body:
            continue
        first_stmt = node.body[0]
        body_line_idx = first_stmt.lineno - 1
        if body_line_idx >= len(lines):
            continue
        body_line = lines[body_line_idx]
        body_indent = body_line[: len(body_line) - len(body_line.lstrip())]

        args = node.args
        num_defaults = len(args.defaults)
        arg_names = [a.arg for a in args.args]
        paired = list(
            zip(
                arg_names[-num_defaults:],
                args.defaults,
                strict=False,
            )
        )

        for arg_name, default in paired:
            if not isinstance(default, mutable_types):
                continue

            if isinstance(default, ast.List):
                literal = "[]"
            elif isinstance(default, ast.Dict):
                literal = "{}"
            elif isinstance(default, ast.Set):
                literal = "set()"
            else:
                continue

            edits.append(
                (
                    default.lineno,
                    arg_name,
                    literal,
                    node.name,
                    first_stmt.lineno,
                    body_indent,
                )
            )

    # Apply in reverse order to preserve line indices
    for (
        line_no,
        arg_name,
        literal,
        func_name,
        body_start,
        indent,
    ) in sorted(edits, key=lambda e: e[0], reverse=True):
        idx = line_no - 1
        if idx >= len(lines):
            continue

        old_line = lines[idx]
        # Replace the default value in the signature
        pat = re.compile(
            rf"(\b{re.escape(arg_name)}\s*)"
            rf"(:\s*[^=,)]+\s*)?"
            rf"=\s*{re.escape(literal)}",
        )
        match = pat.search(old_line)
        if not match:
            continue

        type_hint = match.group(2) or ""
        new_default = f"{arg_name}{type_hint}= None"
        new_line = (
            old_line[: match.start()] + new_default + old_line[match.end() :]
        )
        lines[idx] = new_line

        # Insert body guard before the first statement
        guard = (
            f"{indent}if {arg_name} is None:\n"
            f"{indent}    {arg_name} = {literal}\n"
        )
        body_idx = body_start - 1
        lines.insert(body_idx, guard)

        fixes.append(
            FixAction(
                file=filepath,
                line=line_no,
                code="RPA-E005",
                description=(
                    f"Mutable default {literal}"
                    f" → None + guard in"
                    f" '{func_name}'"
                ),
                before=old_line.rstrip(),
                after=new_line.rstrip(),
            )
        )

    return "".join(lines), fixes


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────


def fix_file(
    filepath: str | Path,
    *,
    dry_run: bool = False,
) -> list[FixAction]:
    """Apply all safe logic fixes to a single file."""
    path = Path(filepath)
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as _:
        return []

    all_fixes: list[FixAction] = []

    # Phase 1: mutable defaults (AST-based)
    new_source, mut_fixes = _fix_mutable_defaults(
        source,
        str(path),
    )
    all_fixes.extend(mut_fixes)

    # Phase 2: line-based fixes
    lines = new_source.splitlines(keepends=True)
    all_fixes.extend(_fix_bare_except(lines, str(path)))
    all_fixes.extend(_fix_is_literal(lines, str(path)))
    all_fixes.extend(
        _fix_fstring_no_placeholder(lines, str(path)),
    )

    # Write back
    if all_fixes and not dry_run:
        path.write_text("".join(lines), encoding="utf-8")

    return all_fixes


def fix_directory(
    directory: str | Path,
    *,
    dry_run: bool = False,
    exclude: frozenset[str] | None = None,
) -> FixResult:
    """Apply all safe logic fixes to a directory."""
    result = FixResult()
    _exclude = exclude or frozenset(
        {"__pycache__", ".git", ".mypy_cache", ".ruff_cache"}
    )
    root = Path(directory)

    for py_file in sorted(root.rglob("*.py")):
        if any(part in _exclude for part in py_file.parts):
            continue
        fixes = fix_file(py_file, dry_run=dry_run)
        if fixes:
            result.files_modified += 1
            result.fixes.extend(fixes)

    return result
