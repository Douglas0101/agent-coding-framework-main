#!/usr/bin/env python3
"""Code Quality PEP — Safe Auto-Fix.

Chains safe auto-fix tools in sequence:
  1. ruff check --fix  (safe lint fixes)
  2. ruff format       (PEP 8 formatting)
  3. isort             (import ordering)

Usage:
    python .agent/skills/code-quality-pep/scripts/autofix.py
    python .agent/skills/code-quality-pep/scripts/autofix.py --dry-run
    python .agent/skills/code-quality-pep/scripts/autofix.py --format-only
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_SRC = _ROOT / "src"
_TESTS = _ROOT / "tests"
_SCRIPTS = _ROOT / "scripts"


def _targets() -> list[str]:
    """Collect existing source directories."""
    dirs: list[str] = []
    for d in [_SRC, _TESTS, _SCRIPTS]:
        if d.exists():
            dirs.append(str(d))
    return dirs


def _run_step(
    label: str,
    cmd: list[str],
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run a single auto-fix step."""
    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(_ROOT),
    )
    elapsed = round(
        (time.perf_counter() - t0) * 1000,
    )
    output = proc.stdout.strip()
    changed = bool(
        output
        and "no changes" not in output.lower()
        and "already" not in output.lower()
    )
    return {
        "step": label,
        "cmd": " ".join(cmd),
        "elapsed_ms": elapsed,
        "exit_code": proc.returncode,
        "output": output,
        "changed": changed and not dry_run,
        "dry_run": dry_run,
    }


def main() -> int:
    """Run the auto-fix chain."""
    ap = argparse.ArgumentParser(
        description="Code Quality PEP — Auto-Fix",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying",
    )
    ap.add_argument(
        "--format-only",
        action="store_true",
        help="Only run formatting (skip lint fix)",
    )
    args = ap.parse_args()

    targets = _targets()
    if not targets:
        print("No source directories found.")
        return 1

    results: list[dict[str, Any]] = []
    py = sys.executable

    # Step 1: ruff check --fix
    if not args.format_only:
        has_ruff = shutil.which("ruff") is not None
        if has_ruff:
            fix_cmd = [
                py,
                "-m",
                "ruff",
                "check",
                *targets,
                "--fix",
            ]
            if args.dry_run:
                fix_cmd = [
                    py,
                    "-m",
                    "ruff",
                    "check",
                    *targets,
                    "--fix",
                    "--diff",
                ]
            results.append(
                _run_step(
                    "ruff_fix",
                    fix_cmd,
                    dry_run=args.dry_run,
                )
            )

    # Step 2: ruff format
    has_ruff = shutil.which("ruff") is not None
    if has_ruff:
        fmt_cmd = [
            py,
            "-m",
            "ruff",
            "format",
            *targets,
        ]
        if args.dry_run:
            fmt_cmd.append("--check")
        results.append(
            _run_step(
                "ruff_format",
                fmt_cmd,
                dry_run=args.dry_run,
            )
        )

    # Step 3: isort
    has_isort = shutil.which("isort") is not None
    if has_isort:
        isort_cmd = [
            py,
            "-m",
            "isort",
            *targets,
        ]
        if args.dry_run:
            isort_cmd.append("--check-only")
        results.append(
            _run_step(
                "isort",
                isort_cmd,
                dry_run=args.dry_run,
            )
        )

    # Report
    sep = "=" * 55
    mode = "DRY RUN" if args.dry_run else "APPLIED"
    print(f"\n{sep}")
    print(f"  Code Quality PEP — Auto-Fix ({mode})")
    print(sep)

    total_changes = 0
    for r in results:
        step = r["step"]
        ms = r["elapsed_ms"]
        if r["changed"]:
            icon = "🔧"
            status = "CHANGED"
            total_changes += 1
        elif r["exit_code"] != 0:
            icon = "⚠️"
            status = "ISSUES"
        else:
            icon = "✅"
            status = "CLEAN"

        print(f"\n  {icon} {step}: {status} ({ms}ms)")

        out = r.get("output", "")
        if out and r["exit_code"] != 0:
            for line in out.splitlines()[:8]:
                print(f"     {line}")
            remaining = len(out.splitlines()) - 8
            if remaining > 0:
                print(f"     ... +{remaining} more")

    print(f"\n{sep}")
    if total_changes:
        print(f"  🔧 {total_changes} step(s) applied")
    else:
        print("  ✅ No changes needed")
    print(f"{sep}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
