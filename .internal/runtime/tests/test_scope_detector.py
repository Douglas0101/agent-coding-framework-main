"""Tests for Scope Detection Engine runtime."""

from __future__ import annotations

from pathlib import Path

import pytest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scope_detector import ScopeDetector, ScopeResult

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SPEC_PATH = REPO_ROOT / ".internal" / "specs" / "core" / "scope-detection-engine.yaml"
ALGO_MAP_PATH = (
    REPO_ROOT
    / ".internal"
    / "domains"
    / "ioi-gold-compiler"
    / "algorithm-selection-map.yaml"
)


@pytest.fixture
def detector():
    return ScopeDetector(spec_path=SPEC_PATH, algorithm_map_path=ALGO_MAP_PATH)


class TestScopeDetectorBasics:
    def test_file_exists(self):
        assert SPEC_PATH.exists()

    def test_algorithm_map_exists(self):
        assert ALGO_MAP_PATH.exists()

    def test_returns_scope_result(self, detector):
        result = detector.classify("Create a simple CRUD endpoint")
        assert isinstance(result, ScopeResult)
        assert result.tier in (
            "tier_1_universal",
            "tier_2_algorithmic",
            "tier_3_competitive",
        )
        assert result.profile in ("default_1x", "performance_2x")
        assert 0.0 <= result.confidence <= 1.0
        assert result.score >= 0.0
        assert isinstance(result.triggers_matched, list)
        assert isinstance(result.rationale, str)
        assert isinstance(result.anti_false_positive_checked, bool)


class TestTier1Classification:
    def test_crud_endpoint(self, detector):
        result = detector.classify("Create a REST API endpoint for user registration")
        assert result.tier == "tier_1_universal"
        assert result.profile == "default_1x"

    def test_refactor_task(self, detector):
        result = detector.classify("Refactor the authentication module to use JWT")
        assert result.tier == "tier_1_universal"

    def test_simple_feature(self, detector):
        result = detector.classify("Add a search filter to the dashboard")
        assert result.tier == "tier_1_universal"

    def test_worker_job(self, detector):
        result = detector.classify(
            "Create a background job to send email notifications"
        )
        assert result.tier == "tier_1_universal"

    def test_database_migration(self, detector):
        result = detector.classify("Add a migration to add email_verified column")
        assert result.tier == "tier_1_universal"

    def test_documentation_task(self, detector):
        result = detector.classify("Update the API documentation for v2 endpoints")
        assert result.tier == "tier_1_universal"

    def test_fast_api_non_technical(self, detector):
        result = detector.classify("Create a fast API endpoint for health check")
        assert result.tier == "tier_1_universal"
        assert result.anti_false_positive_checked is True

    def test_quick_pagination(self, detector):
        result = detector.classify("Add quick pagination to the user list")
        assert result.tier == "tier_1_universal"
        assert result.anti_false_positive_checked is True

    def test_substring_false_positive_rabbitmq(self, detector):
        result = detector.classify("Integrate RabbitMQ for async jobs")
        assert result.tier == "tier_1_universal"

    def test_substring_false_positive_pdfs(self, detector):
        result = detector.classify("Generate PDFs for invoices")
        assert result.tier == "tier_1_universal"

    def test_ambiguous_bit_without_technical_context(self, detector):
        result = detector.classify("Adjust a bit of UI spacing in the dashboard")
        assert result.tier == "tier_1_universal"


class TestTier2Classification:
    def test_range_query_large_n(self, detector):
        result = detector.classify("Range minimum query with updates, n=200000")
        assert result.tier == "tier_2_algorithmic"
        assert result.profile == "performance_2x"

    def test_graph_shortest_path(self, detector):
        result = detector.classify("Find shortest path in graph with 150000 nodes")
        assert result.tier == "tier_2_algorithmic"
        assert result.profile == "performance_2x"

    def test_large_queries(self, detector):
        result = detector.classify("Process 200000 queries on an array efficiently")
        assert result.tier in ("tier_2_algorithmic", "tier_3_competitive")
        assert result.profile == "performance_2x"

    def test_optimization_request(self, detector):
        result = detector.classify(
            "Optimize this range query solution for performance, n=100000"
        )
        assert result.profile == "performance_2x"

    def test_graph_scc(self, detector):
        result = detector.classify(
            "Find strongly connected components in a directed graph"
        )
        assert result.profile == "performance_2x"

    def test_structural_patterns_combo(self, detector):
        result = detector.classify("Range query with subtree query on a tree structure")
        assert result.profile == "performance_2x"

    def test_power_notation(self, detector):
        result = detector.classify("Process array of size 10^5 with range queries")
        assert result.profile == "performance_2x"

    def test_bit_with_technical_context(self, detector):
        result = detector.classify("Use BIT for prefix sums with updates")
        assert result.tier == "tier_2_algorithmic"


class TestTier3Classification:
    def test_link_cut_tree(self, detector):
        result = detector.classify(
            "Dynamic forest with link/cut operations and path maximum query"
        )
        assert result.tier == "tier_3_competitive"
        assert result.profile == "performance_2x"

    def test_eertree(self, detector):
        result = detector.classify(
            "Count distinct palindromic substrings using eertree"
        )
        assert result.tier == "tier_3_competitive"

    def test_suffix_automaton(self, detector):
        result = detector.classify(
            "Build a suffix automaton for longest common substring"
        )
        assert result.tier == "tier_3_competitive"

    def test_ioi_explicit(self, detector):
        result = detector.classify(
            "IOI-grade problem: dynamic tree with path queries, n=10^5"
        )
        assert result.tier == "tier_3_competitive"

    def test_icpc_explicit(self, detector):
        result = detector.classify(
            "ICPC problem: min cost max flow with negative edges"
        )
        assert result.tier == "tier_3_competitive"

    def test_wavelet_tree(self, detector):
        result = detector.classify("K-th smallest in range using wavelet tree")
        assert result.tier == "tier_3_competitive"

    def test_centroid_decomposition(self, detector):
        result = detector.classify(
            "Count paths of length K using centroid decomposition"
        )
        assert result.tier == "tier_3_competitive"


class TestConstraintExtraction:
    def test_extract_n_constraint(self, detector):
        result = detector.classify("Array with n=200000 elements")
        assert "n" in result.constraints_found
        assert result.constraints_found["n"] >= 200000

    def test_extract_q_constraint(self, detector):
        result = detector.classify("Process q=150000 queries")
        assert "q" in result.constraints_found

    def test_extract_power_notation(self, detector):
        result = detector.classify("Size 10^5 array")
        assert "n" in result.constraints_found
        assert result.constraints_found["n"] >= 100000

    def test_small_constraints_no_escalation(self, detector):
        result = detector.classify("Array with n=100 elements")
        assert "n" not in result.constraints_found


class TestAlgorithmSuggestion:
    def test_suggests_segment_tree(self, detector):
        result = detector.classify("Range minimum query with updates, n=200000")
        assert result.suggested_algorithm is not None

    def test_suggests_for_graph(self, detector):
        result = detector.classify(
            "Shortest path in weighted graph with non-negative edges"
        )
        assert result.suggested_algorithm is not None

    def test_no_suggestion_for_tier1(self, detector):
        result = detector.classify("Create user registration endpoint")
        assert result.suggested_algorithm is None


class TestConfidenceScoring:
    def test_high_confidence_tier1(self, detector):
        result = detector.classify("Simple CRUD endpoint")
        assert result.confidence >= 0.7

    def test_high_confidence_tier3(self, detector):
        result = detector.classify("IOI-grade link cut tree problem with n=10^5")
        assert result.confidence >= 0.5

    def test_confidence_in_range(self, detector):
        tasks = [
            "Create API endpoint",
            "Range query with n=200000",
            "Dynamic tree with link cut",
            "Simple list pagination",
            "Graph shortest path 100k nodes",
        ]
        for task in tasks:
            result = detector.classify(task)
            assert 0.0 <= result.confidence <= 1.0


class TestAntiFalsePositive:
    def test_fast_in_non_technical_context(self, detector):
        result = detector.classify("Create a fast endpoint for health check")
        assert result.anti_false_positive_checked is True

    def test_performance_keyword_prevents_fp(self, detector):
        result = detector.classify(
            "Fast performance optimization for range query, n=100000"
        )
        assert result.anti_false_positive_checked is False
        assert result.profile == "performance_2x"

    def test_crud_with_no_constraints(self, detector):
        result = detector.classify("Create REST API for user CRUD")
        assert result.anti_false_positive_checked is True
        assert result.tier == "tier_1_universal"

    def test_anti_false_positive_blocks_simple_api_escalation(self, detector):
        result = detector.classify("Create a simple API for user management")
        assert result.anti_false_positive_checked is True
        assert result.tier == "tier_1_universal"


class TestRationale:
    def test_rationale_not_empty(self, detector):
        result = detector.classify("Range query with n=200000")
        assert len(result.rationale) > 0

    def test_rationale_mentions_tier(self, detector):
        result = detector.classify("Simple CRUD")
        assert "Tier 1" in result.rationale or "tier_1" in result.rationale.lower()

    def test_rationale_for_tier3(self, detector):
        result = detector.classify("LCT for dynamic tree, n=10^5")
        assert "Tier 3" in result.rationale or "tier_3" in result.rationale.lower()
