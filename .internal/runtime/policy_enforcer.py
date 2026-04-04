"""
Policy Enforcer — Runtime security and compliance enforcement.

Scans file contents and code changes against security patterns,
OWASP checks, forbidden patterns, and credential leakage detection.
"""

from __future__ import annotations

import re
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INTERNAL_DIR = Path(__file__).resolve().parent.parent


@dataclass
class PolicyFinding:
    rule_id: str
    severity: str  # critical, high, medium, low, info
    category: str  # secret, pattern, owasp, policy
    message: str
    file_path: str
    line_number: int = 0
    matched_text: str = ""
    remediation: str = ""


@dataclass
class PolicyReport:
    run_id: str
    timestamp: str
    files_scanned: int = 0
    findings: list[PolicyFinding] = field(default_factory=list)
    integrity_hash: str = ""

    @property
    def passed(self) -> bool:
        return not any(f.severity in ("critical", "high") for f in self.findings)

    @property
    def secrets_found(self) -> int:
        return sum(1 for f in self.findings if f.category == "secret")

    @property
    def policy_violations(self) -> int:
        return sum(1 for f in self.findings if f.category == "policy")

    @property
    def risk_score(self) -> float:
        if not self.findings:
            return 0.0
        weights = {"critical": 1.0, "high": 0.7, "medium": 0.4, "low": 0.1, "info": 0.0}
        total = sum(weights.get(f.severity, 0) for f in self.findings)
        return min(total / max(len(self.findings), 1), 1.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "files_scanned": self.files_scanned,
            "passed": self.passed,
            "secrets_found": self.secrets_found,
            "policy_violations": self.policy_violations,
            "risk_score": round(self.risk_score, 3),
            "findings": [asdict(f) for f in self.findings],
            "integrity_hash": self.integrity_hash,
        }


# Security patterns
SECRET_PATTERNS = [
    (
        "SEC-001",
        r"(?i)(api[_-]?key|apikey)\s*[=:]\s*['\"][A-Za-z0-9_\-]{16,}['\"]",
        "API key detected",
    ),
    (
        "SEC-002",
        r"(?i)(secret[_-]?key|secret)\s*[=:]\s*['\"][A-Za-z0-9_\-]{16,}['\"]",
        "Secret key detected",
    ),
    (
        "SEC-003",
        r"(?i)(password|passwd|pwd)\s*[=:]\s*['\"][^\s'\"]{8,}['\"]",
        "Password detected",
    ),
    (
        "SEC-004",
        r"(?i)(token|auth[_-]?token|access[_-]?token)\s*[=:]\s*['\"][A-Za-z0-9_\-\.]{20,}['\"]",
        "Token detected",
    ),
    (
        "SEC-005",
        r"(?i)(aws[_-]?access[_-]?key[_-]?id)\s*[=:]\s*['\"]AKIA[A-Za-z0-9]{16}['\"]",
        "AWS access key detected",
    ),
    (
        "SEC-006",
        r"(?i)(private[_-]?key)\s*[=:]\s*['\"]-----BEGIN",
        "Private key detected",
    ),
    (
        "SEC-007",
        r"(?i)(connection[_-]?string|conn[_-]?str)\s*[=:]\s*['\"][^\s'\"]{20,}['\"]",
        "Connection string detected",
    ),
    (
        "SEC-008",
        r"(?i)(github[_-]?token|ghp_|gho_|ghu_)[A-Za-z0-9]{20,}",
        "GitHub token detected",
    ),
]

FORBIDDEN_PATTERNS = [
    ("POL-001", r"(?i)(eval|exec)\s*\(", "Use of eval/exec detected"),
    ("POL-002", r"(?i)os\.system\s*\(", "Use of os.system detected"),
    (
        "POL-003",
        r"(?i)subprocess\.(call|run|Popen).*shell\s*=\s*True",
        "Shell injection risk in subprocess",
    ),
    ("POL-004", r"(?i)__import__\s*\(", "Dynamic import detected"),
    ("POL-005", r"(?i)pickle\.loads?\s*\(", "Unsafe pickle usage"),
    ("POL-006", r"(?i)yaml\.load\s*\([^)]*\)", "Unsafe yaml.load (use yaml.safe_load)"),
]

OWASP_PATTERNS = [
    (
        "OWASP-001",
        r"(?i)(?:select|insert|update|delete)\b.*\+|\+.*\b(?:from|where|set|into|values)\b",
        "Potential SQL injection",
    ),
    ("OWASP-002", r"(?i)<script[^>]*>.*</script>", "Potential XSS via script tag"),
    ("OWASP-003", r"(?i)javascript\s*:", "Potential XSS via javascript: URI"),
    (
        "OWASP-004",
        r"(?i)on(load|error|click|mouseover)\s*=",
        "Potential XSS via event handler",
    ),
]


class PolicyEnforcer:
    """Enforces security and compliance policies on file contents."""

    def __init__(self, run_id: str | None = None) -> None:
        self.run_id = (
            run_id or f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        )

    def scan_file(self, file_path: str | Path) -> PolicyReport:
        path = Path(file_path)
        if not path.exists():
            return PolicyReport(
                run_id=self.run_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                findings=[
                    PolicyFinding(
                        rule_id="POL-ERR",
                        severity="high",
                        category="policy",
                        message=f"File not found: {file_path}",
                        file_path=str(file_path),
                    )
                ],
            )

        content = path.read_text(encoding="utf-8", errors="replace")
        return self.scan_content(content, str(path))

    def scan_content(self, content: str, file_path: str = "<unknown>") -> PolicyReport:
        findings: list[PolicyFinding] = []

        all_patterns = [
            (SECRET_PATTERNS, "secret"),
            (FORBIDDEN_PATTERNS, "policy"),
            (OWASP_PATTERNS, "owasp"),
        ]

        for patterns, category in all_patterns:
            for rule_id, pattern, message in patterns:
                for line_num, line in enumerate(content.splitlines(), start=1):
                    if re.search(pattern, line):
                        findings.append(
                            PolicyFinding(
                                rule_id=rule_id,
                                severity=self._severity_for_category(category),
                                category=category,
                                message=message,
                                file_path=file_path,
                                line_number=line_num,
                                matched_text=line.strip()[:200],
                                remediation=self._remediation_for_rule(rule_id),
                            )
                        )

        report = PolicyReport(
            run_id=self.run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            files_scanned=1,
            findings=findings,
        )
        report.integrity_hash = self._compute_hash(content)
        return report

    def scan_directory(
        self,
        directory: str | Path,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> PolicyReport:
        dir_path = Path(directory)
        if not dir_path.is_dir():
            return PolicyReport(
                run_id=self.run_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                findings=[
                    PolicyFinding(
                        rule_id="POL-ERR",
                        severity="high",
                        category="policy",
                        message=f"Directory not found: {directory}",
                        file_path=str(directory),
                    )
                ],
            )

        if include_patterns is None:
            include_patterns = [
                "*.py",
                "*.yaml",
                "*.yml",
                "*.json",
                "*.js",
                "*.ts",
                "*.sh",
            ]
        if exclude_patterns is None:
            exclude_patterns = [
                "*.pyc",
                "__pycache__/*",
                ".git/*",
                "node_modules/*",
                "*.lock",
            ]

        all_findings: list[PolicyFinding] = []
        files_scanned = 0

        for pattern in include_patterns:
            for file_path in dir_path.rglob(pattern):
                if self._should_exclude(file_path, exclude_patterns):
                    continue
                try:
                    report = self.scan_file(file_path)
                    all_findings.extend(report.findings)
                    files_scanned += 1
                except (UnicodeDecodeError, PermissionError):
                    continue

        report = PolicyReport(
            run_id=self.run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            files_scanned=files_scanned,
            findings=all_findings,
        )
        combined = "".join(
            f"{f.rule_id}:{f.file_path}:{f.line_number}" for f in all_findings
        )
        report.integrity_hash = (
            f"sha256:{hashlib.sha256(combined.encode()).hexdigest()}"
        )
        return report

    def _severity_for_category(self, category: str) -> str:
        return {"secret": "critical", "policy": "high", "owasp": "high"}.get(
            category, "medium"
        )

    def _remediation_for_rule(self, rule_id: str) -> str:
        remediations = {
            "SEC-001": "Use environment variables or a secrets manager for API keys",
            "SEC-002": "Use environment variables or a secrets manager for secret keys",
            "SEC-003": "Use environment variables or a secrets manager for passwords",
            "SEC-004": "Use environment variables or a secrets manager for tokens",
            "SEC-005": "Use IAM roles or environment variables for AWS credentials",
            "SEC-006": "Store private keys in a secure key management system",
            "SEC-007": "Use environment variables or a secrets manager for connection strings",
            "SEC-008": "Use GitHub Apps or environment variables for tokens",
            "POL-001": "Avoid eval/exec; use safer alternatives like ast.literal_eval",
            "POL-002": "Use subprocess.run with a list of arguments instead",
            "POL-003": "Avoid shell=True; use a list of arguments",
            "POL-004": "Use importlib.import_module instead",
            "POL-005": "Use json or a safer serialization format",
            "POL-006": "Use yaml.safe_load instead",
            "OWASP-001": "Use parameterized queries or an ORM",
            "OWASP-002": "Sanitize and escape user input before rendering",
            "OWASP-003": "Sanitize URIs and use allowlists for protocols",
            "OWASP-004": "Sanitize user input and use CSP headers",
        }
        return remediations.get(rule_id, "Review and remediate the finding")

    def _should_exclude(self, file_path: Path, exclude_patterns: list[str]) -> bool:
        path_str = str(file_path)
        for pattern in exclude_patterns:
            if Path(file_path).match(pattern):
                return True
        return False

    def _compute_hash(self, content: str) -> str:
        return f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"


def scan_directory(directory: str | Path, run_id: str | None = None) -> dict[str, Any]:
    enforcer = PolicyEnforcer(run_id=run_id)
    report = enforcer.scan_directory(directory)
    return report.to_dict()


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "."
    run_id = sys.argv[2] if len(sys.argv) > 2 else None

    enforcer = PolicyEnforcer(run_id=run_id)
    path = Path(target)

    if path.is_dir():
        report = enforcer.scan_directory(path)
    else:
        report = enforcer.scan_file(path)

    status = "PASS" if report.passed else "FAIL"
    print(f"[{status}] Policy scan: {target}")
    print(f"  Files scanned: {report.files_scanned}")
    print(f"  Findings: {len(report.findings)}")
    print(f"  Secrets found: {report.secrets_found}")
    print(f"  Policy violations: {report.policy_violations}")
    print(f"  Risk score: {report.risk_score:.3f}")

    for finding in report.findings:
        print(f"  [{finding.severity.upper()}] {finding.rule_id}: {finding.message}")
        print(f"    {finding.file_path}:{finding.line_number}")
        if finding.matched_text:
            print(f"    Matched: {finding.matched_text[:100]}")

    sys.exit(0 if report.passed else 1)
