#!/usr/bin/env python3
"""Code Quality PEP — Complexity Report.

Analyzes cyclomatic complexity and maintainability of Python
source files using radon.

Outputs:
  - Cyclomatic Complexity (CC) per function
  - Maintainability Index (MI) per file
  - Raw metrics (LoC, SLOC, comments, blank lines)
  - Flags functions exceeding the CC threshold

Usage:
    python .agent/skills/code-quality-pep/scripts/complexity_report.py
    python .agent/skills/code-quality-pep/scripts/complexity_report.py --threshold 8
    python .agent/skills/code-quality-pep/scripts/complexity_report.py --json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_SRC = _ROOT / "src"

_DEFAULT_CC_THRESHOLD = 10
_MI_WARN = 20.0


def _run_radon(
    subcmd: str,
    extra_args: list[str],
) -> str:
    """Run a radon sub-command and return stdout."""
    proc = subprocess.run(
        ["radon", subcmd, str(_SRC), *extra_args],
        capture_output=True,
        text=True,
        cwd=str(_ROOT),
    )
    return proc.stdout.strip()


def _cc_analysis(threshold: int) -> dict[str, Any]:
    """Cyclomatic complexity analysis."""
    raw = _run_radon("cc", ["-s", "-j"])
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "error": "Failed to parse radon cc",
        }

    all_funcs: list[dict[str, Any]] = []
    flagged: list[dict[str, Any]] = []

    for fpath, funcs in data.items():
        rel = str(Path(fpath).relative_to(_ROOT))
        for f in funcs:
            entry = {
                "file": rel,
                "name": f.get("name", "?"),
                "type": f.get("type", "?"),
                "complexity": f.get("complexity", 0),
                "rank": f.get("rank", "?"),
                "lineno": f.get("lineno", 0),
            }
            all_funcs.append(entry)
            if entry["complexity"] > threshold:
                flagged.append(entry)

    return {
        "total_functions": len(all_funcs),
        "threshold": threshold,
        "above_threshold": len(flagged),
        "flagged": flagged,
    }


def _mi_analysis() -> dict[str, Any]:
    """Maintainability index analysis."""
    raw = _run_radon("mi", ["-s", "-j"])
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "error": "Failed to parse radon mi",
        }

    files: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    for fpath, info in data.items():
        rel = str(Path(fpath).relative_to(_ROOT))
        mi_val = info.get("mi", 100)
        rank = info.get("rank", "?")
        entry = {
            "file": rel,
            "mi": round(mi_val, 1),
            "rank": rank,
        }
        files.append(entry)
        if mi_val < _MI_WARN:
            warnings.append(entry)

    files.sort(key=lambda x: x["mi"])
    return {
        "total_files": len(files),
        "warnings": len(warnings),
        "low_mi_files": warnings,
        "all_files": files,
    }


def _raw_metrics() -> dict[str, Any]:
    """Raw LoC metrics."""
    raw = _run_radon("raw", ["-s", "-j"])
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "error": "Failed to parse radon raw",
        }

    total_loc = 0
    total_sloc = 0
    total_comments = 0
    total_blank = 0

    for _fpath, info in data.items():
        total_loc += info.get("loc", 0)
        total_sloc += info.get("sloc", 0)
        total_comments += info.get("comments", 0)
        total_blank += info.get("blank", 0)

    comment_pct = 0.0
    if total_sloc > 0:
        comment_pct = round(
            total_comments / total_sloc * 100,
            1,
        )

    return {
        "loc": total_loc,
        "sloc": total_sloc,
        "comments": total_comments,
        "blank": total_blank,
        "comment_ratio_pct": comment_pct,
    }


def main() -> int:
    """Run the complexity report."""
    ap = argparse.ArgumentParser(
        description="Code Quality — Complexity Report",
    )
    ap.add_argument(
        "--threshold",
        type=int,
        default=_DEFAULT_CC_THRESHOLD,
        help=f"CC threshold (default: {_DEFAULT_CC_THRESHOLD})",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    args = ap.parse_args()

    t0 = time.perf_counter()
    cc = _cc_analysis(args.threshold)
    mi = _mi_analysis()
    raw = _raw_metrics()
    elapsed = round(
        (time.perf_counter() - t0) * 1000,
    )

    if args.json:
        output = {
            "cc": cc,
            "mi": mi,
            "raw": raw,
            "elapsed_ms": elapsed,
        }
        print(json.dumps(output, indent=2))
    else:
        sep = "=" * 55
        print(f"\n{sep}")
        print("  Code Quality — Complexity Report")
        print(sep)

        # Raw metrics
        print("\n  📊 Raw Metrics")
        print(f"     LoC:      {raw.get('loc', '?')}")
        sloc = raw.get("sloc", "?")
        print(f"     SLOC:     {sloc}")
        cmts = raw.get("comments", "?")
        print(f"     Comments: {cmts}")
        blank = raw.get("blank", "?")
        print(f"     Blank:    {blank}")
        ratio = raw.get("comment_ratio_pct", "?")
        print(f"     Comment%: {ratio}%")

        # CC
        total = cc.get("total_functions", 0)
        above = cc.get("above_threshold", 0)
        thr = cc.get("threshold", _DEFAULT_CC_THRESHOLD)
        icon = "✅" if above == 0 else "⚠️"
        print(f"\n  {icon} Cyclomatic Complexity")
        print(f"     Functions: {total}")
        print(f"     Threshold: CC ≤ {thr}")
        print(f"     Above:     {above}")

        for f in cc.get("flagged", [])[:10]:
            nm = f["name"]
            cv = f["complexity"]
            ln = f["lineno"]
            fp = f["file"]
            print(f"     🔴 {fp}:{ln} {nm} CC={cv}")

        # MI
        total_f = mi.get("total_files", 0)
        warns = mi.get("warnings", 0)
        icon = "✅" if warns == 0 else "⚠️"
        print(f"\n  {icon} Maintainability Index")
        print(f"     Files:     {total_f}")
        print(f"     Threshold: MI ≥ {_MI_WARN}")
        print(f"     Below:     {warns}")

        for f in mi.get("low_mi_files", [])[:10]:
            fp = f["file"]
            mv = f["mi"]
            print(f"     🔴 {fp} MI={mv}")

        print(f"\n  ⏱  {elapsed}ms")
        print(f"{sep}\n")

    has_issues = cc.get("above_threshold", 0) > 0 or mi.get("warnings", 0) > 0
    return 1 if has_issues else 0


if __name__ == "__main__":
    sys.exit(main())
