#!/usr/bin/env python3
"""Script de automação para auditoria de segurança com Bandit.

Executa scans SAST, classifica vulnerabilidades por severidade
e gera relatórios detalhados.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class Vulnerability:
    """Representa uma vulnerabilidade encontrada."""

    test_id: str
    test_name: str
    severity: str
    confidence: str
    filename: str
    line_number: int
    code: str
    issue_text: str

    @property
    def severity_level(self) -> int:
        """Retorna nível numérico de severidade."""
        levels = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
        return levels.get(self.severity.upper(), 0)


@dataclass
class ScanResult:
    """Resultado de um scan de segurança."""

    scan_time: str
    files_scanned: int
    vulnerabilities: list[Vulnerability] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def critical_count(self) -> int:
        """Conta vulnerabilidades HIGH severity."""
        return sum(1 for v in self.vulnerabilities if v.severity == "HIGH")

    @property
    def warning_count(self) -> int:
        """Conta vulnerabilidades MEDIUM severity."""
        return sum(1 for v in self.vulnerabilities if v.severity == "MEDIUM")

    @property
    def info_count(self) -> int:
        """Conta vulnerabilidades LOW severity."""
        return sum(1 for v in self.vulnerabilities if v.severity == "LOW")


def run_bandit(
    paths: list[str],
    severity_level: str = "low",
) -> tuple[int, str]:
    """Executa Bandit e retorna código e output JSON."""
    cmd = [
        "bandit",
        "-r",
        *paths,
        "-f",
        "json",
        "-ll" if severity_level == "medium" else "-l",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parents[4],
    )

    return result.returncode, result.stdout or result.stderr


def parse_bandit_output(json_output: str) -> ScanResult:
    """Parseia output JSON do Bandit."""
    try:
        data = json.loads(json_output)
    except json.JSONDecodeError:
        return ScanResult(
            scan_time=datetime.now(UTC).isoformat(),
            files_scanned=0,
            errors=[f"Failed to parse Bandit output: {json_output[:200]}"],
        )

    vulnerabilities = []
    for result in data.get("results", []):
        vuln = Vulnerability(
            test_id=result.get("test_id", ""),
            test_name=result.get("test_name", ""),
            severity=result.get("issue_severity", "UNKNOWN"),
            confidence=result.get("issue_confidence", "UNKNOWN"),
            filename=result.get("filename", ""),
            line_number=result.get("line_number", 0),
            code=result.get("code", ""),
            issue_text=result.get("issue_text", ""),
        )
        vulnerabilities.append(vuln)

    metrics = data.get("metrics", {})
    total_files = sum(
        m.get("loc", 0) > 0 for m in metrics.values() if isinstance(m, dict)
    )

    return ScanResult(
        scan_time=datetime.now(UTC).isoformat(),
        files_scanned=total_files,
        vulnerabilities=vulnerabilities,
    )


def format_report(result: ScanResult) -> str:
    """Formata relatório de segurança."""
    lines = [
        "=" * 70,
        "SECURITY AUDIT REPORT",
        f"Scan Time: {result.scan_time}",
        f"Files Analyzed: {result.files_scanned}",
        "=" * 70,
        "",
        "SUMMARY",
        "-" * 70,
        f"  🔴 HIGH Severity:   {result.critical_count}",
        f"  🟡 MEDIUM Severity: {result.warning_count}",
        f"  🔵 LOW Severity:    {result.info_count}",
        f"  Total Issues:       {len(result.vulnerabilities)}",
        "",
    ]

    if result.vulnerabilities:
        lines.append("VULNERABILITIES")
        lines.append("-" * 70)

        # Agrupa por severidade
        for severity in ["HIGH", "MEDIUM", "LOW"]:
            vulns = [
                v for v in result.vulnerabilities if v.severity == severity
            ]
            if vulns:
                emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🔵"}[severity]
                lines.append(f"\n{emoji} {severity} SEVERITY ({len(vulns)})")
                lines.append("")

                for vuln in vulns:
                    lines.extend(
                        [
                            f"  [{vuln.test_id}] {vuln.test_name}",
                            f"  File: {vuln.filename}:{vuln.line_number}",
                            f"  Issue: {vuln.issue_text}",
                            f"  Confidence: {vuln.confidence}",
                            "",
                        ]
                    )

    lines.extend(
        [
            "=" * 70,
            "RECOMMENDATIONS",
            "-" * 70,
        ]
    )

    if result.critical_count > 0:
        lines.append("⚠️  HIGH severity issues MUST be fixed before deploy!")
    elif result.warning_count > 0:
        lines.append("📋 Review MEDIUM severity issues for potential fixes.")
    else:
        lines.append("✅ No critical security issues found.")

    lines.append("=" * 70)

    return "\n".join(lines)


def main() -> int:
    """Função principal."""
    parser = argparse.ArgumentParser(
        description="Security audit automation with Bandit"
    )
    parser.add_argument(
        "--paths",
        nargs="+",
        default=["src/"],
        help="Paths to scan (default: src/)",
    )
    parser.add_argument(
        "--critical-only",
        action="store_true",
        help="Only show HIGH severity issues",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate detailed report",
    )

    args = parser.parse_args()

    print("🔍 Running security audit...")

    _code, output = run_bandit(args.paths)
    result = parse_bandit_output(output)

    if args.critical_only:
        result.vulnerabilities = [
            v for v in result.vulnerabilities if v.severity == "HIGH"
        ]

    if args.json:
        json_output = {
            "scan_time": result.scan_time,
            "files_scanned": result.files_scanned,
            "summary": {
                "high": result.critical_count,
                "medium": result.warning_count,
                "low": result.info_count,
                "total": len(result.vulnerabilities),
            },
            "vulnerabilities": [
                {
                    "test_id": v.test_id,
                    "severity": v.severity,
                    "file": v.filename,
                    "line": v.line_number,
                    "issue": v.issue_text,
                }
                for v in result.vulnerabilities
            ],
        }
        print(json.dumps(json_output, indent=2))
    elif args.report:
        report = format_report(result)
        print(report)

        # Salva relatório
        report_path = (
            Path(__file__).parents[4] / "artifacts" / "security_report.txt"
        )
        report_path.parent.mkdir(exist_ok=True)
        report_path.write_text(report)
        print(f"\n📄 Report saved to: {report_path}")
    else:
        # Output resumido
        if result.critical_count > 0:
            print(f"🔴 {result.critical_count} HIGH severity issues found!")
        if result.warning_count > 0:
            print(f"🟡 {result.warning_count} MEDIUM severity issues found.")
        if result.info_count > 0:
            print(f"🔵 {result.info_count} LOW severity issues found.")

        if len(result.vulnerabilities) == 0:
            print("✅ No security issues found!")

    # Exit code baseado em vulnerabilidades críticas
    if result.critical_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
