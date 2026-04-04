"""
Approval Gate — Runtime gate for change approval and risk classification.

Evaluates changes against risk criteria, determines approval requirements,
and produces structured approval decisions.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INTERNAL_DIR = Path(__file__).resolve().parent.parent


@dataclass
class ChangeClassification:
    change_id: str
    file_path: str
    change_type: str  # addition, modification, deletion, rename
    risk_level: str  # critical, high, medium, low
    risk_factors: list[str] = field(default_factory=list)
    affected_contracts: list[str] = field(default_factory=list)
    affected_public_api: bool = False
    requires_approval: bool = False
    approvers_required: int = 0


@dataclass
class ApprovalDecision:
    run_id: str
    timestamp: str
    changes: list[ChangeClassification] = field(default_factory=list)
    overall_risk: str = "low"
    approved: bool = False
    blocked_reasons: list[str] = field(default_factory=list)
    approval_requirements: list[str] = field(default_factory=list)
    integrity_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "overall_risk": self.overall_risk,
            "approved": self.approved,
            "total_changes": len(self.changes),
            "blocked_reasons": self.blocked_reasons,
            "approval_requirements": self.approval_requirements,
            "changes": [asdict(c) for c in self.changes],
            "integrity_hash": self.integrity_hash,
        }


# Risk factor definitions
RISK_FACTORS = {
    "contract_change": {
        "level": "critical",
        "description": "Modification to mode contract or core spec",
        "approvers": 2,
    },
    "public_api_change": {
        "level": "high",
        "description": "Change to public API surface",
        "approvers": 2,
    },
    "security_pattern": {
        "level": "critical",
        "description": "Security pattern detected in changes",
        "approvers": 2,
    },
    "config_change": {
        "level": "high",
        "description": "Configuration file modification",
        "approvers": 1,
    },
    "dependency_change": {
        "level": "medium",
        "description": "Dependency addition, removal, or version change",
        "approvers": 1,
    },
    "test_delete": {
        "level": "high",
        "description": "Test file deletion",
        "approvers": 1,
    },
    "large_change": {
        "level": "medium",
        "description": "Change exceeds 200 lines",
        "approvers": 1,
    },
    "runtime_change": {
        "level": "high",
        "description": "Modification to runtime components",
        "approvers": 1,
    },
}

# File patterns for risk classification
CONTRACT_PATTERNS = [
    ".internal/specs/",
    ".internal/adr/",
    "opencode.json",
    ".opencode/opencode.json",
]

PUBLIC_API_PATTERNS = [
    "docs/",
    "README.md",
    "AGENTS.md",
]

CONFIG_PATTERNS = [
    ".pre-commit-config.yaml",
    "pyproject.toml",
    "requirements.txt",
    "setup.py",
    "setup.cfg",
    "Makefile",
    "Dockerfile",
    ".github/",
]

DEPENDENCY_FILES = [
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "setup.py",
    "package.json",
    "Pipfile",
    "poetry.lock",
    "uv.lock",
]

TEST_PATTERNS = [
    "test_",
    "_test.py",
    "tests/",
    "conftest.py",
]

RUNTIME_PATTERNS = [
    ".internal/runtime/",
    ".internal/scripts/",
]


class ApprovalGate:
    """Evaluates changes and determines approval requirements."""

    def __init__(self, run_id: str | None = None) -> None:
        self.run_id = (
            run_id or f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        )

    def classify_change(
        self,
        file_path: str,
        change_type: str = "modification",
        lines_changed: int = 0,
        has_security_finding: bool = False,
    ) -> ChangeClassification:
        risk_factors: list[str] = []
        max_level = "low"
        max_approvers = 0
        affected_contracts: list[str] = []
        affected_public = False

        for pattern in CONTRACT_PATTERNS:
            if pattern in file_path:
                risk_factors.append("contract_change")
                affected_contracts.append(pattern.strip("/"))
                break

        for pattern in PUBLIC_API_PATTERNS:
            if pattern in file_path:
                risk_factors.append("public_api_change")
                affected_public = True
                break

        if has_security_finding:
            risk_factors.append("security_pattern")

        basename = Path(file_path).name
        for pattern in CONFIG_PATTERNS:
            if pattern in file_path or basename == pattern:
                risk_factors.append("config_change")
                break

        if basename in DEPENDENCY_FILES:
            risk_factors.append("dependency_change")

        if change_type == "deletion" and any(p in file_path for p in TEST_PATTERNS):
            risk_factors.append("test_delete")

        if lines_changed > 200:
            risk_factors.append("large_change")

        for pattern in RUNTIME_PATTERNS:
            if pattern in file_path:
                risk_factors.append("runtime_change")
                break

        if not risk_factors:
            risk_factors.append("routine")

        for factor in risk_factors:
            rf = RISK_FACTORS.get(factor, {})
            level = rf.get("level", "low")
            approvers = rf.get("approvers", 0)
            if self._level_priority(level) > self._level_priority(max_level):
                max_level = level
                max_approvers = approvers
            elif self._level_priority(level) == self._level_priority(max_level):
                max_approvers = max(max_approvers, approvers)

        requires_approval = (
            max_level in ("critical", "high", "medium") and max_approvers > 0
        )

        return ChangeClassification(
            change_id=self._change_id(file_path, change_type),
            file_path=file_path,
            change_type=change_type,
            risk_level=max_level,
            risk_factors=risk_factors,
            affected_contracts=affected_contracts,
            affected_public_api=affected_public,
            requires_approval=requires_approval,
            approvers_required=max_approvers,
        )

    def evaluate(
        self,
        changes: list[dict[str, Any]],
        policy_passed: bool = True,
        contract_verified: bool = True,
    ) -> ApprovalDecision:
        classifications: list[ChangeClassification] = []
        blocked_reasons: list[str] = []
        approval_requirements: list[str] = []
        max_risk = "low"
        total_approvers = 0

        for change in changes:
            classification = self.classify_change(
                file_path=change.get("file_path", ""),
                change_type=change.get("change_type", "modification"),
                lines_changed=change.get("lines_changed", 0),
                has_security_finding=change.get("has_security_finding", False),
            )
            classifications.append(classification)

            if self._level_priority(classification.risk_level) > self._level_priority(
                max_risk
            ):
                max_risk = classification.risk_level

            if classification.requires_approval:
                total_approvers = max(
                    total_approvers, classification.approvers_required
                )
                for factor in classification.risk_factors:
                    rf = RISK_FACTORS.get(factor, {})
                    if rf:
                        approval_requirements.append(
                            f"{factor}: {rf.get('description', '')} "
                            f"({rf.get('approvers', 0)} approver(s) required)"
                        )

        if not policy_passed:
            blocked_reasons.append("Policy check failed — security findings detected")
        if not contract_verified:
            blocked_reasons.append(
                "Contract verification failed — mode contract violations detected"
            )

        approved = not blocked_reasons and max_risk != "critical"

        decision = ApprovalDecision(
            run_id=self.run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            changes=classifications,
            overall_risk=max_risk,
            approved=approved,
            blocked_reasons=blocked_reasons,
            approval_requirements=approval_requirements,
        )
        decision.integrity_hash = self._compute_hash(decision)
        return decision

    def evaluate_from_git_diff(
        self,
        diff_text: str,
        policy_passed: bool = True,
        contract_verified: bool = True,
    ) -> ApprovalDecision:
        changes = self._parse_diff(diff_text)
        return self.evaluate(
            changes, policy_passed=policy_passed, contract_verified=contract_verified
        )

    def _parse_diff(self, diff_text: str) -> list[dict[str, Any]]:
        changes: list[dict[str, Any]] = []
        current_file = None
        change_type = "modification"
        lines_changed = 0

        for line in diff_text.splitlines():
            if line.startswith("diff --git"):
                if current_file:
                    changes.append(
                        {
                            "file_path": current_file,
                            "change_type": change_type,
                            "lines_changed": lines_changed,
                        }
                    )
                parts = line.split()
                if len(parts) >= 4:
                    current_file = parts[-1][2:]
                    change_type = "modification"
                    lines_changed = 0
            elif line.startswith("new file"):
                change_type = "addition"
            elif line.startswith("deleted file"):
                change_type = "deletion"
            elif line.startswith("rename"):
                change_type = "rename"
            elif line.startswith("+") and not line.startswith("+++"):
                lines_changed += 1
            elif line.startswith("-") and not line.startswith("---"):
                lines_changed += 1

        if current_file:
            changes.append(
                {
                    "file_path": current_file,
                    "change_type": change_type,
                    "lines_changed": lines_changed,
                }
            )

        return changes

    def _level_priority(self, level: str) -> int:
        return {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(level, 0)

    def _change_id(self, file_path: str, change_type: str) -> str:
        raw = f"{change_type}:{file_path}"
        return f"chg-{hashlib.sha256(raw.encode()).hexdigest()[:12]}"

    def _compute_hash(self, decision: ApprovalDecision) -> str:
        content = json.dumps(
            {
                "run_id": decision.run_id,
                "changes": [asdict(c) for c in decision.changes],
                "overall_risk": decision.overall_risk,
            },
            sort_keys=True,
            default=str,
        )
        return f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"


def evaluate_changes(
    changes: list[dict[str, Any]],
    run_id: str | None = None,
    policy_passed: bool = True,
    contract_verified: bool = True,
) -> dict[str, Any]:
    gate = ApprovalGate(run_id=run_id)
    decision = gate.evaluate(
        changes, policy_passed=policy_passed, contract_verified=contract_verified
    )
    return decision.to_dict()


if __name__ == "__main__":
    import sys

    gate = ApprovalGate()

    if len(sys.argv) > 1:
        diff_path = Path(sys.argv[1])
        if diff_path.exists():
            diff_text = diff_path.read_text()
            decision = gate.evaluate_from_git_diff(diff_text)
        else:
            print(f"File not found: {sys.argv[1]}")
            sys.exit(1)
    else:
        sample_changes = [
            {
                "file_path": ".internal/specs/modes/explore.yaml",
                "change_type": "modification",
                "lines_changed": 15,
            },
            {
                "file_path": "docs/README.md",
                "change_type": "modification",
                "lines_changed": 5,
            },
            {
                "file_path": "src/main.py",
                "change_type": "addition",
                "lines_changed": 50,
            },
        ]
        decision = gate.evaluate(sample_changes)
        decision = decision.to_dict()

    status = "APPROVED" if decision["approved"] else "BLOCKED"
    print(f"[{status}] Approval gate: {decision['run_id']}")
    print(f"  Overall risk: {decision['overall_risk']}")
    print(f"  Total changes: {decision['total_changes']}")
    print(f"  Blocked reasons: {decision['blocked_reasons']}")
    for req in decision["approval_requirements"]:
        print(f"  Requirement: {req}")

    sys.exit(0 if decision["approved"] else 1)
