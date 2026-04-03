#!/usr/bin/env python3
"""Scan tracked text files for sensitive operational patterns.

This script is shared between CI and local pre-commit hooks to prevent policy drift.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import pathlib
import re
import subprocess
import sys
from typing import Iterable

TEXT_EXTENSIONS = {
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".py",
    ".sh",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".java",
    ".go",
    ".rb",
    ".rs",
    ".env",
    ".properties",
    ".xml",
}

SKIP_DIRS = {".git", "node_modules", "dist", "build", ".venv"}
SKIP_FILENAMES = {".env", ".env.example"}

PATTERNS = {
    "possible_token_assignment": re.compile(
        r"(?i)\b(token|api[_-]?key|secret|client[_-]?secret)\b\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{16,}[\"']?"
    ),
    "aws_access_key_id": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github_pat_or_classic_token": re.compile(r"\b(ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    "private_key_material": re.compile(r"-----BEGIN (RSA|EC|DSA|OPENSSH|PRIVATE) KEY-----"),
    "internal_endpoint": re.compile(
        r"https?://[^\s\"']+(\.internal\b|\.corp\b|\.local\b|\b10\.|\b192\.168\.|\b172\.(1[6-9]|2[0-9]|3[0-1])\.)"
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan files for sensitive operational patterns.")
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional list of files to scan. If omitted, scans git-tracked files.",
    )
    return parser.parse_args()


def load_scan_exceptions() -> list[str]:
    allowlist_path = pathlib.Path(".github/security/public-repo-allowlist.json")
    if not allowlist_path.exists():
        return []

    payload = json.loads(allowlist_path.read_text(encoding="utf-8"))
    return [item["pattern"] for item in payload.get("pattern_scan_exceptions", [])]


def tracked_files() -> list[str]:
    output = subprocess.check_output(["git", "ls-files"], text=True)
    return output.splitlines()


def should_scan(path: pathlib.Path) -> bool:
    if any(part in SKIP_DIRS for part in path.parts):
        return False
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return True
    return path.name in SKIP_FILENAMES


def iter_candidate_files(cli_paths: list[str]) -> Iterable[pathlib.Path]:
    raw_paths = cli_paths or tracked_files()
    for value in raw_paths:
        path = pathlib.Path(value)
        if path.exists() and path.is_file() and should_scan(path):
            yield path


def main() -> int:
    args = parse_args()
    scan_exceptions = load_scan_exceptions()

    findings: list[tuple[str, str, str]] = []

    for path in iter_candidate_files(args.paths):
        relative = path.as_posix()

        if any(fnmatch.fnmatch(relative, pattern) for pattern in scan_exceptions):
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        if "example" in path.name.lower() or "sample" in path.name.lower():
            continue

        for name, regex in PATTERNS.items():
            for match in regex.finditer(content):
                snippet = match.group(0).strip().replace("\n", " ")
                findings.append((relative, name, snippet[:120]))

    if findings:
        print("Sensitive operational configuration patterns detected:")
        for rel_path, kind, snippet in findings[:200]:
            print(f" - {rel_path} :: {kind} :: {snippet}")
        print("\nIf this is intentional, sanitize the value or add a reviewed exception to the allowlist.")
        return 1

    print("Sensitive operational configuration scan passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
