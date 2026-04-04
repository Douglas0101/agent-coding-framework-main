"""Tests for the v2 skills."""

from __future__ import annotations

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestRepoTopologyMap:
    def test_map_produces_report(self):
        from skills.repo_topology_map import RepoTopologyMapper

        mapper = RepoTopologyMapper(run_id="test-topo-001")
        report = mapper.map()
        assert report.total_files > 0
        assert report.total_dirs > 0
        assert len(report.modules) > 0
        assert report.integrity_hash.startswith("sha256:")

    def test_map_function_returns_dict(self):
        from skills.repo_topology_map import map_topology

        result = map_topology(run_id="test-topo-002")
        assert "total_files" in result
        assert "modules" in result
        assert "dependency_graph" in result

    def test_module_classification(self):
        from skills.repo_topology_map import RepoTopologyMapper

        mapper = RepoTopologyMapper()
        assert mapper._classify_module(".internal/specs/modes/explore.yaml") == "core"
        assert (
            mapper._classify_module(".internal/runtime/contract_verifier.py")
            == "runtime"
        )
        assert (
            mapper._classify_module(".internal/tests/test_mode_contracts.py") == "test"
        )
        assert mapper._classify_module("docs/README.md") == "doc"
        assert mapper._classify_module(".github/workflows/ci.yml") == "config"
        assert mapper._classify_module("src/main.py") == "other"

    def test_ignore_patterns(self):
        from skills.repo_topology_map import RepoTopologyMapper

        mapper = RepoTopologyMapper()
        assert mapper._is_ignored(".git/config")
        assert mapper._is_ignored("__pycache__/module.pyc")
        assert not mapper._is_ignored("src/main.py")


class TestContractDriftAudit:
    def test_audit_no_drift(self):
        from skills.contract_drift_audit import ContractDriftAuditor

        auditor = ContractDriftAuditor(run_id="test-drift-001")
        report = auditor.audit()
        assert report.modes_checked == 4
        assert report.configs_checked == 2
        assert report.integrity_hash.startswith("sha256:")

    def test_audit_function_returns_dict(self):
        from skills.contract_drift_audit import audit_drift

        result = audit_drift(run_id="test-drift-002")
        assert "has_drift" in result
        assert "findings" in result
        assert "modes_checked" in result

    def test_handoff_target_validation(self):
        from skills.contract_drift_audit import ContractDriftAuditor

        auditor = ContractDriftAuditor(run_id="test-drift-003")
        auditor._check_cross_mode_handoff_drift()
        all_targets_valid = all(f.category != "schema_drift" for f in auditor.findings)
        assert all_targets_valid

    def test_version_format_validation(self):
        from skills.contract_drift_audit import ContractDriftAuditor

        auditor = ContractDriftAuditor(run_id="test-drift-004")
        auditor._check_version_drift()
        all_versions_valid = all(
            f.category != "version_drift" for f in auditor.findings
        )
        assert all_versions_valid


class TestExplicitPlanner:
    def test_plan_explore_and_code(self):
        from skills.explicit_planner import ExplicitPlanner

        planner = ExplicitPlanner(run_id="test-plan-001")
        plan = planner.plan("Explore the codebase and implement new feature")
        assert plan.is_valid
        assert len(plan.steps) >= 2
        assert len(plan.dependencies) >= 1
        assert plan.integrity_hash.startswith("sha256:")

    def test_plan_review_only(self):
        from skills.explicit_planner import ExplicitPlanner

        planner = ExplicitPlanner(run_id="test-plan-002")
        plan = planner.plan("Review the recent changes")
        assert plan.is_valid
        assert len(plan.steps) >= 1
        assert plan.steps[0].mode == "reviewer"

    def test_plan_budget_conservation(self):
        from skills.explicit_planner import ExplicitPlanner

        planner = ExplicitPlanner(run_id="test-plan-003")
        parent_budget = {
            "max_input_tokens": 16000,
            "max_output_tokens": 24000,
            "max_iterations": 20,
        }
        plan = planner.plan("Implement feature", parent_budget=parent_budget)
        for key in parent_budget:
            total = sum(
                step_budget.get(key, 0)
                for step_budget in plan.budget_allocation.values()
            )
            assert total <= parent_budget[key]

    def test_plan_risk_assessment(self):
        from skills.explicit_planner import ExplicitPlanner

        planner = ExplicitPlanner(run_id="test-plan-004")
        plan = planner.plan("Simple task")
        assert "risk_level" in plan.risk_assessment
        assert "risk_factors" in plan.risk_assessment

    def test_plan_function_returns_dict(self):
        from skills.explicit_planner import create_plan

        result = create_plan("Test task", run_id="test-plan-005")
        assert "plan_id" in result
        assert "is_valid" in result
        assert "steps" in result
        assert "budget_allocation" in result

    def test_plan_with_constraints(self):
        from skills.explicit_planner import ExplicitPlanner

        planner = ExplicitPlanner(run_id="test-plan-006")
        plan = planner.plan(
            "Implement security fix",
            constraints=["security-critical", "contract-change"],
        )
        assert plan.risk_assessment["risk_level"] == "high"


class TestDependencySurface:
    def test_analyze_produces_report(self):
        from skills.dependency_surface import DependencySurfaceAnalyzer

        analyzer = DependencySurfaceAnalyzer(run_id="test-dep-001")
        report = analyzer.analyze()
        assert report.total_nodes > 0
        assert report.integrity_hash.startswith("sha256:")

    def test_detects_external_packages(self):
        from skills.dependency_surface import DependencySurfaceAnalyzer

        analyzer = DependencySurfaceAnalyzer(run_id="test-dep-002")
        report = analyzer.analyze()
        ext_names = [p.name for p in report.external_packages]
        assert "yaml" in ext_names

    def test_detects_stdlib_deps(self):
        from skills.dependency_surface import DependencySurfaceAnalyzer

        analyzer = DependencySurfaceAnalyzer(run_id="test-dep-003")
        report = analyzer.analyze()
        assert report.stdlib_deps > 0

    def test_blast_radius_computed(self):
        from skills.dependency_surface import DependencySurfaceAnalyzer

        analyzer = DependencySurfaceAnalyzer(run_id="test-dep-004")
        report = analyzer.analyze()
        assert isinstance(report.blast_radius, dict)

    def test_coupling_metrics_computed(self):
        from skills.dependency_surface import DependencySurfaceAnalyzer

        analyzer = DependencySurfaceAnalyzer(run_id="test-dep-005")
        report = analyzer.analyze()
        assert isinstance(report.coupling, dict)

    def test_report_to_dict_structure(self):
        from skills.dependency_surface import DependencySurfaceAnalyzer

        analyzer = DependencySurfaceAnalyzer(run_id="test-dep-006")
        report = analyzer.analyze()
        d = report.to_dict()
        required_keys = {
            "run_id",
            "timestamp",
            "total_nodes",
            "internal_deps",
            "external_deps",
            "stdlib_deps",
            "circular_dependencies",
            "coupling",
            "nodes",
            "external_packages",
            "blast_radius",
            "has_critical_issues",
            "integrity_hash",
        }
        assert required_keys.issubset(d.keys())


class TestChangeImpactDeep:
    def test_core_contract_change_critical(self):
        from skills.change_impact_deep import ChangeImpactAnalyzer

        analyzer = ChangeImpactAnalyzer(run_id="test-impact-001")
        report = analyzer.analyze(
            changed_files=[".internal/specs/core/orchestration-contract.yaml"],
            change_description="Core contract change",
        )
        assert report.overall_risk == "critical"
        assert report.requires_review is True
        assert report.requires_migration is True

    def test_skill_change_medium(self):
        from skills.change_impact_deep import ChangeImpactAnalyzer

        analyzer = ChangeImpactAnalyzer(run_id="test-impact-002")
        report = analyzer.analyze(
            changed_files=[".internal/skills/repo_topology_map.py"],
            change_description="Update skill",
        )
        assert any(f.category == "skill_affected" for f in report.findings)

    def test_runtime_change_high(self):
        from skills.change_impact_deep import ChangeImpactAnalyzer

        analyzer = ChangeImpactAnalyzer(run_id="test-impact-003")
        report = analyzer.analyze(
            changed_files=[".internal/runtime/contract_verifier.py"],
            change_description="Update runtime",
        )
        assert any(f.category == "runtime_affected" for f in report.findings)

    def test_no_changes_low_risk(self):
        from skills.change_impact_deep import ChangeImpactAnalyzer

        analyzer = ChangeImpactAnalyzer(run_id="test-impact-004")
        report = analyzer.analyze(
            changed_files=["docs/README.md"],
            change_description="Doc update",
        )
        assert report.overall_risk == "low"
        assert report.requires_review is False

    def test_with_dependency_surface(self):
        from skills.change_impact_deep import ChangeImpactAnalyzer

        analyzer = ChangeImpactAnalyzer(run_id="test-impact-005")
        dep_surface = {
            "blast_radius": {
                ".internal.runtime.contract_verifier": ["module_a", "module_b"]
            },
            "circular_dependencies": [],
        }
        report = analyzer.analyze(
            changed_files=[".internal/runtime/contract_verifier.py"],
            change_description="Runtime change with dep surface",
            dependency_surface=dep_surface,
        )
        assert len(report.risk_propagation) > 0

    def test_report_to_dict_structure(self):
        from skills.change_impact_deep import ChangeImpactAnalyzer

        analyzer = ChangeImpactAnalyzer(run_id="test-impact-006")
        report = analyzer.analyze(
            changed_files=[".internal/specs/modes/explore.yaml"],
            change_description="Test",
        )
        d = report.to_dict()
        required_keys = {
            "run_id",
            "timestamp",
            "change_description",
            "changed_files",
            "findings",
            "risk_propagation",
            "migration_requirements",
            "overall_risk",
            "requires_review",
            "requires_migration",
            "integrity_hash",
        }
        assert required_keys.issubset(d.keys())


class TestPolicyGatePlus:
    def test_gate_passes_clean(self):
        from skills.policy_gate_plus import PolicyGatePlus

        gate = PolicyGatePlus(run_id="test-gate-001")
        report = gate.run_full_gate(review_scope="full")
        assert report.gate_status in ("pass", "conditional_pass")
        assert report.can_proceed is True
        assert report.total_checks > 0

    def test_gate_with_policy_findings(self):
        from skills.policy_gate_plus import PolicyGatePlus

        gate = PolicyGatePlus(run_id="test-gate-002")
        report = gate.run_full_gate(
            review_scope="full",
            policy_findings=[{"severity": "critical"}],
        )
        assert report.gate_status == "fail"
        assert report.can_proceed is False

    def test_gate_with_drift_findings(self):
        from skills.policy_gate_plus import PolicyGatePlus

        gate = PolicyGatePlus(run_id="test-gate-003")
        report = gate.run_full_gate(
            review_scope="full",
            drift_findings=[{"severity": "high"}],
        )
        assert any(c.name == "drift_detection" for c in report.checks)

    def test_report_to_dict_structure(self):
        from skills.policy_gate_plus import PolicyGatePlus

        gate = PolicyGatePlus(run_id="test-gate-004")
        report = gate.run_full_gate(review_scope="full")
        d = report.to_dict()
        required_keys = {
            "run_id",
            "timestamp",
            "review_scope",
            "gate_status",
            "can_proceed",
            "total_checks",
            "passed",
            "failed",
            "warnings",
            "skipped",
            "checks",
            "integrity_hash",
        }
        assert required_keys.issubset(d.keys())


class TestBoundaryLeakDetector:
    def test_scan_produces_report(self):
        from skills.boundary_leak_detector import BoundaryLeakDetector

        detector = BoundaryLeakDetector(run_id="test-boundary-001")
        report = detector.scan()
        assert report.files_scanned > 0
        assert report.integrity_hash.startswith("sha256:")

    def test_report_to_dict_structure(self):
        from skills.boundary_leak_detector import BoundaryLeakDetector

        detector = BoundaryLeakDetector(run_id="test-boundary-002")
        report = detector.scan()
        d = report.to_dict()
        required_keys = {
            "run_id",
            "timestamp",
            "files_scanned",
            "has_leaks",
            "has_critical_leaks",
            "total_leaks",
            "categories",
            "leaks",
            "integrity_hash",
        }
        assert required_keys.issubset(d.keys())


class TestBudgetAllocator:
    def test_allocation_valid(self):
        from skills.budget_allocator import BudgetAllocator

        allocator = BudgetAllocator(run_id="test-budget-001")
        parent_budget = {
            "max_input_tokens": 32000,
            "max_output_tokens": 48000,
            "max_iterations": 50,
        }
        allocator.set_parent_budget(parent_budget)
        children = [
            {
                "step_id": "step-01",
                "mode": "explore",
                "budget": {
                    "max_input_tokens": 8000,
                    "max_output_tokens": 12000,
                    "max_iterations": 15,
                },
            },
            {
                "step_id": "step-02",
                "mode": "autocoder",
                "budget": {
                    "max_input_tokens": 16000,
                    "max_output_tokens": 24000,
                    "max_iterations": 25,
                },
            },
        ]
        report = allocator.allocate_children(children)
        assert report.is_valid is True
        assert len(report.conservation_violations) == 0

    def test_allocation_violated(self):
        from skills.budget_allocator import BudgetAllocator

        allocator = BudgetAllocator(run_id="test-budget-002")
        parent_budget = {
            "max_input_tokens": 10000,
        }
        allocator.set_parent_budget(parent_budget)
        children = [
            {
                "step_id": "step-01",
                "mode": "explore",
                "budget": {"max_input_tokens": 8000},
            },
            {
                "step_id": "step-02",
                "mode": "autocoder",
                "budget": {"max_input_tokens": 8000},
            },
        ]
        report = allocator.allocate_children(children)
        assert report.is_valid is False
        assert len(report.conservation_violations) > 0

    def test_consume_budget(self):
        from skills.budget_allocator import BudgetAllocator

        allocator = BudgetAllocator(run_id="test-budget-003")
        allocator.set_parent_budget({"max_input_tokens": 32000})
        children = [
            {
                "step_id": "step-01",
                "mode": "explore",
                "budget": {"max_input_tokens": 8000},
            },
        ]
        allocator.allocate_children(children)
        success, msg = allocator.consume("step-01", "max_input_tokens", 1000)
        assert success is True
        status = allocator.get_status("step-01")
        assert status is not None
        assert status["remaining"]["max_input_tokens"] == 7000


class TestHandoffCompressor:
    def test_compress_summary(self):
        from skills.handoff_compressor import HandoffCompressor

        compressor = HandoffCompressor(run_id="test-compress-001")
        content = "\n".join([f"Line {i}" for i in range(50)])
        payload = compressor.compress(content, mode="summary")
        assert payload.compression_ratio < 1.0
        assert payload.compression_mode == "summary"

    def test_compress_none(self):
        from skills.handoff_compressor import HandoffCompressor

        compressor = HandoffCompressor(run_id="test-compress-002")
        content = "Short content"
        payload = compressor.compress(content, mode="none")
        assert payload.compression_ratio == 1.0

    def test_compress_summary_with_refs(self):
        from skills.handoff_compressor import HandoffCompressor

        compressor = HandoffCompressor(run_id="test-compress-003")
        content = "\n".join([f"Line {i}" for i in range(50)])
        payload = compressor.compress(content, mode="summary+refs", refs=["ref-001"])
        assert len(payload.refs) == 1

    def test_rehydrate_summary(self):
        from skills.handoff_compressor import HandoffCompressor

        compressor = HandoffCompressor(run_id="test-compress-004")
        content = "\n".join([f"Line {i}" for i in range(50)])
        payload = compressor.compress(content, mode="summary")
        result = compressor.rehydrate(payload)
        assert result.success is True

    def test_rehydrate_with_refs(self):
        from skills.handoff_compressor import HandoffCompressor

        compressor = HandoffCompressor(run_id="test-compress-005")
        content = "\n".join([f"Line {i}" for i in range(50)])
        payload = compressor.compress(content, mode="summary+refs", refs=["ref-001"])
        result = compressor.rehydrate(
            payload, ref_resolver={"ref-001": "Evidence data"}
        )
        assert result.success is True
        assert len(result.resolved_refs) == 1


class TestMemoryCuratorV2:
    def test_store_and_retrieve(self):
        from skills.memory_curator_v2 import MemoryCuratorV2

        curator = MemoryCuratorV2(run_id="test-memory-001")
        entry = curator.store(
            tier="operational_context",
            content="Test content",
            producer="test",
        )
        assert entry is not None
        retrieved = curator.retrieve("operational_context", entry.entry_id)
        assert retrieved is not None
        assert retrieved.content == "Test content"

    def test_compress_tier(self):
        from skills.memory_curator_v2 import MemoryCuratorV2

        curator = MemoryCuratorV2(run_id="test-memory-002")
        for i in range(10):
            curator.store(
                tier="operational_context",
                content=f"Content {i}",
                producer="test",
            )
        report = curator.generate_report()
        assert report.total_entries == 10

    def test_evidence_preservation(self):
        from skills.memory_curator_v2 import MemoryCuratorV2

        curator = MemoryCuratorV2(run_id="test-memory-003")
        curator.store(
            tier="structural_memory",
            content="Important contract info",
            producer="system",
            compressible=False,
            evidence_refs=["evidence-001"],
        )
        refs = curator.get_evidence_refs()
        assert "evidence-001" in refs

    def test_report_to_dict_structure(self):
        from skills.memory_curator_v2 import MemoryCuratorV2

        curator = MemoryCuratorV2(run_id="test-memory-004")
        curator.store(
            tier="operational_context",
            content="Test",
            producer="test",
        )
        report = curator.generate_report()
        d = report.to_dict()
        required_keys = {
            "run_id",
            "timestamp",
            "total_entries",
            "total_size",
            "compressed_entries",
            "evidence_preserved",
            "tiers",
            "integrity_hash",
        }
        assert required_keys.issubset(d.keys())


class TestMetricsCollector:
    def test_record_and_kpi_report(self):
        from runtime.metrics_collector import KPITracker, RunMetrics

        tracker = KPITracker(run_id="test-kpi-001")
        tracker.record_run(
            RunMetrics(
                run_id="run-001",
                timestamp="2026-04-04T00:00:00Z",
                mode="explore",
                input_tokens=8000,
                output_tokens=4000,
                context_tokens=16000,
                handoff_count=2,
                handoff_tokens=3000,
                verifier_passed=True,
                compression_ratio=0.45,
                status="success",
            )
        )
        report = tracker.generate_kpi_report()
        assert report.total_runs == 1
        assert report.avg_tokens_per_run > 0
        assert report.verifier_pass_rate == 1.0

    def test_multiple_runs_kpi(self):
        from runtime.metrics_collector import KPITracker, RunMetrics

        tracker = KPITracker(run_id="test-kpi-002")
        for i, mode in enumerate(["explore", "reviewer", "autocoder"]):
            tracker.record_run(
                RunMetrics(
                    run_id=f"run-{i:03d}",
                    timestamp="2026-04-04T00:00:00Z",
                    mode=mode,
                    input_tokens=8000 * (i + 1),
                    output_tokens=4000 * (i + 1),
                    context_tokens=16000 * (i + 1),
                    handoff_count=i + 1,
                    handoff_tokens=3000 * (i + 1),
                    verifier_passed=i < 2,
                    compression_ratio=0.45 + i * 0.05,
                    status="success" if i < 2 else "partial_success",
                )
            )
        report = tracker.generate_kpi_report()
        assert report.total_runs == 3
        assert report.verifier_pass_rate < 1.0
        assert report.partial_success_rate > 0
        assert len(report.cost_by_mode) == 3

    def test_track_kpis_function(self):
        from runtime.metrics_collector import track_kpis

        result = track_kpis(
            run_metrics=[
                {
                    "run_id": "run-001",
                    "mode": "explore",
                    "input_tokens": 8000,
                    "output_tokens": 4000,
                    "context_tokens": 16000,
                    "handoff_count": 2,
                    "handoff_tokens": 3000,
                    "verifier_passed": True,
                    "compression_ratio": 0.45,
                    "status": "success",
                },
            ],
            run_id="test-kpi-003",
        )
        assert result["total_runs"] == 1
        assert result["run_id"] == "test-kpi-003"
