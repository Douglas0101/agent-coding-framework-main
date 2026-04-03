"""Governance checks for the public `.opencode/` contract surface."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GITIGNORE = REPO_ROOT / ".gitignore"

REQUIRED_OPENCODE_FILES = (
    ".opencode/opencode.json",
    ".opencode/specs/README.md",
    ".opencode/specs/handoff-contract.sanitized.json",
    ".opencode/manifests/README.md",
    ".opencode/manifests/sanitized/run-manifest.example.json",
)

REQUIRED_GITIGNORE_PATTERNS = (
    ".opencode/*",
    "!.opencode/opencode.json",
    "!.opencode/specs/",
    "!.opencode/manifests/sanitized/*.json",
    ".opencode/node_modules/",
    ".opencode/memory/",
)


class TestOpencodeGovernance:
    def test_required_public_contract_files_exist(self):
        missing = [
            rel_path for rel_path in REQUIRED_OPENCODE_FILES if not (REPO_ROOT / rel_path).exists()
        ]
        assert not missing, (
            "Missing mandatory `.opencode/` governance files: "
            + ", ".join(missing)
        )

    def test_gitignore_has_public_exceptions_and_runtime_denies(self):
        content = GITIGNORE.read_text(encoding="utf-8")
        for pattern in REQUIRED_GITIGNORE_PATTERNS:
            assert pattern in content, f"Missing `.gitignore` pattern: {pattern}"
