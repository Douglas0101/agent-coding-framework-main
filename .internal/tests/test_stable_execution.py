"""Public repository boundary tests."""

import subprocess
import sys
from pathlib import Path

INTERNAL_ROOT = Path(__file__).resolve().parent.parent
if str(INTERNAL_ROOT) not in sys.path:
    sys.path.insert(0, str(INTERNAL_ROOT))

from scripts.security_patterns import PRIVATE_REPOSITORY_ONLY_PHRASE

REPO_ROOT = INTERNAL_ROOT.parent


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

        tracked_internal = [line for line in result.stdout.splitlines() if line.strip()]
        assert not tracked_internal, (
            "Internal artifacts must not be published in Git history. "
            f"Found tracked paths: {tracked_internal}"
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

    def test_public_config_is_sanitized(self):
        config = (REPO_ROOT / "opencode.json").read_text(encoding="utf-8")
        assert PRIVATE_REPOSITORY_ONLY_PHRASE in config.lower()
