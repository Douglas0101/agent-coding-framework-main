"""
Skill: change_impact_deep (explore mode)

Deep analysis of change impact across contracts, skills, domain packs,
and runtime components. Uses dependency surface data to compute blast radius,
risk propagation, and migration requirements.
"""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INTERNAL_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = INTERNAL_DIR.parent
SPECS_DIR = INTERNAL_DIR / "specs"
MODES_DIR = SPECS_DIR / "modes"


@dataclass
class ImpactFinding:
    finding_id: str
    severity: str  # critical, high, medium, low
    category: str  # contract_breaking, skill_affected, pack_affected, runtime_affected
    affected_component: str
    change_description: str
    propagation_path: list[str] = field(default_factory=list)
    mitigation: str = ""


@dataclass
class RiskPropagation:
    source: str
    affected: list[str] = field(default_factory=list)
    depth: int = 0
    risk_multiplier: float = 1.0


@dataclass
class MigrationRequirement:
    component: str
    migration_type: str  # breaking, non_breaking, config_only
    steps: list[str] = field(default_factory=list)
    estimated_effort: str = ""  # trivial, small, medium, large
    rollback_plan: str = ""


@dataclass
class ChangeImpactReport:
    run_id: str
    timestamp: str
    change_description: str
    changed_files: list[str] = field(default_factory=list)
    findings: list[ImpactFinding] = field(default_factory=list)
    risk_propagation: list[RiskPropagation] = field(default_factory=list)
    migration_requirements: list[MigrationRequirement] = field(default_factory=list)
    overall_risk: str = "low"
    requires_review: bool = False
    requires_migration: bool = False
    integrity_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "change_description": self.change_description,
            "changed_files": self.changed_files,
            "findings": [asdict(f) for f in self.findings],
            "risk_propagation": [asdict(p) for p in self.risk_propagation],
            "migration_requirements": [asdict(m) for m in self.migration_requirements],
            "overall_risk": self.overall_risk,
            "requires_review": self.requires_review,
            "requires_migration": self.requires_migration,
            "integrity_hash": self.integrity_hash,
        }


class ChangeImpactAnalyzer:
    """Deep analysis of change impact across the framework."""

    CONTRACT_PATHS = {
        "core": str(SPECS_DIR / "core"),
        "modes": str(MODES_DIR),
        "domains": str(INTERNAL_DIR / "domains"),
    }

    def __init__(self, run_id: str | None = None) -> None:
        self.run_id = (
            run_id or f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        )
        self._findings: list[ImpactFinding] = []
        self._propagations: list[RiskPropagation] = []
        self._migrations: list[MigrationRequirement] = []
        self._finding_counter = 0

    def analyze(
        self,
        changed_files: list[str],
        change_description: str = "",
        dependency_surface: dict[str, Any] | None = None,
    ) -> ChangeImpactReport:
        self._analyze_contract_changes(changed_files)
        self._analyze_skill_changes(changed_files)
        self._analyze_pack_changes(changed_files)
        self._analyze_runtime_changes(changed_files)
        self._analyze_config_changes(changed_files)

        if dependency_surface:
            self._analyze_dependency_impact(changed_files, dependency_surface)

        self._compute_risk_propagation()
        self._compute_migration_requirements()

        overall_risk = self._compute_overall_risk()

        report = ChangeImpactReport(
            run_id=self.run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            change_description=change_description,
            changed_files=changed_files,
            findings=self._findings,
            risk_propagation=self._propagations,
            migration_requirements=self._migrations,
            overall_risk=overall_risk,
            requires_review=overall_risk in ("critical", "high"),
            requires_migration=len(self._migrations) > 0,
        )
        report.integrity_hash = self._compute_hash(report)
        return report

    def _analyze_contract_changes(self, changed_files: list[str]) -> None:
        for f in changed_files:
            if f.startswith(".internal/specs/core/"):
                self._add_finding(
                    severity="critical",
                    category="contract_breaking",
                    affected_component="core_contract",
                    change_description=f"Core contract changed: {f}",
                    propagation_path=["core", "all_modes", "all_packs"],
                    mitigation="All mode contracts and domain packs must be re-validated",
                )
            elif f.startswith(".internal/specs/modes/"):
                mode_name = Path(f).stem
                self._add_finding(
                    severity="high",
                    category="contract_breaking",
                    affected_component=f"mode_contract:{mode_name}",
                    change_description=f"Mode contract changed: {f}",
                    propagation_path=[f"mode:{mode_name}", "skills", "handoffs"],
                    mitigation=f"Re-validate {mode_name} skills and handoff targets",
                )

    def _analyze_skill_changes(self, changed_files: list[str]) -> None:
        for f in changed_files:
            if f.startswith(".internal/skills/") and f.endswith(".py"):
                skill_name = Path(f).stem
                if skill_name.startswith("test_"):
                    continue
                self._add_finding(
                    severity="medium",
                    category="skill_affected",
                    affected_component=f"skill:{skill_name}",
                    change_description=f"Skill changed: {f}",
                    propagation_path=[f"skill:{skill_name}", "target_mode"],
                    mitigation=f"Run skill regression tests for {skill_name}",
                )

    def _analyze_pack_changes(self, changed_files: list[str]) -> None:
        for f in changed_files:
            if f.startswith(".internal/domains/"):
                pack_name = Path(f).parent.name
                self._add_finding(
                    severity="medium",
                    category="pack_affected",
                    affected_component=f"domain_pack:{pack_name}",
                    change_description=f"Domain pack changed: {f}",
                    propagation_path=[f"pack:{pack_name}", "core_protocols"],
                    mitigation=f"Validate {pack_name} against core protocols",
                )

    def _analyze_runtime_changes(self, changed_files: list[str]) -> None:
        for f in changed_files:
            if f.startswith(".internal/runtime/") and f.endswith(".py"):
                component = Path(f).stem
                if component.startswith("test_"):
                    continue
                self._add_finding(
                    severity="high",
                    category="runtime_affected",
                    affected_component=f"runtime:{component}",
                    change_description=f"Runtime component changed: {f}",
                    propagation_path=[f"runtime:{component}", "all_modes"],
                    mitigation=f"Run full conformance suite after {component} changes",
                )

    def _analyze_config_changes(self, changed_files: list[str]) -> None:
        for f in changed_files:
            if f in ("opencode.json", ".opencode/opencode.json"):
                self._add_finding(
                    severity="high",
                    category="contract_breaking",
                    affected_component="config_binding",
                    change_description=f"Config binding changed: {f}",
                    propagation_path=["config", "routing", "mode_binding"],
                    mitigation="Verify config parity and routing fields",
                )
            elif f.startswith(".github/workflows/"):
                self._add_finding(
                    severity="medium",
                    category="runtime_affected",
                    affected_component="ci_pipeline",
                    change_description=f"CI workflow changed: {f}",
                    propagation_path=["ci", "gates", "validation"],
                    mitigation="Run CI workflow locally to verify",
                )

    def _analyze_dependency_impact(
        self, changed_files: list[str], dep_surface: dict[str, Any]
    ) -> None:
        blast_radius = dep_surface.get("blast_radius", {})
        for f in changed_files:
            module_key = f.replace("/", ".").replace(".py", "")
            affected = blast_radius.get(module_key, [])
            if affected:
                self._propagations.append(
                    RiskPropagation(
                        source=f,
                        affected=affected,
                        depth=len(affected),
                        risk_multiplier=min(1.0 + len(affected) * 0.1, 3.0),
                    )
                )

        circular = dep_surface.get("circular_dependencies", [])
        for cd in circular:
            chain = cd.get("chain", [])
            for cf in changed_files:
                cf_module = cf.replace("/", ".").replace(".py", "")
                if cf_module in chain:
                    self._add_finding(
                        severity="high",
                        category="runtime_affected",
                        affected_component=f"circular_dep:{cf}",
                        change_description=f"Changed file involved in circular dependency",
                        propagation_path=chain,
                        mitigation="Break circular dependency or add indirection",
                    )

    def _compute_risk_propagation(self) -> None:
        if not self._findings:
            return

        affected_components: dict[str, list[str]] = {}
        for finding in self._findings:
            comp = finding.affected_component
            if comp not in affected_components:
                affected_components[comp] = []
            affected_components[comp].extend(finding.propagation_path)

        for comp, paths in affected_components.items():
            unique_paths = list(set(paths))
            if unique_paths:
                self._propagations.append(
                    RiskPropagation(
                        source=comp,
                        affected=unique_paths,
                        depth=len(unique_paths),
                        risk_multiplier=min(1.0 + len(unique_paths) * 0.15, 3.0),
                    )
                )

    def _compute_migration_requirements(self) -> None:
        for finding in self._findings:
            if finding.severity == "critical":
                self._migrations.append(
                    MigrationRequirement(
                        component=finding.affected_component,
                        migration_type="breaking",
                        steps=[
                            f"Review {finding.affected_component} changes",
                            "Update dependent contracts",
                            "Run full conformance suite",
                            "Update golden traces",
                        ],
                        estimated_effort="large",
                        rollback_plan="Revert to previous contract version",
                    )
                )
            elif finding.severity == "high":
                self._migrations.append(
                    MigrationRequirement(
                        component=finding.affected_component,
                        migration_type="non_breaking",
                        steps=[
                            f"Verify {finding.affected_component} compatibility",
                            "Run mode-specific tests",
                        ],
                        estimated_effort="medium",
                        rollback_plan="Revert component changes",
                    )
                )

    def _compute_overall_risk(self) -> str:
        if not self._findings:
            return "low"

        severity_scores = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        max_score = max(severity_scores.get(f.severity, 0) for f in self._findings)
        critical_count = sum(1 for f in self._findings if f.severity == "critical")
        high_count = sum(1 for f in self._findings if f.severity == "high")

        if critical_count > 0:
            return "critical"
        if high_count >= 3:
            return "critical"
        if high_count > 0:
            return "high"
        if max_score >= 2:
            return "medium"
        return "low"

    def _add_finding(
        self,
        severity: str,
        category: str,
        affected_component: str,
        change_description: str,
        propagation_path: list[str] | None = None,
        mitigation: str = "",
    ) -> None:
        self._finding_counter += 1
        self._findings.append(
            ImpactFinding(
                finding_id=f"impact-{self._finding_counter:04d}",
                severity=severity,
                category=category,
                affected_component=affected_component,
                change_description=change_description,
                propagation_path=propagation_path or [],
                mitigation=mitigation,
            )
        )

    def _compute_hash(self, report: ChangeImpactReport) -> str:
        content = json.dumps(
            {
                "run_id": report.run_id,
                "changed_files": sorted(report.changed_files),
                "finding_count": len(report.findings),
                "overall_risk": report.overall_risk,
            },
            sort_keys=True,
            default=str,
        )
        return f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"


def analyze_change_impact(
    changed_files: list[str],
    run_id: str | None = None,
    change_description: str = "",
    dependency_surface: dict[str, Any] | None = None,
) -> dict[str, Any]:
    analyzer = ChangeImpactAnalyzer(run_id=run_id)
    report = analyzer.analyze(changed_files, change_description, dependency_surface)
    return report.to_dict()


if __name__ == "__main__":
    import sys

    run_id = sys.argv[1] if len(sys.argv) > 1 else None
    changed = (
        sys.argv[2:]
        if len(sys.argv) > 2
        else [
            ".internal/specs/modes/explore.yaml",
            ".internal/runtime/contract_verifier.py",
        ]
    )

    result = analyze_change_impact(
        changed_files=changed,
        run_id=run_id,
        change_description="Sample change impact analysis",
    )

    print(f"[{result['overall_risk'].upper()}] Change impact: {result['run_id']}")
    print(f"  Changed files: {len(result['changed_files'])}")
    print(f"  Findings: {len(result['findings'])}")
    print(f"  Requires review: {result['requires_review']}")
    print(f"  Requires migration: {result['requires_migration']}")

    for f in result["findings"]:
        print(f"  [{f['severity'].upper()}] {f['category']}: {f['change_description']}")

    for m in result["migration_requirements"]:
        print(f"  Migration: {m['component']} ({m['migration_type']})")
