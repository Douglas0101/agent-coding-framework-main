"""Public repository boundary tests."""

import subprocess
from pathlib import Path

from scripts.security_patterns import PRIVATE_REPOSITORY_ONLY_PHRASE

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestPublicVsInternalBoundary:
    def test_internal_directories_not_tracked(self):
        tracked_files = subprocess.check_output(
            ["git", "ls-files"],
            cwd=REPO_ROOT,
            text=True,
        ).splitlines()
        for path in (".agent/", ".codex/", ".opencode/"):
            assert not any(file_path.startswith(path) for file_path in tracked_files), (
                f"{path} must stay out of public repo"
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

    def test_public_config_is_sanitized(self):
        config = (REPO_ROOT / "opencode.json").read_text(encoding="utf-8")
        assert PRIVATE_REPOSITORY_ONLY_PHRASE in config.lower()
