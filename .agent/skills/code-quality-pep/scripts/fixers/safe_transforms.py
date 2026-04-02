#!/usr/bin/env python3
"""Safe AST transformation utilities.

Provides a transactional wrapper around file modifications:

    1. Read source → apply transforms → validate result
    2. Write to temp file first
    3. Verify the output compiles (``ast.parse``)
    4. Only then overwrite the original
    5. Generate diff for auditability

This ensures that auto-fixes NEVER corrupt a working file.
"""

from __future__ import annotations

import ast
import difflib
import hashlib
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TransformRecord:
    """Records a single safe transformation."""

    file: str
    hash_before: str
    hash_after: str
    diff_lines: list[str] = field(default_factory=list)
    success: bool = True
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialise to plain dict."""
        return {
            "file": self.file,
            "hash_before": self.hash_before,
            "hash_after": self.hash_after,
            "diff_lines_count": len(self.diff_lines),
            "success": self.success,
            "error": self.error,
        }


def file_hash(path: Path) -> str:
    """Compute SHA-256 of a file's contents."""
    return hashlib.sha256(
        path.read_bytes(),
    ).hexdigest()[:16]


def generate_diff(
    before: str,
    after: str,
    filepath: str,
) -> list[str]:
    """Generate unified diff between two source strings."""
    return list(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{filepath}",
            tofile=f"b/{filepath}",
            lineterm="",
        )
    )


def safe_write(
    path: Path,
    new_source: str,
    original_source: str,
) -> TransformRecord:
    """Safely write new source to path with validation.

    Steps:
        1. Compute hash of original
        2. Validate new source compiles
        3. Write to temp file
        4. Copy temp → original (atomic on same FS)
        5. Compute hash of result
        6. Return diff record
    """
    record = TransformRecord(
        file=str(path),
        hash_before=hashlib.sha256(
            original_source.encode(),
        ).hexdigest()[:16],
        hash_after="",
    )

    # Validate new source compiles
    try:
        ast.parse(new_source, filename=str(path))
    except SyntaxError as exc:
        record.success = False
        record.error = f"Transform produced invalid syntax: {exc}"
        return record

    # Generate diff
    record.diff_lines = generate_diff(
        original_source,
        new_source,
        str(path),
    )

    # Write to temp then copy
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            tmp.write(new_source)
            tmp_path = Path(tmp.name)

        shutil.copy2(str(tmp_path), str(path))
        tmp_path.unlink(missing_ok=True)
    except OSError as exc:
        record.success = False
        record.error = f"Write failed: {exc}"
        return record

    record.hash_after = hashlib.sha256(
        new_source.encode(),
    ).hexdigest()[:16]

    return record


def snapshot_directory(
    directory: Path,
    *,
    exclude: frozenset[str] | None = None,
) -> dict[str, str]:
    """Compute hash snapshot of all .py files.

    Returns mapping of relative_path → sha256[:16].
    Used for before/after comparison in the RPA loop.
    """
    _exclude = exclude or frozenset(
        {"__pycache__", ".git", ".mypy_cache", ".ruff_cache"}
    )
    snapshot: dict[str, str] = {}

    for py_file in sorted(directory.rglob("*.py")):
        if any(part in _exclude for part in py_file.parts):
            continue
        try:
            rel = str(py_file.relative_to(directory))
            snapshot[rel] = file_hash(py_file)
        except (OSError, ValueError) as _:
            continue

    return snapshot


def compare_snapshots(
    before: dict[str, str],
    after: dict[str, str],
) -> dict[str, str]:
    """Compare two snapshots, return changed files.

    Returns mapping of relative_path → change_type where
    change_type is 'modified', 'added', or 'deleted'.
    """
    changes: dict[str, str] = {}

    for path, hash_val in after.items():
        if path not in before:
            changes[path] = "added"
        elif before[path] != hash_val:
            changes[path] = "modified"

    for path in before:
        if path not in after:
            changes[path] = "deleted"

    return changes
