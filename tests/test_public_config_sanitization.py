"""Contract tests for sanitized public configuration files."""

from __future__ import annotations

import re

from scripts.security_patterns import (
    HIGH_ENTROPY_CANDIDATE_PATTERN,
    PRIVATE_REPOSITORY_ONLY_PHRASE,
    PROHIBITED_INTERNAL_ENDPOINT_PATTERNS,
    PROHIBITED_SECRET_PATTERNS,
    PUBLIC_CONFIG_FILES,
    PUBLIC_DOC_FILES,
    REPO_ROOT,
    SAFE_PLACEHOLDER_PATTERNS,
    compile_patterns,
    high_entropy_candidate_has_mixed_charset,
)


class TestSanitizedPublicConfigurationContract:
    def test_inventory_files_exist(self):
        for rel_path in (*PUBLIC_CONFIG_FILES, *PUBLIC_DOC_FILES):
            assert (REPO_ROOT / rel_path).exists(), f"Missing public contract file: {rel_path}"

    def test_no_prohibited_secret_or_internal_endpoint_patterns(self):
        prohibited_patterns = compile_patterns(
            PROHIBITED_SECRET_PATTERNS + PROHIBITED_INTERNAL_ENDPOINT_PATTERNS
        )
        for rel_path in (*PUBLIC_CONFIG_FILES, *PUBLIC_DOC_FILES):
            content = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
            for pattern in prohibited_patterns:
                assert pattern.search(content) is None, (
                    f"Disallowed pattern {pattern.pattern!r} detected in {rel_path}"
                )

    def test_no_high_entropy_values_in_public_contract_files(self):
        token_pattern = re.compile(HIGH_ENTROPY_CANDIDATE_PATTERN)
        for rel_path in (*PUBLIC_CONFIG_FILES, *PUBLIC_DOC_FILES):
            content = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
            for candidate in token_pattern.findall(content):
                if "PLACEHOLDER" in candidate:
                    continue
                assert not high_entropy_candidate_has_mixed_charset(candidate), (
                    f"High-entropy candidate found in {rel_path}: {candidate}"
                )

    def test_safe_placeholders_are_present_in_templates(self):
        required_placeholders_by_file = {
            ".opencode.example/opencode.json.example": (
                "OPENAI_API_KEY_PLACEHOLDER",
                "ANTHROPIC_API_KEY_PLACEHOLDER",
                "https://api.example.com/v1",
            ),
            ".codex.example/config.toml.example": (
                "OPENAI_API_KEY_PLACEHOLDER",
                "https://api.example.com/v1",
            ),
        }
        for rel_path, placeholders in required_placeholders_by_file.items():
            content = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
            for placeholder in placeholders:
                assert placeholder in content, f"Missing safe placeholder {placeholder} in {rel_path}"

        # Keep canonical placeholder regexes actively consumed by tests.
        compiled_safe_placeholders = compile_patterns(SAFE_PLACEHOLDER_PATTERNS)
        merged_template_content = "\n".join(
            (REPO_ROOT / rel_path).read_text(encoding="utf-8")
            for rel_path in required_placeholders_by_file
        )
        for safe_pattern in compiled_safe_placeholders:
            assert safe_pattern.search(merged_template_content), (
                f"Safe placeholder regex has no match: {safe_pattern.pattern}"
            )

    def test_private_repository_only_language_is_explicit(self):
        required_phrase_files = (
            "README.md",
            "opencode.json",
            ".opencode.example/README.md",
            ".codex.example/README.md",
            ".agent.example/README.md",
            ".opencode.example/opencode.json.example",
            ".codex.example/config.toml.example",
        )
        expected_phrase = PRIVATE_REPOSITORY_ONLY_PHRASE.lower()
        for rel_path in required_phrase_files:
            content = (REPO_ROOT / rel_path).read_text(encoding="utf-8").lower()
            assert expected_phrase in content, (
                f"Missing explicit '{PRIVATE_REPOSITORY_ONLY_PHRASE}' language in {rel_path}"
            )
