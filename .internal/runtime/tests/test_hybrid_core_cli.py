"""Tests for Hybrid Core CLI runtime integration."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import hybrid_core_cli
import hybrid_core_validator
from profile_activator import ProfileActivator


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _event_stream(final_text: str) -> str:
    return "\n".join(
        [
            json.dumps(
                {
                    "type": "step_start",
                    "part": {"type": "step-start"},
                }
            ),
            json.dumps(
                {
                    "type": "text",
                    "part": {
                        "type": "text",
                        "text": final_text,
                        "metadata": {"openai": {"phase": "final_answer"}},
                    },
                }
            ),
            json.dumps(
                {
                    "type": "step_finish",
                    "part": {"type": "step-finish", "reason": "stop"},
                }
            ),
        ]
    )


def _valid_1x_payload() -> dict:
    return {
        "execution_profile": "default_1x",
        "scope_classification": "tier_1_universal",
        "summary": "Implemented the requested API change.",
        "code_changes": [
            {"file": "app.py", "action": "modify", "summary": "Added handler"}
        ],
        "compliance_notes": ["typing kept explicit"],
        "tests": ["pytest tests/test_app.py"],
        "risks": ["None"],
    }


@pytest.fixture
def disable_observability(monkeypatch):
    real_validator = hybrid_core_validator.HybridCoreValidator

    class NoObservabilityValidator(real_validator):
        def __init__(self):
            super().__init__(enable_observability=False)

    monkeypatch.setattr(
        hybrid_core_validator,
        "HybridCoreValidator",
        NoObservabilityValidator,
    )


class TestStructuredPrompt:
    def test_2x_prompt_contains_required_specialized_fields(self, monkeypatch):
        monkeypatch.setenv("OPENCODE_HYBRID_CORE", "enabled")
        profile = ProfileActivator().activate(
            "tier_2_algorithmic",
            "performance_2x",
        )

        prompt = hybrid_core_cli._build_structured_output_prompt(
            "Range minimum query with updates, n=200000",
            profile,
        )

        assert 'execution_profile must be "performance_2x"' in prompt
        assert 'scope_classification must be "tier_2_algorithmic"' in prompt
        assert "algorithm_selection_rationale" in prompt
        assert "complexity_certificate" in prompt
        assert "stress_test_plan" in prompt


class TestOutputParsing:
    def test_extract_final_text_prefers_final_answer_parts(self):
        stream = "\n".join(
            [
                json.dumps(
                    {
                        "type": "text",
                        "part": {"type": "text", "text": "draft"},
                    }
                ),
                json.dumps(
                    {
                        "type": "text",
                        "part": {
                            "type": "text",
                            "text": '{"summary": "final"}',
                            "metadata": {"openai": {"phase": "final_answer"}},
                        },
                    }
                ),
            ]
        )

        assert (
            hybrid_core_cli._extract_final_text_from_events(stream)
            == '{"summary": "final"}'
        )

    def test_extract_json_payload_accepts_fenced_json(self):
        payload = hybrid_core_cli._extract_json_payload(
            '```json\n{"summary": "ok"}\n```'
        )

        assert payload == {"summary": "ok"}


class TestRunAutocodeTask:
    def test_run_autocode_task_validates_final_payload(
        self,
        monkeypatch,
        disable_observability,
    ):
        monkeypatch.delenv("OPENCODE_HYBRID_CORE", raising=False)

        completed = subprocess.CompletedProcess(
            args=["opencode"],
            returncode=0,
            stdout=_event_stream(json.dumps(_valid_1x_payload())),
            stderr="",
        )

        def fake_run(*args, **kwargs):
            return completed

        monkeypatch.setattr(subprocess, "run", fake_run)

        exit_code, output = hybrid_core_cli.run_autocode_task(
            task="Create a REST API endpoint for user registration",
            project_root=REPO_ROOT,
        )

        assert exit_code == 0
        assert output["execution_profile"] == "default_1x"
        assert output["scope_classification"] == "tier_1_universal"
        assert output["hybrid_core_validation"]["passed"] is True
        assert output["gate_results"]["overall_status"] in {"pass", "warn"}
        assert any(
            item["kind"] == "scope_detection" for item in output["evidence_trail"]
        )

    def test_run_autocode_task_reports_parse_failures(self, monkeypatch):
        completed = subprocess.CompletedProcess(
            args=["opencode"],
            returncode=0,
            stdout=_event_stream("not-json"),
            stderr="",
        )

        def fake_run(*args, **kwargs):
            return completed

        monkeypatch.setattr(subprocess, "run", fake_run)

        exit_code, output = hybrid_core_cli.run_autocode_task(
            task="Create a REST API endpoint for user registration",
            project_root=REPO_ROOT,
        )

        assert exit_code == 1
        assert "Could not parse a JSON object" in output["error"]
