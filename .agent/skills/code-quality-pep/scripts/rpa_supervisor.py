#!/usr/bin/env python3
"""RPA Supervisor - Supervised Code Quality Engine.

Five-phase loop that scans → fixes → verifies → tests → reports,
converging toward zero issues with a maximum iteration limit.

Phases:
    1. PRE-FLIGHT   - Validate tools and snapshot state
    2. DEEP SCAN    - L0 AST + L1-L5 static analysis
    3. SUPERVISED FIX - ruff auto-fix + AST logic fixes
    4. VERIFICATION  - Re-scan + pytest regression check
    5. REPORT        - Per-layer summary with metric deltas

Usage:
    python .agent/skills/code-quality-pep/scripts/rpa_supervisor.py
    python .agent/skills/code-quality-pep/scripts/rpa_supervisor.py --fix
    python .agent/skills/code-quality-pep/scripts/rpa_supervisor.py \
        --fix --max-iterations 3
    python .agent/skills/code-quality-pep/scripts/rpa_supervisor.py --json
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from analyzers.ast_logic_analyzer import (
    AnalysisResult as LogicResult,
)
from analyzers.ast_logic_analyzer import (
    analyze_directory as analyze_logic,
)
from analyzers.data_structure_checker import (
    StructResult,
)
from analyzers.data_structure_checker import (
    analyze_directory as analyze_structure,
)
from analyzers.syntax_validator import (
    SyntaxResult,
)
from analyzers.syntax_validator import (
    validate_directory as validate_syntax,
)
from fixers.logic_fixer import FixResult
from fixers.logic_fixer import fix_directory as fix_logic
from fixers.safe_transforms import compare_snapshots, snapshot_directory


# ── Resolve project root ──────────────────────
_SCRIPT_DIR = Path(__file__).resolve().parent
_ROOT = _SCRIPT_DIR.parent.parent.parent.parent
_SRC = _ROOT / "src"
_TESTS = _ROOT / "tests"
_SCRIPTS = _ROOT / "scripts"


# ── Constants ─────────────────────────────────
_DEFAULT_MAX_ITERS = 3
_EXCLUDE = frozenset(
    {
        "__pycache__",
        ".git",
        ".mypy_cache",
        ".ruff_cache",
        ".agent",
        ".benchmarks",
        "egg-info",
    }
)


def _snapshot_targets() -> dict[str, Path]:
    """Return directories that should be tracked for change detection."""
    targets = {
        "src": _SRC,
        "tests": _TESTS,
        "scripts": _SCRIPTS,
    }
    return {name: path for name, path in targets.items() if path.exists()}


def _snapshot_workspace() -> dict[str, str]:
    """Create a combined snapshot for src/tests/scripts."""
    snapshot: dict[str, str] = {}
    for name, path in _snapshot_targets().items():
        target_snapshot = snapshot_directory(path, exclude=_EXCLUDE)
        for rel_path, hash_value in target_snapshot.items():
            snapshot[f"{name}/{rel_path}"] = hash_value
    return snapshot


# ══════════════════════════════════════════════
# Phase 1: Pre-flight
# ══════════════════════════════════════════════


def _check_tools() -> dict[str, bool]:
    """Verify required tools are available."""
    tools = ["ruff", "mypy", "bandit", "radon", "vulture"]
    return {t: shutil.which(t) is not None for t in tools}


def _phase_preflight() -> dict[str, Any]:
    """Phase 1: pre-flight checks."""
    tools = _check_tools()
    missing = [t for t, ok in tools.items() if not ok]
    snapshot = _snapshot_workspace()

    return {
        "phase": "preflight",
        "tools": tools,
        "missing_tools": missing,
        "snapshot_files": len(snapshot),
        "snapshot": snapshot,
        "passed": len(missing) == 0,
    }


# ══════════════════════════════════════════════
# Phase 2: Deep Scan (L0 + L1-L5)
# ══════════════════════════════════════════════


def _run_cmd(
    cmd: list[str],
    label: str,
) -> dict[str, Any]:
    """Run a tool command and capture results."""
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
    return {
        "layer": label,
        "exit_code": proc.returncode,
        "elapsed_ms": elapsed,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "passed": proc.returncode == 0,
    }


def _count_issues(
    output: str,
    *,
    skip_notes: bool = False,
) -> int:
    """Count non-empty lines in tool output.

    When *skip_notes* is True, lines starting with
    'note:' or 'Found N error' (mypy summary) are
    excluded from the count.
    """
    if not output:
        return 0
    lines = [ln for ln in output.splitlines() if ln.strip()]
    if skip_notes:
        lines = [
            ln
            for ln in lines
            if not ln.strip().startswith("note:")
            and not ln.strip().startswith("Found ")
            and ": note:" not in ln
        ]
    return len(lines)


def _phase_scan() -> dict[str, Any]:
    """Phase 2: deep scan across all layers."""
    t0 = time.perf_counter()
    results: dict[str, dict[str, Any]] = {}

    # L0: AST analysis (logic + structure + syntax)
    logic: LogicResult = analyze_logic(
        _SRC,
        exclude=_EXCLUDE,
    )
    struct: StructResult = analyze_structure(
        _SRC,
        exclude=_EXCLUDE,
    )
    syntax: SyntaxResult = validate_syntax(
        _SRC,
        exclude=_EXCLUDE,
    )

    results["L0_logic"] = {
        "layer": "L0_logic",
        "issues": logic.total,
        "passed": logic.passed,
        "detail": logic.to_dict(),
    }
    results["L0_structure"] = {
        "layer": "L0_structure",
        "issues": struct.total,
        "passed": struct.passed,
        "detail": struct.to_dict(),
    }
    results["L0_syntax"] = {
        "layer": "L0_syntax",
        "issues": syntax.total,
        "passed": syntax.passed,
        "detail": syntax.to_dict(),
    }

    # L1: Style (ruff)
    targets = [str(d) for d in [_SRC, _TESTS, _SCRIPTS] if d.exists()]
    if shutil.which("ruff"):
        l1 = _run_cmd(
            [
                sys.executable,
                "-m",
                "ruff",
                "check",
                *targets,
                "--output-format=concise",
            ],
            "L1_style",
        )
        l1["issues"] = 0 if l1["passed"] else _count_issues(l1["stdout"])
        results["L1_style"] = l1

    # L2: Types (mypy)
    if shutil.which("mypy"):
        l2 = _run_cmd(
            [
                sys.executable,
                "-m",
                "mypy",
                str(_SRC),
                "--ignore-missing-imports",
                "--no-error-summary",
            ],
            "L2_types",
        )
        l2["issues"] = _count_issues(
            l2["stdout"],
            skip_notes=True,
        )
        # Use issue count for pass/fail (mypy exits 1
        # even for notes-only output)
        l2["passed"] = l2["issues"] == 0
        results["L2_types"] = l2

    # L3: Security (bandit)
    if shutil.which("bandit"):
        l3 = _run_cmd(
            [
                sys.executable,
                "-m",
                "bandit",
                "-r",
                str(_SRC),
                "-c",
                str(_ROOT / "pyproject.toml"),
                "-q",
            ],
            "L3_security",
        )
        output = l3["stdout"] + l3["stderr"]
        has_sec = "High:" in output or "Medium:" in output
        l3["passed"] = l3["exit_code"] == 0 and not has_sec
        l3["issues"] = _count_issues(l3["stdout"])
        results["L3_security"] = l3

    # L4: Complexity (radon)
    if shutil.which("radon"):
        cc_proc = subprocess.run(
            [
                "radon",
                "cc",
                str(_SRC),
                "-s",
                "-n",
                "C",
                "-j",
            ],
            capture_output=True,
            text=True,
            cwd=str(_ROOT),
        )
        high_cc = 0
        try:
            data = json.loads(cc_proc.stdout)
            for _fpath, funcs in data.items():
                for f in funcs:
                    if f.get("complexity", 0) > 10:
                        high_cc += 1
        except (json.JSONDecodeError, KeyError) as _:
            pass

        results["L4_complexity"] = {
            "layer": "L4_complexity",
            "issues": high_cc,
            "passed": high_cc == 0,
        }

    # L5: Dead code (vulture) — advisory
    if shutil.which("vulture"):
        l5 = _run_cmd(
            [
                "vulture",
                str(_SRC),
                "--min-confidence",
                "80",
            ],
            "L5_dead_code",
        )
        l5["issues"] = _count_issues(l5["stdout"])
        l5["passed"] = True  # advisory
        l5["advisory"] = True
        results["L5_dead_code"] = l5

    elapsed = round(
        (time.perf_counter() - t0) * 1000,
    )

    total_issues = sum(
        r.get("issues", 0) for r in results.values() if not r.get("advisory")
    )

    return {
        "phase": "scan",
        "elapsed_ms": elapsed,
        "layers": results,
        "total_issues": total_issues,
        "passed": total_issues == 0,
    }


# ══════════════════════════════════════════════
# Phase 3: Supervised Fix
# ══════════════════════════════════════════════


def _phase_fix(*, dry_run: bool = False) -> dict[str, Any]:
    """Phase 3: apply safe auto-fixes."""
    t0 = time.perf_counter()
    all_actions: list[dict[str, Any]] = []

    # Step 1: ruff auto-fix (formatting + lint)
    targets = [str(d) for d in [_SRC, _TESTS, _SCRIPTS] if d.exists()]
    ruff_applied = False
    if shutil.which("ruff") and not dry_run:
        snapshot_before_ruff = _snapshot_workspace()
        # Lint fix (--unsafe-fixes enables UP045,
        # RUF012, and similar rules)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "ruff",
                "check",
                *targets,
                "--fix",
                "--unsafe-fixes",
                "--silent",
            ],
            capture_output=True,
            text=True,
            cwd=str(_ROOT),
        )
        # Format
        subprocess.run(
            [
                sys.executable,
                "-m",
                "ruff",
                "format",
                *targets,
            ],
            capture_output=True,
            text=True,
            cwd=str(_ROOT),
        )
        snapshot_after_ruff = _snapshot_workspace()
        ruff_applied = (
            len(compare_snapshots(snapshot_before_ruff, snapshot_after_ruff))
            > 0
        )
        all_actions.append(
            {"step": "ruff_autofix", "applied": ruff_applied},
        )

    # Step 2: AST logic fixes
    logic_result: FixResult = fix_logic(
        _SRC,
        dry_run=dry_run,
        exclude=_EXCLUDE,
    )
    all_actions.extend(
        [f.to_dict() for f in logic_result.fixes],
    )

    elapsed = round(
        (time.perf_counter() - t0) * 1000,
    )

    return {
        "phase": "fix",
        "elapsed_ms": elapsed,
        "dry_run": dry_run,
        "ruff_applied": ruff_applied,
        "logic_fixes": logic_result.total,
        "files_modified": logic_result.files_modified,
        "actions": all_actions,
    }


# ══════════════════════════════════════════════
# Phase 4: Verification
# ══════════════════════════════════════════════


def _phase_verify(
    snapshot_before: dict[str, str],
    *,
    skip_tests: bool = False,
) -> dict[str, Any]:
    """Phase 4: full re-scan + pytest regression check."""
    t0 = time.perf_counter()

    # Compare file snapshots
    snapshot_after = _snapshot_workspace()
    changes = compare_snapshots(
        snapshot_before,
        snapshot_after,
    )

    # Full L0-L5 rescan (not ruff-only) for accurate
    # delta measurement across iterations
    rescan = _phase_scan()
    rescan_issues = rescan["total_issues"]

    # Run pytest
    test_result: dict[str, Any] = {"skipped": True}
    if not skip_tests and _TESTS.exists():
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(_TESTS),
                "-v",
                "--tb=short",
                "-q",
            ],
            capture_output=True,
            text=True,
            cwd=str(_ROOT),
        )
        test_result = {
            "skipped": False,
            "exit_code": proc.returncode,
            "passed": proc.returncode == 0,
            "output": proc.stdout.strip()[-500:],
        }

    elapsed = round(
        (time.perf_counter() - t0) * 1000,
    )

    return {
        "phase": "verify",
        "elapsed_ms": elapsed,
        "files_changed": len(changes),
        "changes": changes,
        "rescan_issues": rescan_issues,
        "rescan_detail": rescan.get("layers", {}),
        "tests": test_result,
        "passed": (rescan_issues == 0 and test_result.get("passed", True)),
    }


# ══════════════════════════════════════════════
# Phase 5: Report
# ══════════════════════════════════════════════


def _print_report(
    iterations: list[dict[str, Any]],
    total_elapsed: int,
) -> None:
    """Print the human-readable report."""
    sep = "═" * 60
    thin = "─" * 60

    print(f"\n{sep}")
    print("  🤖 RPA SUPERVISOR — Quality Report")
    print(sep)

    for it in iterations:
        it_num = it["iteration"]
        print(f"\n  ┌{'─' * 50}┐")
        print(f"  │  Iteration {it_num:>2}{'':>38}│")
        print(f"  └{'─' * 50}┘")

        # Scan results
        scan = it.get("scan", {})
        layers = scan.get("layers", {})
        print(f"\n  📊 SCAN ({scan.get('elapsed_ms', 0)}ms)")

        layer_order = [
            "L0_syntax",
            "L0_logic",
            "L0_structure",
            "L1_style",
            "L2_types",
            "L3_security",
            "L4_complexity",
            "L5_dead_code",
        ]
        for layer_name in layer_order:
            layer = layers.get(layer_name)
            if layer is None:
                continue
            issues = layer.get("issues", 0)
            is_advisory = layer.get("advisory", False)
            passed = layer.get("passed", True)

            if passed and issues == 0:
                icon = "✅"
                status = "PASS"
            elif is_advisory:
                icon = "i "
                status = f"{issues} (advisory)"
            else:
                icon = "❌"
                status = f"FAIL ({issues} issues)"

            print(f"    {icon} {layer_name}: {status}")

        # Fix results
        fix = it.get("fix")
        if fix:
            logic_n = fix.get("logic_fixes", 0)
            ruff_ok = fix.get("ruff_applied", False)
            print(f"\n  🔧 FIX ({fix.get('elapsed_ms', 0)}ms)")
            if ruff_ok:
                print("    ✅ ruff auto-fix applied")
            if logic_n:
                print(
                    f"    🔧 {logic_n} AST logic fix(es) in "
                    f"{fix.get('files_modified', 0)} file(s)"
                )
            if not ruff_ok and logic_n == 0:
                print("    — No fixes needed")

        # Verify results
        verify = it.get("verify")
        if verify:
            print(f"\n  🔍 VERIFY ({verify.get('elapsed_ms', 0)}ms)")
            n_changed = verify.get("files_changed", 0)
            rescan = verify.get("rescan_issues", 0)
            print(f"    Files changed: {n_changed}")
            print(f"    Rescan issues: {rescan}")

            tests = verify.get("tests", {})
            if tests.get("skipped"):
                print("    Tests: ⏭  skipped")
            elif tests.get("passed"):
                print("    Tests: ✅ PASS")
            else:
                print("    Tests: ❌ FAIL")

    # Overall
    last = iterations[-1] if iterations else {}
    scan = last.get("scan", {})
    overall_issues = scan.get("total_issues", 0)
    overall_pass = overall_issues == 0

    verify = last.get("verify", {})
    tests_pass = verify.get("tests", {}).get("passed", True)

    print(f"\n{thin}")
    print(f"  ⏱  Total: {total_elapsed}ms")
    print(f"  📈 Iterations: {len(iterations)}")
    print(f"  🎯 Remaining issues: {overall_issues}")

    if overall_pass and tests_pass:
        print("\n  🟢 OVERALL: PASS")
    else:
        print("\n  🔴 OVERALL: FAIL")
        if not tests_pass:
            print("      ∟ Tests failed — review output")
        if not overall_pass:
            print(f"      ∟ {overall_issues} issue(s) remain")

    print(f"{sep}\n")


# ══════════════════════════════════════════════
# Main orchestrator
# ══════════════════════════════════════════════


def run_supervisor(
    *,
    fix: bool = False,
    max_iterations: int = _DEFAULT_MAX_ITERS,
    json_output: bool = False,
    skip_tests: bool = False,
) -> dict[str, Any]:
    """Run the full RPA supervised loop."""
    t_start = time.perf_counter()
    iterations: list[dict[str, Any]] = []

    # Phase 1: Pre-flight
    preflight = _phase_preflight()
    snapshot_before = preflight.pop("snapshot", {})

    if not preflight["passed"]:
        msg = f"Pre-flight failed: missing tools {preflight['missing_tools']}"
        if json_output:
            print(
                json.dumps(
                    {
                        "status": "preflight_failed",
                        "preflight": preflight,
                    },
                    indent=2,
                )
            )
        else:
            print(f"\n  ❌ {msg}\n")
        return {"status": "preflight_failed"}

    prev_issues: int | None = None

    for iteration in range(1, max_iterations + 1):
        it_data: dict[str, Any] = {"iteration": iteration}

        # Phase 2: Scan
        scan = _phase_scan()
        it_data["scan"] = scan
        current_issues = scan["total_issues"]

        # If no issues, done
        if scan["passed"]:
            iterations.append(it_data)
            break

        # Phase 3: Fix (if enabled)
        if fix:
            fix_result = _phase_fix(dry_run=False)
            it_data["fix"] = fix_result

            # Phase 4: Verify
            verify = _phase_verify(
                snapshot_before,
                skip_tests=skip_tests,
            )
            it_data["verify"] = verify

            # Update snapshot for next iteration
            snapshot_before = _snapshot_workspace()
        else:
            # Scan-only mode: no loop
            iterations.append(it_data)
            break

        iterations.append(it_data)

        # Convergence: stop if zero issues, verify
        # passed, or no improvement (plateau)
        if it_data.get("verify", {}).get("passed", False):
            break
        if prev_issues is not None and current_issues >= prev_issues:
            # No improvement — stop iterating
            break
        prev_issues = current_issues

    total_elapsed = round(
        (time.perf_counter() - t_start) * 1000,
    )

    result = {
        "status": "complete",
        "iterations": iterations,
        "total_elapsed_ms": total_elapsed,
        "total_iterations": len(iterations),
    }

    if json_output:
        print(json.dumps(result, indent=2))
    else:
        _print_report(iterations, total_elapsed)

    return result


def main() -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(
        description=("RPA Supervisor — Supervised Code Quality Engine"),
    )
    ap.add_argument(
        "--fix",
        action="store_true",
        help=("Enable auto-fix mode (default: scan-only)"),
    )
    ap.add_argument(
        "--max-iterations",
        type=int,
        default=_DEFAULT_MAX_ITERS,
        help=(f"Max correction iterations (default: {_DEFAULT_MAX_ITERS})"),
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    ap.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip pytest in verification phase",
    )
    args = ap.parse_args()

    result = run_supervisor(
        fix=args.fix,
        max_iterations=args.max_iterations,
        json_output=args.json,
        skip_tests=args.skip_tests,
    )

    last = (result.get("iterations") or [{}])[-1]
    scan = last.get("scan", {})
    if scan.get("passed", False):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
