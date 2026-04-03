"""Stable execution regression tests for routing and guardrails."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
AGENTS_MD = REPO_ROOT / "AGENTS.md"
RUN_AUTOCODE_SH = REPO_ROOT / ".internal/scripts/run-autocode.sh"
ROOT_CONFIG = REPO_ROOT / "opencode.json"


class TestCommandRoutingRegression:
    def test_autocode_without_agent_documents_observed_fallback(self):
        content = AGENTS_MD.read_text(encoding="utf-8")
        assert "NOT routed to the `autocoder` agent" in content
        assert "falls back to the `general` agent with `maxSteps: 50`" in content

    def test_autocode_with_explicit_agent_is_documented_workaround(self):
        content = AGENTS_MD.read_text(encoding="utf-8")
        assert "opencode run --agent autocoder --command autocode" in content

    def test_autocode_wrapper_enforces_supported_path(self):
        content = RUN_AUTOCODE_SH.read_text(encoding="utf-8")
        assert "--agent autocoder" in content
        assert "--command autocode" in content

    def test_no_silent_fallback_is_explicit_guardrail(self):
        content = AGENTS_MD.read_text(encoding="utf-8")
        assert "No silent fallback" in content


class TestStableExecutionGuardrails:
    def test_verifier_gate_is_required(self):
        content = AGENTS_MD.read_text(encoding="utf-8")
        assert "`verifier` is the mandatory gate before `synthesizer`" in content

    def test_write_scope_disjoint_is_required(self):
        content = AGENTS_MD.read_text(encoding="utf-8")
        assert "Keep `write_scope` disjoint across parallel workers" in content

    def test_config_drift_is_fail_fast_in_wrapper(self):
        content = RUN_AUTOCODE_SH.read_text(encoding="utf-8")
        assert "Missing $DOT_CONFIG" in content
        assert "causes silent routing failure" in content
        assert "exit 1" in content

    def test_root_config_remains_sanitized_contract(self):
        cfg = json.loads(ROOT_CONFIG.read_text(encoding="utf-8"))
        assert cfg["default_agent"] == "autocoder"
