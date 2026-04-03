"""Public repository boundary tests with sanitized .opencode allowlist."""

import subprocess
import sys
from pathlib import Path

INTERNAL_ROOT = Path(__file__).resolve().parent.parent
if str(INTERNAL_ROOT) not in sys.path:
    sys.path.insert(0, str(INTERNAL_ROOT))

from scripts.security_patterns import PRIVATE_REPOSITORY_ONLY_PHRASE

REPO_ROOT = INTERNAL_ROOT.parent

# Sanitized allowlist for .opencode/ - only these files are allowed in public repo
# This matches test_opencode_governance.py and .gitignore
ALLOWED_OPENCODE_FILES = {
    ".opencode/opencode.json",
    ".opencode/specs/README.md",
    ".opencode/specs/handoff-contract.sanitized.json",
    ".opencode/manifests/README.md",
    ".opencode/manifests/sanitized/run-manifest.example.json",
}


class TestPublicVsInternalBoundary:
    """Tests for public vs internal artifact boundary."""

    def test_internal_directories_not_tracked(self):
        """Verify .agent and .codex are not tracked in public repo."""
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

    def test_opencode_public_surface_follows_allowlist(self):
        """Verify only sanitized .opencode files are tracked."""
        tracked_files = subprocess.check_output(
            ["git", "ls-files"],
            cwd=REPO_ROOT,
            text=True,
        ).splitlines()

        # Get all .opencode tracked files
        tracked_opencode = [f for f in tracked_files if f.startswith(".opencode/")]

        # Check against allowlist
        disallowed = []
        for f in tracked_opencode:
            # Check if it matches any allowed pattern
            allowed = False
            for allowed_pattern in ALLOWED_OPENCODE_FILES:
                if f == allowed_pattern or f.startswith(
                    allowed_pattern.rstrip("/") + "/"
                ):
                    allowed = True
                    break
            if not allowed:
                disallowed.append(f)

        assert not disallowed, (
            f"Only sanitized .opencode allowlist files allowed in public repo. "
            f"Found disallowed: {disallowed}"
        )

    def test_sanitized_templates_exist(self):
        """Verify sanitized template files exist."""
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
        """Verify README documents public vs internal boundary."""
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        assert "Public vs Internal Artifacts" in readme

    def test_public_config_is_sanitized(self):
        """Verify public config explicitly states private repository only."""
        config = (REPO_ROOT / "opencode.json").read_text(encoding="utf-8")
        assert PRIVATE_REPOSITORY_ONLY_PHRASE in config.lower()
