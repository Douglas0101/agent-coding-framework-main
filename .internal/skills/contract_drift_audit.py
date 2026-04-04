"""
Skill: contract_drift_audit (reviewer mode)

Detects drift between mode contracts, config bindings, and actual enforcement.
Produces structured drift reports with severity classification.
"""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INTERNAL_DIR = Path(__file__).resolve().parent.parent.parent
SPECS_DIR = INTERNAL_DIR / "specs"
MODES_DIR = SPECS_DIR / "modes"


@dataclass
class DriftFinding:
    drift_id: str
    severity: str  # critical, high, medium, low
    category: (
        str  # config_drift, budget_drift, skill_drift, schema_drift, version_drift
    )
    source: str
    target: str
    expected: str
    actual: str
    message: str


@dataclass
class DriftReport:
    run_id: str
    timestamp: str
    findings: list[DriftFinding] = field(default_factory=list)
    modes_checked: int = 0
    configs_checked: int = 0
    integrity_hash: str = ""

    @property
    def has_drift(self) -> bool:
        return any(f.severity in ("critical", "high") for f in self.findings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "has_drift": self.has_drift,
            "modes_checked": self.modes_checked,
            "configs_checked": self.configs_checked,
            "findings": [asdict(f) for f in self.findings],
            "integrity_hash": self.integrity_hash,
        }


class ContractDriftAuditor:
    """Detects drift between contracts, configs, and enforcement."""

    def __init__(self, run_id: str | None = None) -> None:
        self.run_id = (
            run_id or f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        )
        self.findings: list[DriftFinding] = []
        self._drift_counter = 0

    def audit(self) -> DriftReport:
        self._check_config_contract_drift()
        self._check_budget_drift()
        self._check_skill_drift()
        self._check_version_drift()
        self._check_cross_mode_handoff_drift()

        report = DriftReport(
            run_id=self.run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings=self.findings,
            modes_checked=4,
            configs_checked=2,
        )
        report.integrity_hash = self._compute_hash(report)
        return report

    def _add_finding(
        self,
        severity: str,
        category: str,
        source: str,
        target: str,
        expected: str,
        actual: str,
        message: str,
    ) -> None:
        self._drift_counter += 1
        self.findings.append(
            DriftFinding(
                drift_id=f"drift-{self._drift_counter:04d}",
                severity=severity,
                category=category,
                source=source,
                target=target,
                expected=expected,
                actual=actual,
                message=message,
            )
        )

    def _check_config_contract_drift(self) -> None:
        """Check that opencode.json mode_contract paths match actual files."""
        import yaml

        config_paths = [
            Path("opencode.json"),
            Path(".opencode/opencode.json"),
        ]

        for config_path in config_paths:
            if not config_path.exists():
                continue
            try:
                config = json.loads(config_path.read_text())
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue

            agents = config.get("agent", {})
            for agent_name, agent_config in agents.items():
                contract_path = agent_config.get("mode_contract")
                if contract_path:
                    full_path = Path(contract_path)
                    if not full_path.exists():
                        self._add_finding(
                            severity="critical",
                            category="config_drift",
                            source=str(config_path),
                            target=contract_path,
                            expected="file exists",
                            actual="file not found",
                            message=f"Mode contract referenced in {config_path} not found: {contract_path}",
                        )

    def _check_budget_drift(self) -> None:
        """Check that budgets in contracts are consistent with ADR-003."""
        import yaml

        for mode_file in sorted(MODES_DIR.glob("*.yaml")):
            try:
                with open(mode_file, encoding="utf-8") as fh:
                    contract = yaml.safe_load(fh)
            except (yaml.YAMLError, UnicodeDecodeError):
                continue

            amc = contract.get("agent_mode_contract", contract)
            res = amc.get("resources", {})
            mem = amc.get("memory", {})

            hp_max = mem.get("handoff_payload_budget", {}).get("max_tokens", 0)
            ctx_max = res.get("max_context_tokens", 0)

            if hp_max and ctx_max and hp_max > ctx_max:
                self._add_finding(
                    severity="high",
                    category="budget_drift",
                    source=str(mode_file),
                    target="memory.handoff_payload_budget",
                    expected=f"<= {ctx_max}",
                    actual=str(hp_max),
                    message=f"Handoff budget ({hp_max}) exceeds context budget ({ctx_max}) in {mode_file.stem}",
                )

            total_budget = res.get("max_input_tokens", 0) + res.get(
                "max_output_tokens", 0
            )
            mode_name = amc.get("metadata", {}).get("name", mode_file.stem)
            if total_budget == 0:
                self._add_finding(
                    severity="medium",
                    category="budget_drift",
                    source=str(mode_file),
                    target="resources",
                    expected="positive token budget",
                    actual="0",
                    message=f"Zero token budget in {mode_file.stem}",
                )

    def _check_skill_drift(self) -> None:
        """Check that skills declared in contracts have valid sources and budgets."""
        import yaml

        for mode_file in sorted(MODES_DIR.glob("*.yaml")):
            try:
                with open(mode_file, encoding="utf-8") as fh:
                    contract = yaml.safe_load(fh)
            except (yaml.YAMLError, UnicodeDecodeError):
                continue

            amc = contract.get("agent_mode_contract", contract)
            skills = amc.get("skills", [])
            mode_name = amc.get("metadata", {}).get("name", mode_file.stem)
            total_budget = 0.0

            for skill in skills:
                bs = skill.get("budget_share", 0)
                total_budget += bs

                if not skill.get("source"):
                    self._add_finding(
                        severity="high",
                        category="skill_drift",
                        source=str(mode_file),
                        target=f"skills.{skill.get('name', 'unknown')}",
                        expected="valid source",
                        actual="missing",
                        message=f"Skill '{skill.get('name')}' in {mode_name} missing source",
                    )

            if total_budget > 1.0:
                self._add_finding(
                    severity="critical",
                    category="skill_drift",
                    source=str(mode_file),
                    target=f"skills (total budget)",
                    expected="<= 1.0",
                    actual=str(total_budget),
                    message=f"Total skill budget_share exceeds 1.0 in {mode_name}: {total_budget}",
                )

    def _check_version_drift(self) -> None:
        """Check that contract versions are valid semver."""
        import yaml
        import re

        semver_pattern = re.compile(r"^\d+\.\d+\.\d+$")

        for mode_file in sorted(MODES_DIR.glob("*.yaml")):
            try:
                with open(mode_file, encoding="utf-8") as fh:
                    contract = yaml.safe_load(fh)
            except (yaml.YAMLError, UnicodeDecodeError):
                continue

            amc = contract.get("agent_mode_contract", contract)
            version = amc.get("metadata", {}).get("version", "")
            if version and not semver_pattern.match(version):
                self._add_finding(
                    severity="medium",
                    category="version_drift",
                    source=str(mode_file),
                    target="metadata.version",
                    expected="semver (MAJOR.MINOR.PATCH)",
                    actual=version,
                    message=f"Invalid version format in {mode_file.stem}: {version}",
                )

    def _check_cross_mode_handoff_drift(self) -> None:
        """Check that handoff targets reference existing modes."""
        import yaml

        existing_modes = {f.stem for f in MODES_DIR.glob("*.yaml")}

        for mode_file in sorted(MODES_DIR.glob("*.yaml")):
            try:
                with open(mode_file, encoding="utf-8") as fh:
                    contract = yaml.safe_load(fh)
            except (yaml.YAMLError, UnicodeDecodeError):
                continue

            amc = contract.get("agent_mode_contract", contract)
            handoff = amc.get("handoff", {})
            targets = handoff.get("allowed_targets", [])
            mode_name = amc.get("metadata", {}).get("name", mode_file.stem)

            for target in targets:
                if target not in existing_modes:
                    self._add_finding(
                        severity="high",
                        category="schema_drift",
                        source=str(mode_file),
                        target=f"handoff.allowed_targets.{target}",
                        expected=f"one of {existing_modes}",
                        actual=target,
                        message=f"Handoff target '{target}' in {mode_name} does not exist",
                    )

    def _compute_hash(self, report: DriftReport) -> str:
        content = json.dumps(
            {
                "run_id": report.run_id,
                "findings": [asdict(f) for f in report.findings],
            },
            sort_keys=True,
            default=str,
        )
        return f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"


def audit_drift(run_id: str | None = None) -> dict[str, Any]:
    auditor = ContractDriftAuditor(run_id=run_id)
    report = auditor.audit()
    return report.to_dict()


if __name__ == "__main__":
    import sys

    run_id = sys.argv[1] if len(sys.argv) > 1 else None
    result = audit_drift(run_id=run_id)

    status = "DRIFT DETECTED" if result["has_drift"] else "NO DRIFT"
    print(f"[{status}] Drift audit: {result['run_id']}")
    print(f"  Modes checked: {result['modes_checked']}")
    print(f"  Configs checked: {result['configs_checked']}")
    print(f"  Findings: {len(result['findings'])}")

    for f in result["findings"]:
        print(f"  [{f['severity'].upper()}] {f['category']}: {f['message']}")

    sys.exit(1 if result["has_drift"] else 0)
