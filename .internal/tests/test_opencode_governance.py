"""Governance checks for the public `.opencode/` contract surface."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GITIGNORE = REPO_ROOT / ".gitignore"

# Sanitized allowlist - only these .opencode files are allowed in public repo
# This must match test_public_boundary.py ALLOWED_OPENCODE_FILES
REQUIRED_OPENCODE_FILES = (
    ".opencode/opencode.json",
    ".opencode/specs/README.md",
    ".opencode/specs/handoff-contract.sanitized.json",
    ".opencode/manifests/README.md",
    ".opencode/manifests/sanitized/run-manifest.example.json",
)

# Gitignore patterns for .opencode/ - deny all, allow specific sanitized files
REQUIRED_GITIGNORE_PATTERNS = (
    ".opencode/*",
    "!.opencode/opencode.json",
    "!.opencode/specs/README.md",
    "!.opencode/specs/*.sanitized.json",
    "!.opencode/manifests/README.md",
    "!.opencode/manifests/sanitized/*.json",
    ".opencode/node_modules/",
    ".opencode/memory/",
    ".opencode/evidence/",
    ".opencode/context/",
    ".opencode/tmp/",
    ".opencode/artifacts/",
    ".opencode/memory/",
)


class TestOpencodeGovernance:
    """Tests for .opencode/ public contract surface governance."""

    def test_required_public_contract_files_exist(self):
        """Verify all required sanitized .opencode files exist."""
        missing = [
            rel_path
            for rel_path in REQUIRED_OPENCODE_FILES
            if not (REPO_ROOT / rel_path).exists()
        ]
        assert not missing, (
            "Missing mandatory `.opencode/` governance files: " + ", ".join(missing)
        )

    def test_gitignore_has_public_exceptions_and_runtime_denies(self):
        """Verify .gitignore has proper patterns for .opencode/ boundary."""
        content = GITIGNORE.read_text(encoding="utf-8")
        for pattern in REQUIRED_GITIGNORE_PATTERNS:
            assert pattern in content, f"Missing `.gitignore` pattern: {pattern}"
