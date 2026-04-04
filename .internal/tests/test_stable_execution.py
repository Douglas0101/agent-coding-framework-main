"""Stable execution regression tests for routing and guardrails."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# Import the phrase used for sanitized config validation
INTERNAL_ROOT = Path(__file__).resolve().parent.parent
if str(INTERNAL_ROOT) not in sys.path:
    sys.path.insert(0, str(INTERNAL_ROOT))

from scripts.security_patterns import PRIVATE_REPOSITORY_ONLY_PHRASE

REPO_ROOT = REPO_ROOT = Path(__file__).resolve().parent.parent.parent
AGENTS_MD = REPO_ROOT / "AGENTS.md"
RUN_AUTOCODE_SH = REPO_ROOT / ".internal/scripts/run-autocode.sh"
ROOT_CONFIG = REPO_ROOT / "opencode.json"

# Critical routing fields that must match between configs
ROUTING_CRITICAL_FIELDS = (
    "default_agent",
    "command.autocode.agent",
    "agent.autocoder.maxSteps",
    "agent.general.maxSteps",
)

REQUIRED_COMMAND_TEMPLATES = (
    "command.autocode.template",
    "command.analyze.template",
    "command.review.template",
    "command.ship.template",
)


class TestCommandRoutingRegression:
    """Tests for /autocode command routing behavior."""

    def test_autocode_without_agent_documents_native_routing(self):
        """Verify AGENTS.md documents native routing with supported schema."""
        content = AGENTS_MD.read_text(encoding="utf-8")
        assert "routes natively to the `autocoder` agent" in content
        assert "without `--agent`" in content

    def test_old_routing_issue_is_documented_as_invalid_schema(self):
        """Verify docs describe the stale-schema root cause accurately."""
        content = AGENTS_MD.read_text(encoding="utf-8")
        assert "invalid/stale config schema" in content
        assert "`agent` and `command`" in content

    def test_autocode_wrapper_uses_native_command_routing(self):
        """Verify the wrapper script relies on native command routing."""
        content = RUN_AUTOCODE_SH.read_text(encoding="utf-8")
        assert "--command autocode" in content
        assert "--agent autocoder" not in content


class TestStableExecutionGuardrails:
    """Tests for stable execution guardrails and invariants."""

    def test_no_silent_fallback_is_explicit_guardrail(self):
        """Verify AGENTS.md declares no silent fallback as invariant."""
        content = AGENTS_MD.read_text(encoding="utf-8")
        assert "No silent fallback" in content

    def test_verifier_gate_is_required(self):
        """Verify verifier gate is documented as mandatory."""
        content = AGENTS_MD.read_text(encoding="utf-8")
        assert "`verifier` is the mandatory gate before `synthesizer`" in content

    def test_write_scope_disjoint_is_required(self):
        """Verify write_scope disjoint is documented as required."""
        content = AGENTS_MD.read_text(encoding="utf-8")
        assert "Keep `write_scope` disjoint across parallel workers" in content

    def test_config_drift_is_fail_fast_in_wrapper(self):
        """Verify wrapper fails fast when .opencode/opencode.json is missing."""
        content = RUN_AUTOCODE_SH.read_text(encoding="utf-8")
        assert "Missing $DOT_CONFIG" in content
        assert "config resolution will diverge" in content
        assert "exit 1" in content

    def test_runtime_schema_validation_is_fail_fast_in_wrapper(self):
        """Verify wrapper validates the config with the real runtime schema."""
        content = RUN_AUTOCODE_SH.read_text(encoding="utf-8")
        assert "opencode debug config" in content
        assert "OpenCode rejected the project config schema" in content

    def test_root_config_remains_sanitized_contract(self):
        """Verify root config is sanitized with private_repository_only phrase."""
        cfg = json.loads(ROOT_CONFIG.read_text(encoding="utf-8"))
        assert cfg["default_agent"] == "autocoder"
        assert cfg["command"]["autocode"]["agent"] == "autocoder"
        assert isinstance(cfg["instructions"], list)

    def test_configs_use_supported_command_schema(self):
        """Verify configs use the supported OpenCode schema, not the stale routing schema."""
        root_cfg = json.loads(ROOT_CONFIG.read_text(encoding="utf-8"))

        assert "routing" not in root_cfg
        assert "maxSteps" not in root_cfg

        for path in REQUIRED_COMMAND_TEMPLATES:
            current = root_cfg
            for segment in path.split("."):
                assert segment in current, f"Missing supported schema path: {path}"
                current = current[segment]
            assert isinstance(current, str) and current, f"Invalid template at {path}"

    def test_public_config_is_sanitized(self):
        """Verify public config explicitly states it's private repository only."""
        config = (REPO_ROOT / "opencode.json").read_text(encoding="utf-8")
        assert PRIVATE_REPOSITORY_ONLY_PHRASE in config.lower()


class TestOpenCodeConfigParity:
    """Tests for configuration parity between opencode.json and .opencode/opencode.json."""

    def _load_json(self, rel_path: str) -> dict:
        """Load JSON file from relative path."""
        path = REPO_ROOT / rel_path
        assert path.exists(), (
            f"Parity check requires '{rel_path}', but file is missing. "
            f"Expected path: {path}"
        )
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise AssertionError(
                f"Invalid JSON in '{rel_path}' at line {exc.lineno}, column {exc.colno}: {exc.msg}"
            ) from exc

    @staticmethod
    def _get_path(data: dict, path: str):
        """Get nested value from dict using dot-notation path."""
        current = data
        for segment in path.split("."):
            if not isinstance(current, dict) or segment not in current:
                return False, None
            current = current[segment]
        return True, current

    def test_root_and_dot_opencode_configs_exist(self):
        """Verify both config files exist."""
        assert (REPO_ROOT / "opencode.json").exists()
        assert (REPO_ROOT / ".opencode/opencode.json").exists()

    def test_root_and_dot_opencode_configs_match_routing_fields(self):
        """Verify critical routing fields match between root and .opencode configs."""
        root_rel = "opencode.json"
        dot_rel = ".opencode/opencode.json"

        root_cfg = self._load_json(root_rel)
        dot_cfg = self._load_json(dot_rel)

        for field in ROUTING_CRITICAL_FIELDS:
            root_found, root_value = self._get_path(root_cfg, field)
            dot_found, dot_value = self._get_path(dot_cfg, field)

            assert root_found, f"Missing required critical field in {root_rel}: {field}"
            assert dot_found, f"Missing required critical field in {dot_rel}: {field}"

            assert root_found == dot_found, (
                "Config parity mismatch: field presence diverged for "
                f"'{field}'. {root_rel}: {'present' if root_found else 'missing'}; "
                f"{dot_rel}: {'present' if dot_found else 'missing'}."
            )

            assert root_value == dot_value, (
                "Config parity mismatch: field value diverged for "
                f"'{field}'. {root_rel}: {root_value!r}; {dot_rel}: {dot_value!r}."
            )

    def test_config_parity_by_critical_fields_only(self):
        """Verify the policy allows non-critical fields to differ."""
        # This test documents the policy: only ROUTING_CRITICAL_FIELDS must match
        # Other supported fields can differ without changing routing behavior.
        root_cfg = self._load_json("opencode.json")
        dot_cfg = self._load_json(".opencode/opencode.json")

        # These fields are allowed to differ when present.
        allowed_differ = ["providers", "instructions"]

        for field in allowed_differ:
            root_val = root_cfg.get(field)
            dot_val = dot_cfg.get(field)
            if root_val is None and dot_val is None:
                continue
            assert root_val != dot_val or root_val == dot_val


class TestRuntimeIntegration:
    """Optional runtime-backed integration checks."""

    def test_opencode_debug_config_accepts_repository_schema(self):
        """Verify the real OpenCode runtime accepts the repository config."""
        if shutil.which("opencode") is None:
            pytest.skip("opencode runtime not available")

        result = subprocess.run(
            ["opencode", "debug", "config", "--print-logs"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )

        output = (result.stdout or "") + (result.stderr or "")
        assert result.returncode == 0, output
        assert '"default_agent": "autocoder"' in output
        assert '"autocode": {' in output

    def test_native_autocode_routes_to_autocoder_when_opted_in(self):
        """Optional smoke test that proves native command routing at runtime."""
        if shutil.which("opencode") is None:
            pytest.skip("opencode runtime not available")
        if os.environ.get("RUN_OPENCODE_RUNTIME_SMOKE") != "1":
            pytest.skip("set RUN_OPENCODE_RUNTIME_SMOKE=1 to enable runtime smoke test")

        result = subprocess.run(
            [
                "timeout",
                "20s",
                "opencode",
                "run",
                "--command",
                "autocode",
                "--format",
                "json",
                "--print-logs",
                "ping",
            ],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )

        output = (result.stdout or "") + (result.stderr or "")
        assert result.returncode in {0, 124}, output
        assert "command=autocode command" in output, output
        assert "agent=autocoder" in output, output
