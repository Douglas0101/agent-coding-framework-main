"""Tests for Regression Harness."""

from __future__ import annotations

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from regression_harness import RegressionHarness


@pytest.fixture
def harness():
    return RegressionHarness()


class TestRegressionHarnessBasics:
    def test_has_scenarios(self, harness):
        assert len(harness._scenarios) > 0

    def test_run_all_returns_results(self, harness):
        results = harness.run_all()
        assert len(results) > 0

    def test_all_results_have_scenario_id(self, harness):
        results = harness.run_all()
        for r in results:
            assert r.scenario_id.startswith("REG-")


class TestTierScenarios:
    def test_tier1_scenarios(self, harness):
        results = harness.run_tier("tier1")
        assert len(results) > 0
        for r in results:
            assert r.expected_tier == "tier_1_universal"

    def test_tier2_scenarios(self, harness):
        results = harness.run_tier("tier2")
        assert len(results) > 0
        for r in results:
            assert r.expected_tier == "tier_2_algorithmic"

    def test_tier3_scenarios(self, harness):
        results = harness.run_tier("tier3")
        assert len(results) > 0
        for r in results:
            assert r.expected_tier == "tier_3_competitive"


class TestFalsePositivePrevention:
    def test_fp_scenarios_exist(self, harness):
        results = harness.run_false_positives()
        assert len(results) > 0

    def test_fp_stay_tier1(self, harness):
        results = harness.run_false_positives()
        for r in results:
            assert r.actual_tier == "tier_1_universal", (
                f"False positive: {r.scenario_id} classified as {r.actual_tier}"
            )


class TestOverUnderEngineering:
    def test_over_engineering_detected(self, harness):
        results = harness.run_over_engineering()
        assert len(results) > 0
        for r in results:
            assert r.expected_tier == "tier_1_universal"

    def test_under_engineering_triggers_2x(self, harness):
        results = harness.run_under_engineering()
        assert len(results) > 0
        for r in results:
            assert r.expected_profile == "performance_2x"


class TestSummary:
    def test_summary_has_required_fields(self, harness):
        results = harness.run_all()
        summary = harness.get_summary(results)
        assert "total" in summary
        assert "passed" in summary
        assert "failed" in summary
        assert "pass_rate" in summary
        assert "failed_scenarios" in summary

    def test_summary_counts_match(self, harness):
        results = harness.run_all()
        summary = harness.get_summary(results)
        assert summary["total"] == len(results)
        assert summary["passed"] + summary["failed"] == summary["total"]
