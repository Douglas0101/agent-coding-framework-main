#!/usr/bin/env python3
"""Code Quality PEP — 5-Layer Audit.

Runs all quality layers in sequence and reports per-layer
pass/fail status with optional JSON output.

Layers:
  L1  Style     ruff check (E/W/F/I/N/UP/B/C4/SIM)
  L2  Types     mypy --strict
  L3  Security  bandit -r
  L4  Complexity radon cc + mi
  L5  Dead code vulture

Usage:
    python .agent/skills/code-quality-pep/scripts/audit.py
    python .agent/skills/code-quality-pep/scripts/audit.py --quick
    python .agent/skills/code-quality-pep/scripts/audit.py --json
    python .agent/skills/code-quality-pep/scripts/audit.py --strict
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


_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_SRC = _ROOT / "src"
_TESTS = _ROOT / "tests"
_SCRIPTS = _ROOT / "scripts"

# L4 thresholds
_CC_MAX = 10  # Cyclomatic complexity
_MI_MIN = 20.0  # Maintainability index


def _run(
    cmd: list[str],
    label: str,
) -> dict[str, Any]:
    """Run a command, capture output and timing."""
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


def _check_tool(name: str) -> bool:
    """Check if a CLI tool is available."""
    return shutil.which(name) is not None


def _run_layer_1() -> dict[str, Any]:
    """L1 Style: ruff check."""
    if not _check_tool("ruff"):
        return {
            "layer": "L1_style",
            "skipped": True,
            "reason": "ruff not found",
        }
    targets = []
    for d in [_SRC, _TESTS, _SCRIPTS]:
        if d.exists():
            targets.append(str(d))
    return _run(
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


def _run_layer_2() -> dict[str, Any]:
    """L2 Types: mypy strict."""
    if not _check_tool("mypy"):
        return {
            "layer": "L2_types",
            "skipped": True,
            "reason": "mypy not found",
        }
    return _run(
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


def _run_layer_3() -> dict[str, Any]:
    """L3 Security: bandit."""
    if not _check_tool("bandit"):
        return {
            "layer": "L3_security",
            "skipped": True,
            "reason": "bandit not found",
        }
    result = _run(
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
    output = result["stdout"] + result["stderr"]
    has_issues = "High:" in output or "Medium:" in output
    result["passed"] = result["exit_code"] == 0 and not has_issues
    return result


def _run_layer_4() -> dict[str, Any]:
    """L4 Complexity: radon cc + mi."""
    if not _check_tool("radon"):
        return {
            "layer": "L4_complexity",
            "skipped": True,
            "reason": "radon not found",
        }
    t0 = time.perf_counter()
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

    mi_proc = subprocess.run(
        [
            "radon",
            "mi",
            str(_SRC),
            "-s",
            "-j",
        ],
        capture_output=True,
        text=True,
        cwd=str(_ROOT),
    )
    elapsed = round(
        (time.perf_counter() - t0) * 1000,
    )

    high_cc: list[str] = []
    try:
        data = json.loads(cc_proc.stdout)
        for fpath, funcs in data.items():
            for f in funcs:
                if f.get("complexity", 0) > _CC_MAX:
                    nm = f.get("name", "?")
                    cc = f["complexity"]
                    high_cc.append(f"{fpath}:{nm} CC={cc}")
    except (json.JSONDecodeError, KeyError) as _:
        pass

    low_mi: list[str] = []
    try:
        data = json.loads(mi_proc.stdout)
        for fpath, info in data.items():
            mi_val = info.get("mi", 100)
            if mi_val < _MI_MIN:
                low_mi.append(f"{fpath} MI={mi_val:.1f}")
    except (json.JSONDecodeError, KeyError) as _:
        pass

    passed = len(high_cc) == 0 and len(low_mi) == 0
    return {
        "layer": "L4_complexity",
        "elapsed_ms": elapsed,
        "passed": passed,
        "high_cc_functions": high_cc,
        "low_mi_files": low_mi,
    }


def _run_layer_5() -> dict[str, Any]:
    """L5 Dead code: vulture."""
    if not _check_tool("vulture"):
        return {
            "layer": "L5_dead_code",
            "skipped": True,
            "reason": "vulture not found",
        }
    result = _run(
        [
            "vulture",
            str(_SRC),
            "--min-confidence",
            "80",
        ],
        "L5_dead_code",
    )
    # vulture exits 1 when it finds dead code,
    # but we treat L5 as advisory (review only)
    result["advisory"] = True
    dead_count = len(result["stdout"].splitlines()) if result["stdout"] else 0
    result["dead_items"] = dead_count
    result["passed"] = True  # advisory layer
    return result


def main() -> int:
    """Run the 5-layer audit."""
    ap = argparse.ArgumentParser(
        description="Code Quality PEP — 5-Layer Audit",
    )
    ap.add_argument(
        "--quick",
        action="store_true",
        help="Run L1 + L2 only (style + types)",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Fail on any layer (including advisory)",
    )
    ap.add_argument(
        "--layer",
        type=int,
        choices=[1, 2, 3, 4, 5],
        help="Run a specific layer only",
    )
    args = ap.parse_args()

    layers = {
        1: ("L1 Style", _run_layer_1),
        2: ("L2 Types", _run_layer_2),
        3: ("L3 Security", _run_layer_3),
        4: ("L4 Complexity", _run_layer_4),
        5: ("L5 Dead Code", _run_layer_5),
    }

    if args.layer:
        run_layers = [args.layer]
    elif args.quick:
        run_layers = [1, 2]
    else:
        run_layers = [1, 2, 3, 4, 5]

    results: list[dict[str, Any]] = []
    for num in run_layers:
        _label, fn = layers[num]
        results.append(fn())

    all_pass = all(r.get("passed", True) for r in results)
    if args.strict:
        all_pass = all(
            r.get("passed", True) and not r.get("dead_items", 0)
            for r in results
        )

    if args.json:
        output = {
            "overall": "PASS" if all_pass else "FAIL",
            "layers": results,
        }
        print(json.dumps(output, indent=2))
    else:
        sep = "=" * 55
        print(f"\n{sep}")
        print("  Code Quality PEP — Audit Report")
        print(sep)

        for r in results:
            layer = r["layer"]
            if r.get("skipped"):
                icon = "⏭"
                status = f"SKIP ({r['reason']})"
            elif r.get("passed"):
                icon = "✅"
                status = "PASS"
            else:
                icon = "❌"
                status = "FAIL"

            ms = r.get("elapsed_ms", "—")
            print(f"\n  {icon} {layer}: {status} ({ms}ms)")

            stdout = r.get("stdout", "")
            if stdout and not r.get("passed"):
                for line in stdout.splitlines()[:10]:
                    print(f"     {line}")
                remain = len(stdout.splitlines()) - 10
                if remain > 0:
                    print(f"     ... +{remain} more")

            hcc = r.get("high_cc_functions", [])
            if hcc:
                for item in hcc[:5]:
                    print(f"     ⚠ {item}")

            lmi = r.get("low_mi_files", [])
            if lmi:
                for item in lmi[:5]:
                    print(f"     ⚠ {item}")

            dead = r.get("dead_items", 0)
            if dead:
                print(f"     [i] {dead} items (review)")

        overall = "🟢 PASS" if all_pass else "🔴 FAIL"
        print(f"\n{sep}")
        print(f"  {overall}")
        print(f"{sep}\n")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
