"""Allowlist governance tests for public repository exceptions."""

import datetime as dt
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ALLOWLIST = REPO_ROOT / ".github/security/public-repo-allowlist.json"
REQUIRED_FIELDS = {"pattern", "justification", "owner", "expires_on", "ticket_ref"}
REQUIRED_CATEGORIES = ("path_exceptions", "pattern_scan_exceptions")
OPTIONAL_CATEGORIES = ("tool_exceptions",)


class TestPublicRepoAllowlistGovernance:
    def test_required_categories_exist(self):
        cfg = json.loads(ALLOWLIST.read_text(encoding="utf-8"))
        for category in REQUIRED_CATEGORIES:
            assert category in cfg, f"Missing category: {category}"
            assert isinstance(cfg[category], list), f"{category} must be a list"

    def test_exceptions_include_required_metadata(self):
        cfg = json.loads(ALLOWLIST.read_text(encoding="utf-8"))
        for category in (*REQUIRED_CATEGORIES, *OPTIONAL_CATEGORIES):
            entries = cfg.get(category, [])
            assert isinstance(entries, list), f"{category} must be a list"
            for index, entry in enumerate(entries):
                assert isinstance(entry, dict), f"{category}[{index}] must be an object"
                missing = [
                    field
                    for field in REQUIRED_FIELDS
                    if not str(entry.get(field, "")).strip()
                ]
                assert not missing, (
                    f"{category}[{index}] missing fields: {', '.join(sorted(missing))}"
                )

    def test_exceptions_are_not_expired(self):
        cfg = json.loads(ALLOWLIST.read_text(encoding="utf-8"))
        today = dt.date.today()

        for category in (*REQUIRED_CATEGORIES, *OPTIONAL_CATEGORIES):
            for index, entry in enumerate(cfg.get(category, [])):
                expires_on = dt.date.fromisoformat(entry["expires_on"])
                assert expires_on >= today, (
                    f"{category}[{index}] expired on {expires_on.isoformat()} ({entry['pattern']})"
                )
