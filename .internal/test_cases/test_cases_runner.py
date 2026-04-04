#!/usr/bin/env python3
"""Test runner for Hybrid Core classification.

Runs all test cases and validates that scope detection correctly
classifies tasks into tiers.

Usage:
    python test_cases_runner.py
"""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent / "runtime"))

import yaml
from scope_detector import ScopeDetector


def load_test_cases() -> list[dict[str, Any]]:
    """Load all test cases from YAML files."""
    test_dir = Path(__file__).parent
    test_files = [
        test_dir / "tier1_universal.yaml",
        test_dir / "tier2_algorithmic.yaml",
        test_dir / "tier3_competitive.yaml",
    ]

    test_cases = []
    for test_file in test_files:
        if test_file.exists():
            content = test_file.read_text()
            current_case = {}
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("task:"):
                    current_case["task"] = line.replace("task:", "").strip().strip('"')
                elif line.startswith("expected_tier:"):
                    current_case["expected_tier"] = line.replace(
                        "expected_tier:", ""
                    ).strip()
                elif line.startswith("expected_profile:"):
                    current_case["expected_profile"] = line.replace(
                        "expected_profile:", ""
                    ).strip()
                    if "task" in current_case:
                        test_cases.append(current_case.copy())
                        current_case = {}
            if "task" in current_case and "expected_tier" in current_case:
                test_cases.append(current_case)

    return test_cases


def run_tests():
    """Run all test cases and report results."""
    detector = ScopeDetector()
    test_cases = load_test_cases()

    print(f"Running {len(test_cases)} test cases...\n")

    passed = 0
    failed = 0
    results = []

    for i, tc in enumerate(test_cases, 1):
        result = detector.classify(tc["task"], {})

        tier_match = result.tier == tc["expected_tier"]
        profile_match = result.profile == tc["expected_profile"]

        is_pass = tier_match and profile_match

        if is_pass:
            passed += 1
        else:
            failed += 1

        results.append(
            {
                "num": i,
                "task": tc["task"][:60] + "..." if len(tc["task"]) > 60 else tc["task"],
                "expected_tier": tc["expected_tier"],
                "actual_tier": result.tier,
                "tier_match": tier_match,
                "expected_profile": tc["expected_profile"],
                "actual_profile": result.profile,
                "profile_match": profile_match,
                "is_pass": is_pass,
            }
        )

    print(f"{'#':>3} {'Expected':<25} {'Actual':<25} {'Status'}")
    print("-" * 65)

    for r in results:
        tier_status = "✅" if r["tier_match"] else "❌"
        print(
            f"{r['num']:>3} {r['expected_tier']:<25} {r['actual_tier']:<25} {tier_status}"
        )

    print(f"\nResults: {passed} passed, {failed} failed out of {len(test_cases)}")

    if failed > 0:
        print("\nFailed cases:")
        for r in results:
            if not r["is_pass"]:
                print(f"  - {r['task'][:50]}...")
                print(f"    Expected: {r['expected_tier']} / {r['expected_profile']}")
                print(f"    Got:      {r['actual_tier']} / {r['actual_profile']}")

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
