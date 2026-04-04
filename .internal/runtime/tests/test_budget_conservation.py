"""Tests for budget conservation module."""

from __future__ import annotations

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from budget_conservation import (
    BudgetEnforcer,
    CompressionEngine,
    BudgetAllocation,
    CompressedPayload,
    COORDINATION_OVERHEAD,
)


class TestBudgetAllocation:
    def test_initial_state(self):
        alloc = BudgetAllocation(
            step_id="step-01",
            mode="explore",
            allocated={"max_input_tokens": 8000, "max_iterations": 15},
        )
        assert alloc.remaining == {"max_input_tokens": 8000, "max_iterations": 15}
        assert alloc.utilization == {"max_input_tokens": 0.0, "max_iterations": 0.0}
        assert not alloc.is_exceeded
        assert not alloc.is_exhausted

    def test_consume_within_budget(self):
        alloc = BudgetAllocation(
            step_id="step-01",
            mode="explore",
            allocated={"max_input_tokens": 8000},
        )
        success, msg = alloc.consume("max_input_tokens", 5000)
        assert success
        assert alloc.remaining["max_input_tokens"] == 3000

    def test_consume_exceeds_budget(self):
        alloc = BudgetAllocation(
            step_id="step-01",
            mode="explore",
            allocated={"max_input_tokens": 8000},
        )
        success, msg = alloc.consume("max_input_tokens", 9000)
        assert not success
        assert "exceeded" in msg

    def test_exhausted_threshold(self):
        alloc = BudgetAllocation(
            step_id="step-01",
            mode="explore",
            allocated={"max_input_tokens": 1000},
        )
        alloc.consume("max_input_tokens", 950)
        assert alloc.is_exhausted
        assert alloc.status == "exhausted"

    def test_to_dict(self):
        alloc = BudgetAllocation(
            step_id="step-01",
            mode="explore",
            allocated={"max_input_tokens": 8000},
        )
        d = alloc.to_dict()
        assert "step_id" in d
        assert "remaining" in d
        assert "utilization" in d


class TestBudgetEnforcer:
    def test_no_parent_budget_fails(self):
        enforcer = BudgetEnforcer(run_id="test-be-001")
        success, errors = enforcer.allocate_children(
            [{"step_id": "s1", "mode": "explore", "budget": {}}]
        )
        assert not success

    def test_conservation_pass(self):
        enforcer = BudgetEnforcer(run_id="test-be-002")
        enforcer.set_parent_budget({"max_input_tokens": 32000})
        success, errors = enforcer.allocate_children(
            [
                {
                    "step_id": "s1",
                    "mode": "explore",
                    "budget": {"max_input_tokens": 8000},
                },
                {
                    "step_id": "s2",
                    "mode": "autocoder",
                    "budget": {"max_input_tokens": 16000},
                },
            ]
        )
        assert success
        assert not errors

    def test_conservation_fail(self):
        enforcer = BudgetEnforcer(run_id="test-be-003")
        enforcer.set_parent_budget({"max_input_tokens": 10000})
        success, errors = enforcer.allocate_children(
            [
                {
                    "step_id": "s1",
                    "mode": "explore",
                    "budget": {"max_input_tokens": 8000},
                },
                {
                    "step_id": "s2",
                    "mode": "autocoder",
                    "budget": {"max_input_tokens": 8000},
                },
            ]
        )
        assert not success
        assert any("conservation violated" in e for e in errors)

    def test_consume_and_status(self):
        enforcer = BudgetEnforcer(run_id="test-be-004")
        enforcer.set_parent_budget({"max_input_tokens": 32000})
        enforcer.allocate_children(
            [
                {
                    "step_id": "s1",
                    "mode": "explore",
                    "budget": {"max_input_tokens": 8000},
                },
            ]
        )
        success, _ = enforcer.consume("s1", "max_input_tokens", 5000)
        assert success

        status = enforcer.get_status("s1")
        assert status is not None
        assert status["remaining"]["max_input_tokens"] == 3000

    def test_unknown_step(self):
        enforcer = BudgetEnforcer(run_id="test-be-005")
        success, msg = enforcer.consume("nonexistent", "max_input_tokens", 100)
        assert not success
        assert "Unknown step" in msg

    def test_get_all_status(self):
        enforcer = BudgetEnforcer(run_id="test-be-006")
        enforcer.set_parent_budget({"max_input_tokens": 32000})
        enforcer.allocate_children(
            [
                {
                    "step_id": "s1",
                    "mode": "explore",
                    "budget": {"max_input_tokens": 8000},
                },
            ]
        )
        status = enforcer.get_all_status()
        assert status["run_id"] == "test-be-006"
        assert "s1" in status["children"]


class TestCompressionEngine:
    def test_compress_none_mode(self):
        content = "Some content"
        payload = CompressionEngine.compress(content, mode="none")
        assert payload.compression_mode == "none"
        assert payload.original_size == len(content.encode())
        assert payload.compression_ratio == 1.0

    def test_compress_summary(self):
        content = "\n".join([f"Line {i}" for i in range(50)])
        payload = CompressionEngine.compress(content, mode="summary")
        assert payload.compression_mode == "summary"
        assert payload.compression_ratio < 1.0
        assert "Line 0" in payload.summary
        assert "Line 49" in payload.summary

    def test_compress_summary_with_refs(self):
        content = "Important content here"
        payload = CompressionEngine.compress(
            content, mode="summary+refs", refs=["ref-001"]
        )
        assert payload.compression_mode == "summary+refs"
        assert payload.refs == ["ref-001"]

    def test_compress_delta_no_previous(self):
        content = "Some content"
        payload = CompressionEngine.compress(content, mode="delta")
        assert payload.compression_mode == "delta"

    def test_compress_delta_with_previous(self):
        original = "Line 1\nLine 2\nLine 3"
        modified = "Line 1\nLine 2 modified\nLine 3\nLine 4"
        payload = CompressionEngine.compress(
            modified, mode="delta", previous_content=original
        )
        assert payload.compression_mode == "delta"
        assert "+ Line 4" in payload.summary

    def test_decompress_roundtrip(self):
        content = "Hello, world!"
        payload = CompressionEngine.compress(content, mode="summary")
        decompressed = CompressionEngine.decompress(payload)
        assert "Hello, world!" in decompressed

    def test_rehydrate_with_refs(self):
        content = "Base context"
        payload = CompressionEngine.compress(
            content, mode="summary+refs", refs=["ref-a"]
        )
        result = CompressionEngine.rehydrate(
            payload,
            ref_resolver={"ref-a": "Resolved reference content"},
        )
        assert result.success
        assert len(result.resolved_refs) == 1
        assert not result.errors

    def test_rehydrate_missing_ref(self):
        content = "Base context"
        payload = CompressionEngine.compress(
            content, mode="summary+refs", refs=["missing-ref"]
        )
        result = CompressionEngine.rehydrate(payload, ref_resolver={})
        assert not result.success
        assert len(result.errors) == 1

    def test_summarize_short_content(self):
        content = "Short"
        summary = CompressionEngine._summarize(content)
        assert summary == content

    def test_summarize_long_content(self):
        content = "\n".join([f"Line {i}" for i in range(100)])
        summary = CompressionEngine._summarize(content)
        assert "Line 0" in summary
        assert "Line 99" in summary
        assert "omitted" in summary

    def test_delta_no_changes(self):
        content = "Same content"
        payload = CompressionEngine.compress(
            content, mode="delta", previous_content=content
        )
        assert "(no changes)" in payload.summary


class TestBudgetConservationIntegration:
    def test_full_workflow(self):
        enforcer = BudgetEnforcer(run_id="test-integration-001")
        enforcer.set_parent_budget(
            {
                "max_input_tokens": 32000,
                "max_output_tokens": 48000,
                "max_iterations": 50,
                "timeout_seconds": 3600,
            }
        )

        success, errors = enforcer.allocate_children(
            [
                {
                    "step_id": "step-01",
                    "mode": "explore",
                    "budget": {
                        "max_input_tokens": 8000,
                        "max_output_tokens": 12000,
                        "max_iterations": 15,
                        "timeout_seconds": 300,
                    },
                },
                {
                    "step_id": "step-02",
                    "mode": "autocoder",
                    "budget": {
                        "max_input_tokens": 16000,
                        "max_output_tokens": 24000,
                        "max_iterations": 25,
                        "timeout_seconds": 900,
                    },
                },
            ]
        )
        assert success

        ok, _ = enforcer.consume("step-01", "max_input_tokens", 5000)
        assert ok

        status = enforcer.get_status("step-01")
        assert status["remaining"]["max_input_tokens"] == 3000
        assert status["utilization"]["max_input_tokens"] == 0.625
