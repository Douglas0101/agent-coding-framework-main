"""
Skill: boundary_leak_detector (reviewer mode)

Detects boundary leaks between public (docs/) and internal (.internal/) surfaces,
identifies sensitive data exposure, config leakage, and architectural boundary violations.
"""

from __future__ import annotations

import json
import hashlib
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INTERNAL_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = INTERNAL_DIR.parent


@dataclass
class BoundaryLeak:
    leak_id: str
    severity: str  # critical, high, medium, low
    category: str  # internal_reference, secret_exposure, config_leak, arch_violation
    file_path: str
    line_number: int
    description: str
    evidence: str = ""
    remediation: str = ""


@dataclass
class BoundaryLeakReport:
    run_id: str
    timestamp: str
    files_scanned: int = 0
    leaks: list[BoundaryLeak] = field(default_factory=list)
    categories: dict[str, int] = field(default_factory=dict)
    integrity_hash: str = ""

    @property
    def has_leaks(self) -> bool:
        return len(self.leaks) > 0

    @property
    def has_critical_leaks(self) -> bool:
        return any(l.severity == "critical" for l in self.leaks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "files_scanned": self.files_scanned,
            "has_leaks": self.has_leaks,
            "has_critical_leaks": self.has_critical_leaks,
            "total_leaks": len(self.leaks),
            "categories": self.categories,
            "leaks": [asdict(l) for l in self.leaks],
            "integrity_hash": self.integrity_hash,
        }


class BoundaryLeakDetector:
    """Detects boundary leaks between public and internal surfaces."""

    INTERNAL_REF_PATTERNS = [
        re.compile(r"\.internal/"),
        re.compile(r"\.internal\\"),
        re.compile(r"from\s+\._?internal"),
        re.compile(r"import\s+\._?internal"),
        re.compile(r"\.internal\\."),
    ]

    SECRET_PATTERNS = [
        (
            re.compile(r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"][A-Za-z0-9]{16,}['\"]"),
            "API key exposure",
        ),
        (
            re.compile(
                r"(?i)(secret[_-]?key|secret)\s*[:=]\s*['\"][A-Za-z0-9]{16,}['\"]"
            ),
            "Secret key exposure",
        ),
        (
            re.compile(r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
            "Password exposure",
        ),
        (
            re.compile(r"(?i)(token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}['\"]"),
            "Token exposure",
        ),
        (
            re.compile(r"(?i)(aws[_-]?access[_-]?key[_-]?id)\s*[:=]\s*['\"]AKIA"),
            "AWS key exposure",
        ),
    ]

    CONFIG_LEAK_PATTERNS = [
        (
            re.compile(
                r"(?i)(provider[_-]?key|openai[_-]?key|anthropic[_-]?key)\s*[:=]"
            ),
            "Provider key in public file",
        ),
        (
            re.compile(
                r"(?i)(database[_-]?url|db[_-]?url|connection[_-]?string)\s*[:=]\s*['\"]"
            ),
            "Connection string exposure",
        ),
        (
            re.compile(r"(?i)(private[_-]?key|ssh[_-]?key)\s*[:=]\s*['\"]"),
            "Private key reference",
        ),
    ]

    ARCH_VIOLATION_PATTERNS = [
        (
            re.compile(r"from\s+\..*\s+import\s+"),
            "Relative import from internal module",
        ),
        (re.compile(r"__all__\s*="), "Module exports may expose internal details"),
    ]

    PUBLIC_DIRS = [
        "docs/",
        "README.md",
        "LICENSE",
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
    ]

    def __init__(self, run_id: str | None = None, root: Path | None = None) -> None:
        self.run_id = (
            run_id or f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        )
        self.root = root or PROJECT_ROOT
        self._leaks: list[BoundaryLeak] = []
        self._leak_counter = 0
        self._files_scanned = 0

    def scan(self) -> BoundaryLeakReport:
        self._scan_public_files()
        self._scan_gitignore()
        self._scan_configs()

        categories: dict[str, int] = {}
        for leak in self._leaks:
            categories[leak.category] = categories.get(leak.category, 0) + 1

        report = BoundaryLeakReport(
            run_id=self.run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            files_scanned=self._files_scanned,
            leaks=self._leaks,
            categories=categories,
        )
        report.integrity_hash = self._compute_hash(report)
        return report

    def _scan_public_files(self) -> None:
        for pattern in ["*.md", "*.txt", "*.rst", "*.py", "*.yaml", "*.yml", "*.json"]:
            for pub_dir in ["docs"]:
                pub_path = self.root / pub_dir
                if not pub_path.exists():
                    continue
                for file_path in pub_path.rglob(pattern):
                    self._scan_file_for_leaks(str(file_path))

        for pub_file in ["README.md"]:
            fpath = self.root / pub_file
            if fpath.exists():
                self._scan_file_for_leaks(str(fpath))

    def _scan_gitignore(self) -> None:
        gitignore = self.root / ".gitignore"
        if not gitignore.exists():
            self._add_leak(
                severity="critical",
                category="config_leak",
                file_path=".gitignore",
                line_number=0,
                description=".gitignore not found - all files may be tracked",
                remediation="Create .gitignore with appropriate exclusions",
            )
            return

        self._files_scanned += 1
        content = gitignore.read_text(encoding="utf-8", errors="replace")

        if ".internal/" not in content and ".env" not in content:
            self._add_leak(
                severity="high",
                category="config_leak",
                file_path=".gitignore",
                line_number=0,
                description=".gitignore may not exclude .internal/ or .env files",
                remediation="Add .internal/ and .env to .gitignore",
            )

    def _scan_configs(self) -> None:
        config_files = ["opencode.json", ".opencode/opencode.json", "pyproject.toml"]
        for config_file in config_files:
            fpath = self.root / config_file
            if fpath.exists():
                self._scan_file_for_leaks(str(fpath), is_config=True)

    def _scan_file_for_leaks(self, file_path: str, is_config: bool = False) -> None:
        self._files_scanned += 1
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="replace")
        except (PermissionError, UnicodeDecodeError):
            return

        rel_path = str(Path(file_path).relative_to(self.root))

        for line_num, line in enumerate(content.splitlines(), 1):
            self._check_internal_refs(rel_path, line_num, line)
            self._check_secrets(rel_path, line_num, line)
            if is_config:
                self._check_config_leaks(rel_path, line_num, line)
            self._check_arch_violations(rel_path, line_num, line)

    def _check_internal_refs(self, file_path: str, line_num: int, line: str) -> None:
        for pattern in self.INTERNAL_REF_PATTERNS:
            match = pattern.search(line)
            if match:
                self._add_leak(
                    severity="high",
                    category="internal_reference",
                    file_path=file_path,
                    line_number=line_num,
                    description=f"Internal reference in public file: {match.group()}",
                    evidence=line.strip()[:100],
                    remediation="Remove or redact internal path references",
                )

    def _check_secrets(self, file_path: str, line_num: int, line: str) -> None:
        for pattern, description in self.SECRET_PATTERNS:
            match = pattern.search(line)
            if match:
                self._add_leak(
                    severity="critical",
                    category="secret_exposure",
                    file_path=file_path,
                    line_number=line_num,
                    description=description,
                    evidence=line.strip()[:100],
                    remediation="Use environment variables or secrets manager",
                )

    def _check_config_leaks(self, file_path: str, line_num: int, line: str) -> None:
        for pattern, description in self.CONFIG_LEAK_PATTERNS:
            match = pattern.search(line)
            if match:
                self._add_leak(
                    severity="high",
                    category="config_leak",
                    file_path=file_path,
                    line_number=line_num,
                    description=description,
                    evidence=line.strip()[:100],
                    remediation="Use placeholders or environment variables",
                )

    def _check_arch_violations(self, file_path: str, line_num: int, line: str) -> None:
        for pattern, description in self.ARCH_VIOLATION_PATTERNS:
            match = pattern.search(line)
            if match:
                self._add_leak(
                    severity="medium",
                    category="arch_violation",
                    file_path=file_path,
                    line_number=line_num,
                    description=description,
                    evidence=line.strip()[:100],
                    remediation="Review module boundaries and exports",
                )

    def _add_leak(
        self,
        severity: str,
        category: str,
        file_path: str,
        line_number: int,
        description: str,
        evidence: str = "",
        remediation: str = "",
    ) -> None:
        self._leak_counter += 1
        self._leaks.append(
            BoundaryLeak(
                leak_id=f"leak-{self._leak_counter:04d}",
                severity=severity,
                category=category,
                file_path=file_path,
                line_number=line_number,
                description=description,
                evidence=evidence,
                remediation=remediation,
            )
        )

    def _compute_hash(self, report: BoundaryLeakReport) -> str:
        content = json.dumps(
            {
                "run_id": report.run_id,
                "files_scanned": report.files_scanned,
                "leak_count": len(report.leaks),
                "categories": report.categories,
            },
            sort_keys=True,
            default=str,
        )
        return f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"


def detect_boundary_leaks(
    run_id: str | None = None, root: str | None = None
) -> dict[str, Any]:
    detector = BoundaryLeakDetector(run_id=run_id, root=Path(root) if root else None)
    report = detector.scan()
    return report.to_dict()


if __name__ == "__main__":
    import sys

    run_id = sys.argv[1] if len(sys.argv) > 1 else None
    result = detect_boundary_leaks(run_id=run_id)

    status = "LEAKS FOUND" if result["has_leaks"] else "CLEAN"
    if result["has_critical_leaks"]:
        status = "CRITICAL LEAKS"

    print(f"[{status}] Boundary leak detector: {result['run_id']}")
    print(f"  Files scanned: {result['files_scanned']}")
    print(f"  Total leaks: {result['total_leaks']}")

    for cat, count in result["categories"].items():
        print(f"    {cat}: {count}")

    for leak in result["leaks"]:
        print(
            f"  [{leak['severity'].upper()}] {leak['category']}: {leak['description']}"
        )
        print(f"    {leak['file_path']}:{leak['line_number']}")
