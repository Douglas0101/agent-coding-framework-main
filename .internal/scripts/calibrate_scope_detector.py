#!/usr/bin/env python3
"""Scope Detector Calibration Tool.

Runs the regression harness and reports accuracy metrics in human-readable
or JSON format.

Usage:
    python .internal/scripts/calibrate_scope_detector.py --verbose
    python .internal/scripts/calibrate_scope_detector.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "runtime"))

from regression_harness import RegressionHarness


def run_calibration() -> dict:
    """Run calibration and return metrics."""
    harness = RegressionHarness()

    all_results = harness.run_all()
    summary = harness.get_summary(all_results)

    fp_results = harness.run_false_positives()
    fp_failures = [r for r in fp_results if r.actual_tier != "tier_1_universal"]

    tier2_results = harness.run_tier("tier2")
    tier2_misses = [r for r in tier2_results if r.actual_tier != "tier_2_algorithmic"]

    tier3_results = harness.run_tier("tier3")
    tier3_misses = [r for r in tier3_results if r.actual_tier != "tier_3_competitive"]

    over_eng = harness.run_over_engineering()
    over_eng_issues = [r for r in over_eng if r.actual_tier != r.expected_tier]

    under_eng = harness.run_under_engineering()
    under_eng_issues = [r for r in under_eng if r.actual_profile != r.expected_profile]

    return {
        "total": summary["total"],
        "passed": summary["passed"],
        "failed": summary["failed"],
        "pass_rate": summary["pass_rate"],
        "false_positives": len(fp_failures),
        "tier2_misses": len(tier2_misses),
        "tier3_misses": len(tier3_misses),
        "over_engineering_issues": len(over_eng_issues),
        "under_engineering_issues": len(under_eng_issues),
        "failed_scenarios": summary.get("failed_scenarios", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hybrid Core scope detector calibration"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON to stdout",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Emit human-readable calibration summary",
    )
    args = parser.parse_args()

    metrics = run_calibration()

    if args.json:
        print(json.dumps(metrics, indent=2, sort_keys=True))
        return 0 if metrics["failed"] == 0 else 1

    if args.verbose or not args.json:
        print("\n" + "=" * 60)
        print("SCOPE DETECTOR CALIBRATION REPORT")
        print("=" * 60)
        print(f"Total scenarios:   {metrics['total']}")
        print(f"Passed:            {metrics['passed']}")
        print(f"Failed:            {metrics['failed']}")
        print(f"Pass rate:         {metrics['pass_rate']:.1%}")
        print()
        print(f"False positives:   {metrics['false_positives']}")
        print(f"Tier 2 misses:     {metrics['tier2_misses']}")
        print(f"Tier 3 misses:     {metrics['tier3_misses']}")
        print(f"Over-eng issues:   {metrics['over_engineering_issues']}")
        print(f"Under-eng issues:  {metrics['under_engineering_issues']}")
        if metrics["failed_scenarios"]:
            print()
            print("Failed scenarios:")
            for failed in metrics["failed_scenarios"]:
                print(f"  - {failed['id']}: {failed['details']}")
        print("=" * 60)

    return 0 if metrics["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
