"""
Contract Verifier — Runtime enforcement for mode contracts.

Validates mode contracts against schema, checks invariant compliance,
and produces structured verification reports.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INTERNAL_DIR = Path(__file__).resolve().parent.parent
SPECS_DIR = INTERNAL_DIR / "specs"
MODES_DIR = SPECS_DIR / "modes"
CORE_DIR = SPECS_DIR / "core"


@dataclass
class Violation:
    rule_id: str
    severity: str  # critical, warning, info
    message: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationReport:
    run_id: str
    mode: str
    contract_version: str
    timestamp: str
    violations: list[Violation] = field(default_factory=list)
    checks_passed: int = 0
    checks_failed: int = 0
    integrity_hash: str = ""

    @property
    def passed(self) -> bool:
        return not any(v.severity == "critical" for v in self.violations)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "mode": self.mode,
            "contract_version": self.contract_version,
            "timestamp": self.timestamp,
            "passed": self.passed,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "violations": [asdict(v) for v in self.violations],
            "integrity_hash": self.integrity_hash,
        }


class ContractVerifier:
    """Validates mode contracts against schema and invariants."""

    REQUIRED_SECTIONS = [
        "metadata",
        "mission",
        "scope",
        "resources",
        "memory",
        "satisficing",
        "handoff",
        "error_policy",
    ]

    VALID_SATISFICING = {"URGENT", "ECONOMICAL", "BALANCED", "DEEP"}
    VALID_RETENTION = {"ephemeral", "session", "persistent"}
    VALID_COMPRESSION = {"none", "summary", "summary+refs", "delta"}
    VALID_BUDGET_POLICY = {"fail_fast", "degrade_gracefully", "notify_and_continue"}

    def __init__(self, run_id: str | None = None) -> None:
        self.run_id = (
            run_id or f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        )

    def verify_mode(self, mode_name: str) -> VerificationReport:
        contract_path = MODES_DIR / f"{mode_name}.yaml"
        if not contract_path.exists():
            return VerificationReport(
                run_id=self.run_id,
                mode=mode_name,
                contract_version="unknown",
                timestamp=datetime.now(timezone.utc).isoformat(),
                violations=[
                    Violation(
                        rule_id="CV-000",
                        severity="critical",
                        message=f"Contract file not found: {contract_path}",
                    )
                ],
            )

        contract = self._load_yaml(contract_path)
        report = VerificationReport(
            run_id=self.run_id,
            mode=mode_name,
            contract_version=contract.get("agent_mode_contract", {})
            .get("metadata", {})
            .get("version", "unknown"),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        violations: list[Violation] = []
        passed = 0

        checks = [
            ("CV-001", self._check_required_sections),
            ("CV-002", self._check_metadata),
            ("CV-003", self._check_mission),
            ("CV-004", self._check_scope),
            ("CV-005", self._check_resources),
            ("CV-006", self._check_memory),
            ("CV-007", self._check_satisficing),
            ("CV-008", self._check_handoff),
            ("CV-009", self._check_error_policy),
            ("CV-010", self._check_skills),
            ("CV-011", self._check_budget_conservation),
            ("CV-012", self._check_tools_disjoint),
        ]

        for rule_id, check_fn in checks:
            try:
                result = check_fn(contract)
                violations.extend(result)
                if not result:
                    passed += 1
            except Exception as exc:
                violations.append(
                    Violation(
                        rule_id=rule_id,
                        severity="critical",
                        message=f"Check raised exception: {exc}",
                    )
                )

        report.violations = violations
        report.checks_passed = passed
        report.checks_failed = len(violations)
        report.integrity_hash = self._compute_hash(contract)
        return report

    def verify_all_modes(self) -> dict[str, VerificationReport]:
        results = {}
        for mode_file in sorted(MODES_DIR.glob("*.yaml")):
            mode_name = mode_file.stem
            results[mode_name] = self.verify_mode(mode_name)
        return results

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        try:
            import yaml

            with open(path, encoding="utf-8") as fh:
                return yaml.safe_load(fh)
        except ImportError:
            return self._parse_yaml_manual(path)

    def _parse_yaml_manual(self, path: Path) -> dict[str, Any]:
        """Minimal YAML parser for mode contracts when PyYAML unavailable."""
        content = path.read_text(encoding="utf-8")
        result: dict[str, Any] = {"agent_mode_contract": {}}
        current_section = None
        current_subsection = None
        current_list = None

        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            indent = len(line) - len(line.lstrip())

            if indent == 0 and stripped.startswith("agent_mode_contract:"):
                continue

            if indent == 2 and stripped.endswith(":"):
                current_section = stripped[:-1]
                result["agent_mode_contract"][current_section] = {}
                current_subsection = None
                current_list = None
            elif indent == 4 and current_section and stripped.endswith(":"):
                current_subsection = stripped[:-1]
                result["agent_mode_contract"][current_section][current_subsection] = {}
                current_list = None
            elif (
                indent == 6
                and current_section
                and current_subsection
                and stripped.endswith(":")
            ):
                key = stripped[:-1]
                result["agent_mode_contract"][current_section][current_subsection][
                    key
                ] = {}
            elif indent >= 6 and ":" in stripped and not stripped.startswith("-"):
                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if current_subsection and current_section:
                    section_data = result["agent_mode_contract"][current_section]
                    if isinstance(section_data.get(current_subsection), dict):
                        section_data[current_subsection][key] = self._coerce(value)
            elif stripped.startswith("- ") and current_subsection and current_section:
                section_data = result["agent_mode_contract"][current_section]
                if not isinstance(section_data.get(current_subsection), list):
                    section_data[current_subsection] = []
                item = stripped[2:].strip().strip('"').strip("'")
                section_data[current_subsection].append(item)

        return result

    def _coerce(self, value: str) -> Any:
        if not value:
            return ""
        if value.lower() in ("true", "yes"):
            return True
        if value.lower() in ("false", "no"):
            return False
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        return value

    def _check_required_sections(self, contract: dict) -> list[Violation]:
        violations = []
        amc = contract.get("agent_mode_contract", contract)
        for section in self.REQUIRED_SECTIONS:
            if section not in amc:
                violations.append(
                    Violation(
                        rule_id="CV-001",
                        severity="critical",
                        message=f"Missing required section: {section}",
                    )
                )
        return violations

    def _check_metadata(self, contract: dict) -> list[Violation]:
        violations = []
        amc = contract.get("agent_mode_contract", contract)
        meta = amc.get("metadata", {})
        for field_name in (
            "name",
            "version",
            "parent_contract",
            "created",
            "last_modified",
            "author",
        ):
            if not meta.get(field_name):
                violations.append(
                    Violation(
                        rule_id="CV-002",
                        severity="critical",
                        message=f"Missing metadata field: {field_name}",
                    )
                )
        return violations

    def _check_mission(self, contract: dict) -> list[Violation]:
        violations = []
        amc = contract.get("agent_mode_contract", contract)
        mission = amc.get("mission", {})
        for field_name in (
            "description",
            "success_criteria",
            "failure_conditions",
            "priority",
        ):
            if field_name not in mission:
                violations.append(
                    Violation(
                        rule_id="CV-003",
                        severity="critical",
                        message=f"Missing mission field: {field_name}",
                    )
                )
        priority = mission.get("priority", "")
        if priority and priority not in ("critical", "high", "medium", "low"):
            violations.append(
                Violation(
                    rule_id="CV-003",
                    severity="warning",
                    message=f"Invalid priority: {priority}",
                )
            )
        return violations

    def _check_scope(self, contract: dict) -> list[Violation]:
        violations = []
        amc = contract.get("agent_mode_contract", contract)
        scope = amc.get("scope", {})
        if "input_schema" not in scope:
            violations.append(Violation("CV-004", "critical", "Missing input_schema"))
        if "output_schema" not in scope:
            violations.append(Violation("CV-004", "critical", "Missing output_schema"))
        if "tools_allowlist" not in scope:
            violations.append(
                Violation("CV-004", "critical", "Missing tools_allowlist")
            )
        if "tools_denylist" not in scope:
            violations.append(Violation("CV-004", "critical", "Missing tools_denylist"))
        return violations

    def _check_resources(self, contract: dict) -> list[Violation]:
        violations = []
        amc = contract.get("agent_mode_contract", contract)
        res = amc.get("resources", {})
        resource_fields = [
            "max_input_tokens",
            "max_output_tokens",
            "max_context_tokens",
            "max_retrieval_chunks",
            "max_iterations",
            "max_handoffs",
            "timeout_seconds",
        ]
        for field_name in resource_fields:
            value = res.get(field_name)
            if value is None:
                violations.append(
                    Violation("CV-005", "critical", f"Missing resource: {field_name}")
                )
            elif not isinstance(value, (int, float)) or value <= 0:
                violations.append(
                    Violation(
                        "CV-005",
                        "critical",
                        f"Resource must be positive: {field_name}={value}",
                    )
                )
        return violations

    def _check_memory(self, contract: dict) -> list[Violation]:
        violations = []
        amc = contract.get("agent_mode_contract", contract)
        mem = amc.get("memory", {})
        for tier in ("operational_context", "session_state", "structural_memory"):
            if tier not in mem:
                violations.append(
                    Violation("CV-006", "critical", f"Missing memory tier: {tier}")
                )
                continue
            tier_data = mem[tier]
            if "max_tokens" not in tier_data:
                violations.append(
                    Violation("CV-006", "critical", f"Missing {tier}.max_tokens")
                )
            if "retention" not in tier_data:
                violations.append(
                    Violation("CV-006", "critical", f"Missing {tier}.retention")
                )
            elif tier_data["retention"] not in self.VALID_RETENTION:
                violations.append(
                    Violation(
                        "CV-006",
                        "warning",
                        f"Invalid retention: {tier_data['retention']}",
                    )
                )
        hp = mem.get("handoff_payload_budget", {})
        if "max_tokens" not in hp:
            violations.append(
                Violation(
                    "CV-006", "critical", "Missing handoff_payload_budget.max_tokens"
                )
            )
        if (
            "compression_mode" in hp
            and hp["compression_mode"] not in self.VALID_COMPRESSION
        ):
            violations.append(
                Violation(
                    "CV-006",
                    "warning",
                    f"Invalid compression_mode: {hp['compression_mode']}",
                )
            )
        return violations

    def _check_satisficing(self, contract: dict) -> list[Violation]:
        violations = []
        amc = contract.get("agent_mode_contract", contract)
        sat = amc.get("satisficing", {})
        mode = sat.get("mode", "")
        if mode and mode not in self.VALID_SATISFICING:
            violations.append(
                Violation("CV-007", "critical", f"Invalid satisficing mode: {mode}")
            )
        qt = sat.get("quality_threshold")
        if qt is not None and not (0.0 <= qt <= 1.0):
            violations.append(
                Violation("CV-007", "critical", f"quality_threshold out of range: {qt}")
            )
        return violations

    def _check_handoff(self, contract: dict) -> list[Violation]:
        violations = []
        amc = contract.get("agent_mode_contract", contract)
        handoff = amc.get("handoff", {})
        if "allowed_targets" not in handoff:
            violations.append(
                Violation("CV-008", "critical", "Missing handoff.allowed_targets")
            )
        if (
            "compression" in handoff
            and handoff["compression"] not in self.VALID_COMPRESSION
        ):
            violations.append(
                Violation(
                    "CV-008",
                    "warning",
                    f"Invalid handoff compression: {handoff['compression']}",
                )
            )
        return violations

    def _check_error_policy(self, contract: dict) -> list[Violation]:
        violations = []
        amc = contract.get("agent_mode_contract", contract)
        ep = amc.get("error_policy", {})
        retry = ep.get("retry_max")
        if retry is not None and (not isinstance(retry, int) or retry < 0 or retry > 3):
            violations.append(
                Violation("CV-009", "critical", f"retry_max must be 0-3, got {retry}")
            )
        budget_policy = ep.get("on_budget_exceeded", "")
        if budget_policy and budget_policy not in self.VALID_BUDGET_POLICY:
            violations.append(
                Violation(
                    "CV-009", "warning", f"Invalid on_budget_exceeded: {budget_policy}"
                )
            )
        return violations

    def _check_skills(self, contract: dict) -> list[Violation]:
        violations = []
        amc = contract.get("agent_mode_contract", contract)
        skills = amc.get("skills", [])
        if not skills:
            return violations

        total_budget = 0.0
        seen_names = set()
        valid_sources = {"opencode-builtin", "internal", "domain-pack"}

        for skill in skills:
            name = skill.get("name", "")
            if not name:
                violations.append(Violation("CV-010", "critical", "Skill missing name"))
                continue

            if name in seen_names:
                violations.append(
                    Violation("CV-010", "critical", f"Duplicate skill name: {name}")
                )
            seen_names.add(name)

            for field_name in ("description", "source", "trigger", "budget_share"):
                if field_name not in skill:
                    violations.append(
                        Violation(
                            "CV-010", "critical", f"Skill '{name}' missing {field_name}"
                        )
                    )

            bs = skill.get("budget_share", 0)
            if not isinstance(bs, (int, float)) or bs < 0 or bs > 1:
                violations.append(
                    Violation(
                        "CV-010",
                        "critical",
                        f"Skill '{name}' budget_share out of range: {bs}",
                    )
                )
            total_budget += bs

            source = skill.get("source", "")
            source_base = source.split(":")[0] if source else ""
            if source_base and source_base not in valid_sources:
                violations.append(
                    Violation(
                        "CV-010", "warning", f"Skill '{name}' unknown source: {source}"
                    )
                )

        if total_budget > 1.0:
            violations.append(
                Violation(
                    "CV-010",
                    "critical",
                    f"Total skill budget_share exceeds 1.0: {total_budget}",
                )
            )
        return violations

    def _check_budget_conservation(self, contract: dict) -> list[Violation]:
        violations = []
        amc = contract.get("agent_mode_contract", contract)
        mem = amc.get("memory", {})
        hp = mem.get("handoff_payload_budget", {})
        res = amc.get("resources", {})
        hp_max = hp.get("max_tokens", 0)
        ctx_max = res.get("max_context_tokens", 0)
        if hp_max and ctx_max and hp_max > ctx_max:
            violations.append(
                Violation(
                    "CV-011",
                    "critical",
                    f"handoff_payload_budget.max_tokens ({hp_max}) > max_context_tokens ({ctx_max})",
                )
            )
        return violations

    def _check_tools_disjoint(self, contract: dict) -> list[Violation]:
        violations = []
        amc = contract.get("agent_mode_contract", contract)
        scope = amc.get("scope", {})
        allowlist = set(scope.get("tools_allowlist", []))
        denylist = set(scope.get("tools_denylist", []))
        overlap = allowlist & denylist
        if overlap:
            violations.append(
                Violation(
                    "CV-012",
                    "critical",
                    f"Tools in both allowlist and denylist: {overlap}",
                )
            )
        return violations

    def _compute_hash(self, contract: dict) -> str:
        content = json.dumps(contract, sort_keys=True, default=str).encode()
        return f"sha256:{hashlib.sha256(content).hexdigest()}"


def verify_all_modes(run_id: str | None = None) -> dict[str, dict]:
    verifier = ContractVerifier(run_id=run_id)
    results = verifier.verify_all_modes()
    return {mode: report.to_dict() for mode, report in results.items()}


if __name__ == "__main__":
    import sys

    run_id = sys.argv[1] if len(sys.argv) > 1 else None
    results = verify_all_modes(run_id)

    all_passed = True
    for mode, report in results.items():
        status = "PASS" if report["passed"] else "FAIL"
        if not report["passed"]:
            all_passed = False
        print(
            f"[{status}] {mode} v{report['contract_version']} "
            f"({report['checks_passed']} passed, {report['checks_failed']} failed)"
        )
        for v in report["violations"]:
            print(f"  [{v['severity'].upper()}] {v['rule_id']}: {v['message']}")

    sys.exit(0 if all_passed else 1)
