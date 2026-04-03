"""Shared security patterns for public-configuration sanitization checks."""

from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Public files that represent the supported sanitized configuration surface.
PUBLIC_CONFIG_FILES = (
    "opencode.json",
    ".opencode.example/opencode.json.example",
    ".codex.example/config.toml.example",
    ".agent.example/skills.example",
)

PUBLIC_DOC_FILES = (
    "README.md",
    ".opencode.example/README.md",
    ".codex.example/README.md",
    ".agent.example/README.md",
)

# Canonical "private repository only" wording used by tests/docs.
PRIVATE_REPOSITORY_ONLY_PHRASE = "private repository only"

# Explicit secret/token/private-key patterns that must never appear in public files.
PROHIBITED_SECRET_PATTERNS = (
    r"OPENAI_API_KEY\s*[:=]\s*['\"]?(?!\$\{?OPENAI_API_KEY_PLACEHOLDER\}?)([A-Za-z0-9_\-]{12,})",
    r"ANTHROPIC_API_KEY\s*[:=]\s*['\"]?(?!\$\{?ANTHROPIC_API_KEY_PLACEHOLDER\}?)([A-Za-z0-9_\-]{12,})",
    r"AWS_SECRET_ACCESS_KEY\s*[:=]\s*['\"]?([A-Za-z0-9/+=]{20,})",
    r"BEGIN (RSA|OPENSSH|EC) PRIVATE KEY",
    r"ghp_[A-Za-z0-9]{20,}",
    r"xox[baprs]-[A-Za-z0-9-]{10,}",
)

# Internal/private network endpoints that cannot be published in template/docs.
PROHIBITED_INTERNAL_ENDPOINT_PATTERNS = (
    r"https?://(?:localhost|127\.0\.0\.1)(?::\d+)?(?:/|$)",
    r"https?://(?:[a-zA-Z0-9-]+\.)?(?:corp|internal|intranet|local)(?::\d+)?(?:/|$)",
    r"\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
    r"\b192\.168\.\d{1,3}\.\d{1,3}\b",
)

# High-entropy candidate detector: long token-like string with broad charset mix.
HIGH_ENTROPY_CANDIDATE_PATTERN = r"\b[A-Za-z0-9+/=_-]{32,}\b"

# Safe placeholders that should appear wherever credentials are exemplified.
SAFE_PLACEHOLDER_PATTERNS = (
    r"OPENAI_API_KEY_PLACEHOLDER",
    r"ANTHROPIC_API_KEY_PLACEHOLDER",
    r"https://api\.example\.com",
)


def compile_patterns(patterns: tuple[str, ...]) -> list[re.Pattern[str]]:
    return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]


def high_entropy_candidate_has_mixed_charset(candidate: str) -> bool:
    has_upper = any(ch.isupper() for ch in candidate)
    has_lower = any(ch.islower() for ch in candidate)
    has_digit = any(ch.isdigit() for ch in candidate)
    has_symbol = any(ch in "+/=_-" for ch in candidate)
    return sum([has_upper, has_lower, has_digit, has_symbol]) >= 3
