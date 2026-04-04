"""Tests for the observability module."""

from __future__ import annotations

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from observability import (
    ArtifactLedger,
    EvidenceStore,
    HandoffHistory,
    ObservabilityHub,
)


class TestArtifactLedger:
    def test_record_and_retrieve(self):
        ledger = ArtifactLedger()
        record = ledger.record(
            run_id="test-001",
            artifact_type="report",
            file_path=".internal/artifacts/baseline.md",
            producer="test-agent",
        )
        assert record.artifact_id.startswith("art-")
        assert record.integrity_hash.startswith("sha256:")

        results = ledger.get_by_run("test-001")
        assert len(results) == 1
        assert results[0].artifact_type == "report"

    def test_get_by_type(self):
        ledger = ArtifactLedger()
        ledger.record("test-002", "code", "src/main.py", "autocoder")
        ledger.record("test-002", "report", "reports/summary.md", "reviewer")
        code_results = ledger.get_by_type("code")
        assert len(code_results) == 1

    def test_to_dict(self):
        ledger = ArtifactLedger()
        record = ledger.record("test-003", "spec", "specs/test.yaml", "orchestrator")
        d = record.to_dict()
        assert "artifact_id" in d
        assert "integrity_hash" in d


class TestEvidenceStore:
    def test_store_and_retrieve(self, tmp_path, monkeypatch):
        import observability as obs

        monkeypatch.setattr(obs, "INTERNAL_DIR", tmp_path)
        monkeypatch.setattr(obs, "EVIDENCE_DIR", tmp_path / "evidence")
        (tmp_path / "evidence").mkdir(parents=True, exist_ok=True)

        store = EvidenceStore()
        record = store.store(
            run_id="test-ev-001",
            evidence_type="operational",
            producer="contract_verifier",
            content="All checks passed",
        )
        assert record.evidence_id.startswith("ev-")
        assert record.integrity_hash.startswith("sha256:")

        results = store.get_by_run("test-ev-001")
        assert len(results) == 1

    def test_get_by_type(self):
        store = EvidenceStore()
        store.store("test-ev-002", "session", "reviewer", "Review complete")
        store.store("test-ev-002", "operational", "policy_enforcer", "Scan passed")
        session_results = store.get_by_type("session")
        assert len(session_results) == 1


class TestHandoffHistory:
    def test_log_and_retrieve(self, tmp_path, monkeypatch):
        import observability as obs

        monkeypatch.setattr(obs, "HANDOFF_DIR", tmp_path / "handoffs")
        (tmp_path / "handoffs").mkdir(parents=True, exist_ok=True)

        history = HandoffHistory()
        record = history.log_handoff(
            run_id="test-ho-001",
            producer_agent="explore",
            consumer_agent="autocoder",
            spec_id="handoff-contract",
            spec_version="1.0.0",
            payload_size=3000,
        )
        assert record.handoff_id.startswith("ho-")
        assert record.integrity_hash

        results = history.get_by_run("test-ho-001")
        assert len(results) == 1

    def test_get_by_agent(self, tmp_path, monkeypatch):
        import observability as obs

        monkeypatch.setattr(obs, "HANDOFF_DIR", tmp_path / "handoffs2")
        (tmp_path / "handoffs2").mkdir(parents=True, exist_ok=True)

        history = HandoffHistory()
        history.log_handoff("test-ho-002", "explore", "autocoder", "hc", "1.0.0")
        history.log_handoff("test-ho-002", "autocoder", "reviewer", "hc", "1.0.0")
        results = history.get_by_agent("autocoder")
        assert len(results) == 2


class TestObservabilityHub:
    def test_summary(self, tmp_path, monkeypatch):
        import observability as obs

        monkeypatch.setattr(obs, "LEDGER_DIR", tmp_path / "ledger")
        monkeypatch.setattr(obs, "EVIDENCE_DIR", tmp_path / "evidence")
        monkeypatch.setattr(obs, "HANDOFF_DIR", tmp_path / "handoffs")
        for d in ("ledger", "evidence", "handoffs"):
            (tmp_path / d).mkdir(parents=True, exist_ok=True)

        hub = ObservabilityHub(run_id="test-hub-001")
        hub.record_artifact("report", "test.md", "tester")
        hub.store_evidence("operational", "verifier", "OK")
        hub.log_handoff("explore", "autocoder", "hc", "1.0.0")

        s = hub.summary()
        assert s["run_id"] == "test-hub-001"
        assert s["artifacts"] == 1
        assert s["evidence_records"] == 1
        assert s["handoffs"] == 1
