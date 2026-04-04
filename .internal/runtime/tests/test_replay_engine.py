"""Tests for the replay engine."""

from __future__ import annotations

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from replay_engine import (
    ReplayEngine,
    ChangeClassifier,
    GoldenTraceManager,
    create_golden_traces,
)


class TestReplayEngine:
    def test_replay_nonexistent_run(self):
        engine = ReplayEngine(run_id="test-replay-001")
        result = engine.replay_run("nonexistent-run")
        assert result.status == "failed"
        assert not result.integrity_match
        assert len(result.discrepancies) > 0

    def test_replay_conformance_record(self, tmp_path, monkeypatch):
        import replay_engine as re

        monkeypatch.setattr(re, "ARTIFACTS_DIR", tmp_path)
        conf_dir = tmp_path / "conformance"
        conf_dir.mkdir(parents=True, exist_ok=True)

        import json

        conf_data = {
            "run_id": "test-run-replay",
            "contract_verification": {"all_passed": True},
            "policy_scan": {"passed": True},
            "approval_decision": {"approved": True},
            "traces": [{"span_id": "span-0000"}],
        }
        (conf_dir / "test-run-replay.json").write_text(json.dumps(conf_data))

        engine = ReplayEngine(run_id="test-replay-002")
        result = engine.replay_run("test-run-replay")
        assert result.status == "success"
        assert result.integrity_match
        assert result.steps_replayed >= 3


class TestChangeClassifier:
    def test_contract_change_critical(self):
        classifier = ChangeClassifier()
        result = classifier.classify(
            "Update mode contract",
            affected_files=[".internal/specs/modes/explore.yaml"],
        )
        assert result.risk_level == "critical"
        assert result.requires_review
        assert result.requires_migration
        assert len(result.affected_contracts) == 1

    def test_skill_change_medium(self):
        classifier = ChangeClassifier()
        result = classifier.classify(
            "Add new skill",
            affected_files=[".internal/skills/new_skill.py"],
        )
        assert result.risk_level == "medium"
        assert not result.requires_review
        assert not result.requires_migration

    def test_pack_change_medium(self):
        classifier = ChangeClassifier()
        result = classifier.classify(
            "Update domain pack",
            affected_files=[".internal/domains/ml-ai/contract.yaml"],
        )
        assert result.risk_level == "medium"

    def test_runtime_change_high(self):
        classifier = ChangeClassifier()
        result = classifier.classify(
            "Update runtime",
            affected_files=[".internal/runtime/contract_verifier.py"],
        )
        assert result.risk_level == "high"
        assert result.requires_review

    def test_config_change_high(self):
        classifier = ChangeClassifier()
        result = classifier.classify(
            "Update config",
            affected_files=["opencode.json"],
        )
        assert result.risk_level == "high"

    def test_routine_low(self):
        classifier = ChangeClassifier()
        result = classifier.classify(
            "Update README",
            affected_files=["docs/README.md"],
        )
        assert result.risk_level == "low"
        assert not result.requires_review

    def test_to_dict(self):
        classifier = ChangeClassifier()
        result = classifier.classify("Test", ["src/main.py"])
        d = result.to_dict()
        assert "classification_id" in d
        assert "risk_level" in d
        assert "impact_matrix" in d


class TestGoldenTraceManager:
    def test_create_and_retrieve(self):
        manager = GoldenTraceManager()
        trace = manager.create_trace(
            name="test_trace",
            description="Test",
            mode="explore",
            input_data={"task": "test"},
            expected_output={"result": "ok"},
        )
        assert trace.trace_id.startswith("gt-")

        retrieved = manager.get_by_name("test_trace")
        assert retrieved is not None
        assert retrieved.mode == "explore"

    def test_get_by_mode(self):
        manager = GoldenTraceManager()
        manager.create_trace("t1", "d1", "explore", {}, {})
        manager.create_trace("t2", "d2", "reviewer", {}, {})
        manager.create_trace("t3", "d3", "explore", {}, {})

        explore_traces = manager.get_by_mode("explore")
        assert len(explore_traces) == 2

    def test_get_nonexistent(self):
        manager = GoldenTraceManager()
        assert manager.get_by_name("nonexistent") is None


class TestCreateGoldenTraces:
    def test_creates_traces(self):
        traces = create_golden_traces()
        assert len(traces) == 3
        modes = {t["mode"] for t in traces}
        assert "explore" in modes
        assert "reviewer" in modes
        assert "orchestrator" in modes
