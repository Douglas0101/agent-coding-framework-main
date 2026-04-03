"""Stable execution regression tests for routing and guardrails."""

from __future__ import annotations

import json

"""Stable execution checks for routing-critical OpenCode configuration parity."""

import json
import subprocess
import sys
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

class TestPublicVsInternalBoundary:
    def test_internal_directories_not_tracked(self):
        internal_paths = (".agent", ".codex")
        try:
            result = subprocess.run(
                ["git", "ls-files", "--", *internal_paths],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise AssertionError(
                "Git is required for this test because the public boundary is "
                "defined by tracked files."
            ) from exc
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            raise AssertionError(
                "Unable to inspect tracked files with 'git ls-files'. "
                "Run tests from a valid Git checkout."
                + (f" stderr: {stderr}" if stderr else "")
            ) from exc

    def test_autocode_with_explicit_agent_is_documented_workaround(self):
        content = AGENTS_MD.read_text(encoding="utf-8")
        assert "opencode run --agent autocoder --command autocode" in content

    def test_autocode_wrapper_enforces_supported_path(self):
        content = RUN_AUTOCODE_SH.read_text(encoding="utf-8")
        assert "--agent autocoder" in content
        assert "--command autocode" in content
ROUTING_CRITICAL_FIELDS = (
    "default_agent",
    "maxSteps",
    "routing.commands.autocode",
    "routing.agents.autocoder.maxSteps",
)

        tracked_files = subprocess.check_output(
            ["git", "ls-files"],
            cwd=REPO_ROOT,
            text=True,
        ).splitlines()
        for path in (".agent/", ".codex/"):
            assert not any(file_path.startswith(path) for file_path in tracked_files), (
                f"{path} must stay out of public repo"
            )

        allowed_opencode_files = {
            ".opencode/opencode.json",
            ".opencode/specs/README.md",
            ".opencode/specs/handoff-contract.sanitized.json",
            ".opencode/manifests/README.md",
            ".opencode/manifests/sanitized/run-manifest.example.json",
        }
        tracked_opencode_files = [
            file_path for file_path in tracked_files if file_path.startswith(".opencode/")
        ]
        disallowed_opencode_files = sorted(
            set(tracked_opencode_files) - allowed_opencode_files
        )
        assert not disallowed_opencode_files, (
            "Only sanitized .opencode contract files are allowed in public repo. "
            f"Found: {disallowed_opencode_files}"
        )

    def test_sanitized_templates_exist(self):
        required = [
            ".agent.example/README.md",
            ".codex.example/README.md",
            ".opencode.example/README.md",
            ".codex.example/config.toml.example",
            ".opencode.example/opencode.json.example",
        ]
        for rel in required:
            assert (REPO_ROOT / rel).exists(), f"Missing sanitized template: {rel}"

    def test_readme_has_public_vs_internal_section(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        assert "Public vs Internal Artifacts" in readme


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
    def test_public_config_is_sanitized(self):
        config = (REPO_ROOT / "opencode.json").read_text(encoding="utf-8")
        assert PRIVATE_REPOSITORY_ONLY_PHRASE in config.lower()


class TestOpenCodeConfigParity:
    def _load_json(self, rel_path: str):
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
        current = data
        for segment in path.split("."):
            if not isinstance(current, dict) or segment not in current:
                return False, None
            current = current[segment]
        return True, current

    def test_root_and_dot_opencode_configs_match_routing_fields(self):
        root_rel = "opencode.json"
        dot_rel = ".opencode/opencode.json"

        root_cfg = self._load_json(root_rel)
        dot_cfg = self._load_json(dot_rel)

        for field in ROUTING_CRITICAL_FIELDS:
            root_found, root_value = self._get_path(root_cfg, field)
            dot_found, dot_value = self._get_path(dot_cfg, field)

            assert root_found == dot_found, (
                "Config parity mismatch: field presence diverged for "
                f"'{field}'. {root_rel}: {'present' if root_found else 'missing'}; "
                f"{dot_rel}: {'present' if dot_found else 'missing'}."
            )

            assert root_value == dot_value, (
                "Config parity mismatch: field value diverged for "
                f"'{field}'. {root_rel}: {root_value!r}; {dot_rel}: {dot_value!r}."
            )
