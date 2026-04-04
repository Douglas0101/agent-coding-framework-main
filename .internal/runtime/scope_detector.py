"""Scope Detection Engine — Runtime implementation.

Classifies tasks into operational tiers (Tier 1/2/3) and determines
the appropriate execution profile (default_1x or performance_2x)
based on semantic analysis of task input, constraints, and context.

Spec: .internal/specs/core/scope-detection-engine.yaml
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SPEC_PATH = REPO_ROOT / ".internal" / "specs" / "core" / "scope-detection-engine.yaml"
ALGORITHM_MAP_PATH = (
    REPO_ROOT
    / ".internal"
    / "domains"
    / "ioi-gold-compiler"
    / "algorithm-selection-map.yaml"
)

TIER_3_PATTERNS = {
    "link_cut_tree",
    "wavelet_tree",
    "eertree",
    "persistent_data_structures",
    "min_cost_max_flow_potentials",
    "centroid_decomposition",
    "suffix_automaton",
    "simulated_annealing",
}

TIER_3_KEYWORDS = {
    "link cut",
    "link-cut",
    "lct",
    "wavelet",
    "eertree",
    "palindrome tree",
    "suffix automaton",
    "suffix array",
    "centroid decomposition",
    "persistent segment",
    "min cost max flow",
    "mcmf",
    "simulated annealing",
    "dynamic tree",
    "online dynamic",
}

AMBIGUOUS_KEYWORDS = {
    "bit",
    "bridge",
    "heap",
    "prim",
}

TECHNICAL_CONTEXT_PATTERN = re.compile(
    r"\b(algorithm|array|component|complexity|constraint|dynamic|edge|edges|flow|"
    r"forest|graph|latency|node|nodes|offline|online|optimi(?:s|z)e|palindrome|"
    r"path|performance|prefix|query|queries|range|shortest|substring|suffix|sum|"
    r"throughput|traversal|tree|update|updates|weighted)\b"
)

ALGORITHM_TIER_OVERRIDES = {
    "segment tree": "tier_2",
    "fenwick tree": "tier_2",
    "bit": "tier_2",
    "binary indexed": "tier_2",
    "dijkstra": "tier_2",
    "bellman-ford": "tier_2",
    "spfa": "tier_2",
    "floyd-warshall": "tier_2",
    "topological sort": "tier_2",
    "bfs": "tier_2",
    "dfs": "tier_2",
    "tarjan": "tier_2",
    "scc": "tier_2",
    "articulation": "tier_2",
    "bridge": "tier_2",
    "kruskal": "tier_2",
    "prim": "tier_2",
    "dsu": "tier_2",
    "disjoint set": "tier_2",
    "union find": "tier_2",
    "lca": "tier_2",
    "lowest common ancestor": "tier_2",
    "sparse table": "tier_2",
    "rmq": "tier_2",
    "range minimum": "tier_2",
    "heap": "tier_2",
    "priority queue": "tier_2",
    "binary search": "tier_2",
    "binary indexed tree": "tier_2",
    "euler tour": "tier_2",
    "heavy light": "tier_2",
    "sliding window": "tier_2",
    "two pointers": "tier_2",
    "prefix sum": "tier_2",
    "difference array": "tier_2",
    "link cut": "tier_3",
    "link-cut": "tier_3",
    "link/cut": "tier_3",
    "link-cut tree": "tier_3",
    "link cut tree": "tier_3",
    "lct": "tier_3",
    "wavelet": "tier_3",
    "eertree": "tier_3",
    "palindrome tree": "tier_3",
    "suffix automaton": "tier_3",
    "suffix array": "tier_3",
    "persistent segment": "tier_3",
    "persistent tree": "tier_3",
    "centroid": "tier_3",
    "centroid decomposition": "tier_3",
    "min-cost max flow": "tier_3",
    "mcmf": "tier_3",
}


@dataclass
class ScopeResult:
    """Result of scope classification."""

    tier: str
    profile: str
    confidence: float
    score: float
    triggers_matched: list[str] = field(default_factory=list)
    rationale: str = ""
    anti_false_positive_checked: bool = False
    constraints_found: dict[str, int] = field(default_factory=dict)
    suggested_algorithm: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier,
            "profile": self.profile,
            "confidence": self.confidence,
            "score": self.score,
            "triggers_matched": self.triggers_matched,
            "rationale": self.rationale,
            "anti_false_positive_checked": self.anti_false_positive_checked,
            "constraints_found": self.constraints_found,
            "suggested_algorithm": self.suggested_algorithm,
        }


@dataclass
class _TriggerGroup:
    """Internal representation of a trigger group match."""

    name: str
    weight: float
    matched_keywords: list[str] = field(default_factory=list)
    raw_score: float = 0.0


class ScopeDetector:
    """Runtime scope detection engine.

    Reads configuration from scope-detection-engine.yaml and classifies
    task inputs into operational tiers.
    """

    def __init__(
        self, spec_path: Path | None = None, algorithm_map_path: Path | None = None
    ):
        self._spec_path = spec_path or SPEC_PATH
        self._algorithm_map_path = algorithm_map_path or ALGORITHM_MAP_PATH
        self._spec = self._load_spec()
        self._algorithm_map = self._load_algorithm_map()

    def _load_spec(self) -> dict:
        if not self._spec_path.exists():
            raise FileNotFoundError(
                f"Scope detection spec not found: {self._spec_path}"
            )
        return yaml.safe_load(self._spec_path.read_text(encoding="utf-8"))

    def _load_algorithm_map(self) -> list[dict]:
        if not self._algorithm_map_path.exists():
            return []
        data = yaml.safe_load(self._algorithm_map_path.read_text(encoding="utf-8"))
        return data.get("mappings", [])

    def classify(
        self,
        task_input: str,
        context: dict[str, Any] | None = None,
    ) -> ScopeResult:
        """Classify a task into an operational tier and execution profile.

        Args:
            task_input: The task description / prompt text.
            context: Optional additional context (e.g., file contents, constraints).

        Returns:
            ScopeResult with tier, profile, confidence, and rationale.
        """
        text = task_input.lower()
        full_text = text
        if context and "files_content" in context:
            for content in context["files_content"].values():
                full_text += "\n" + content.lower()

        triggers = self._spec.get("triggers", {})
        classification = self._spec.get("classification", {})
        scoring = self._spec.get("scoring", {})
        anti_fp_rules = self._spec.get("anti_false_positive", {}).get("rules", [])

        trigger_groups: list[_TriggerGroup] = []

        complexity = self._match_keywords(
            text, triggers.get("complexity_indicators", {})
        )
        if complexity.matched_keywords:
            trigger_groups.append(complexity)

        structural = self._match_keywords(text, triggers.get("structural_patterns", {}))
        if structural.matched_keywords:
            trigger_groups.append(structural)

        user_lang = self._match_keywords(text, triggers.get("user_language", {}))
        if user_lang.matched_keywords:
            trigger_groups.append(user_lang)

        constraints_cfg = triggers.get("constraints", {})
        constraint_matches = self._extract_constraints(text, constraints_cfg)
        constraint_trigger = _TriggerGroup(
            name="constraints",
            weight=constraints_cfg.get("weight", 2),
        )
        if constraint_matches:
            constraint_trigger.matched_keywords = list(constraint_matches.keys())
            constraint_trigger.raw_score = len(constraint_matches)
            trigger_groups.append(constraint_trigger)

        tier_3_keyword_matches = self._match_tier_3_keywords(text)
        if tier_3_keyword_matches:
            t3_trigger = _TriggerGroup(
                name="tier_3_indicators",
                weight=2.0,
                matched_keywords=tier_3_keyword_matches,
                raw_score=len(tier_3_keyword_matches),
            )
            trigger_groups.append(t3_trigger)

        score = self._compute_score(trigger_groups, scoring)
        anti_fp_checked = self._check_anti_false_positive(text, anti_fp_rules)

        tier = self._classify_tier(
            text,
            score,
            constraint_matches,
            structural,
            tier_3_keyword_matches,
            anti_fp_checked,
            classification,
        )
        profile = classification.get(tier, {}).get("profile", "default_1x")
        confidence_threshold = classification.get(tier, {}).get(
            "confidence_threshold", 0.0
        )
        confidence = self._compute_confidence(score, tier, confidence_threshold)

        triggers_matched = []
        for tg in trigger_groups:
            triggers_matched.extend(tg.matched_keywords)

        rationale = self._build_rationale(
            tier,
            score,
            triggers_matched,
            constraint_matches,
            structural,
            tier_3_keyword_matches,
            anti_fp_checked,
        )

        suggested_algo = None
        if tier in ("tier_2_algorithmic", "tier_3_competitive"):
            suggested_algo = self._suggest_algorithm(task_input, constraint_matches)

        return ScopeResult(
            tier=tier,
            profile=profile,
            confidence=confidence,
            score=score,
            triggers_matched=triggers_matched,
            rationale=rationale,
            anti_false_positive_checked=anti_fp_checked,
            constraints_found=constraint_matches,
            suggested_algorithm=suggested_algo,
        )

    def _match_keywords(self, text: str, trigger_cfg: dict) -> _TriggerGroup:
        keywords = trigger_cfg.get("keywords", [])
        weight = trigger_cfg.get("weight", 1.0)
        matched = []
        for kw in keywords:
            if self._contains_keyword(text, kw):
                matched.append(kw)
        raw = len(matched)
        return _TriggerGroup(
            name=trigger_cfg.get("name", "unknown"),
            weight=weight,
            matched_keywords=matched,
            raw_score=raw,
        )

    def _match_tier_3_keywords(self, text: str) -> list[str]:
        matched = []
        for kw in TIER_3_KEYWORDS:
            if self._contains_keyword(text, kw):
                matched.append(kw)
        return matched

    def _contains_keyword(self, text: str, keyword: str) -> bool:
        normalized_keyword = keyword.lower()
        escaped_keyword = re.escape(normalized_keyword).replace(r"\ ", r"\s+")
        prefix = r"\b" if normalized_keyword[:1].isalnum() else ""
        suffix = r"\b" if normalized_keyword[-1:].isalnum() else ""
        if not re.search(f"{prefix}{escaped_keyword}{suffix}", text):
            return False
        if normalized_keyword in AMBIGUOUS_KEYWORDS and not self._has_technical_context(
            text
        ):
            return False
        return True

    def _has_technical_context(self, text: str) -> bool:
        return TECHNICAL_CONTEXT_PATTERN.search(text) is not None

    def _extract_constraints(self, text: str, constraints_cfg: dict) -> dict[str, int]:
        """Extract numeric constraints (n, q, m) from task text."""
        result = {}
        threshold_n = constraints_cfg.get("max_n_for_escalation", 100000)
        threshold_q = constraints_cfg.get("max_q_for_escalation", 100000)
        threshold_m = constraints_cfg.get("max_m_for_escalation", 100000)

        patterns = [
            (r"(?:max[_\s]*)?n\s*[=:]\s*(\d+)", "n", threshold_n),
            (r"(?:max[_\s]*)?q\s*[=:]\s*(\d+)", "q", threshold_q),
            (r"(?:max[_\s]*)?m\s*[=:]\s*(\d+)", "m", threshold_m),
            (r"n\s*=\s*(\d+)", "n", threshold_n),
            (r"q\s*=\s*(\d+)", "q", threshold_q),
            (r"m\s*=\s*(\d+)", "m", threshold_m),
            (r"(\d+)\s*elements?", "n", threshold_n),
            (r"(\d+)\s*queries?", "q", threshold_q),
            (r"(\d+)\s*nodes?", "n", threshold_n),
            (r"(\d+)\s*edges?", "m", threshold_m),
            (r"(\d+)\s*vertices?", "n", threshold_n),
            (r"(\d+)\s*strings?", "n", threshold_n),
        ]

        power_patterns = [
            (r"10\^(\d+)", "n"),
            (r"10\*\*(\d+)", "n"),
        ]

        for pattern, var_name, threshold in patterns:
            for match in re.finditer(pattern, text):
                value = int(match.group(1))
                if value >= threshold:
                    result[var_name] = max(result.get(var_name, 0), value)

        for pattern, var_name in power_patterns:
            for match in re.finditer(pattern, text):
                exponent = int(match.group(1))
                value = 10**exponent
                threshold = threshold_n if var_name == "n" else threshold_q
                if value >= threshold:
                    result[var_name] = max(result.get(var_name, 0), value)

        return result

    def _compute_score(
        self, trigger_groups: list[_TriggerGroup], scoring: dict
    ) -> float:
        """Compute weighted score from matched trigger groups."""
        total = 0.0
        for tg in trigger_groups:
            total += tg.raw_score * tg.weight

        max_score = scoring.get("max_score", 10.0)
        return min(total, max_score)

    def _classify_tier(
        self,
        task_input: str,
        score: float,
        constraints: dict[str, int],
        structural: _TriggerGroup,
        tier_3_keywords: list[str],
        anti_false_positive: bool,
        classification: dict,
    ) -> str:
        """Determine the operational tier based on score and signals."""
        text_lower = task_input.lower()

        if anti_false_positive and not constraints and not tier_3_keywords:
            return "tier_1_universal"

        for algorithm, forced_tier in ALGORITHM_TIER_OVERRIDES.items():
            if self._contains_keyword(text_lower, algorithm):
                if forced_tier == "tier_2":
                    return "tier_2_algorithmic"
                elif forced_tier == "tier_3":
                    return "tier_3_competitive"

        escalation_2x = self._spec.get("scoring", {}).get(
            "escalation_threshold_2x", 3.0
        )
        escalation_t3 = self._spec.get("scoring", {}).get(
            "escalation_threshold_tier3", 5.0
        )

        has_large_constraints = any(v >= 100000 for v in constraints.values())
        has_tier_3_signals = len(tier_3_keywords) >= 1

        ioi_icpc_mentioned = any(
            kw in "".join(tier_3_keywords).lower()
            for kw in ("ioi", "icpc", "competitive")
        )

        if score >= escalation_t3 or has_tier_3_signals or ioi_icpc_mentioned:
            return "tier_3_competitive"

        if score >= escalation_2x or has_large_constraints:
            return "tier_2_algorithmic"

        if len(structural.matched_keywords) >= 2:
            return "tier_2_algorithmic"

        return "tier_1_universal"

    def _compute_confidence(self, score: float, tier: str, threshold: float) -> float:
        """Compute confidence score based on how far above threshold."""
        if tier == "tier_1_universal":
            if score == 0:
                return 1.0
            return max(0.0, 1.0 - (score / 3.0))

        max_score = self._spec.get("scoring", {}).get("max_score", 10.0)
        if threshold == 0:
            return 1.0

        ratio = score / max_score
        confidence = min(1.0, ratio * 1.5)
        return round(confidence, 3)

    def _check_anti_false_positive(self, text: str, rules: list[str]) -> bool:
        """Check whether anti-false-positive conditions apply."""
        fp_indicators = {
            "fast": r"\bfast\b",
            "quick": r"\bquick\b",
            "simple": r"\bsimple\b",
            "basic": r"\bbasic\b",
            "easy": r"\beasy\b",
        }

        for word, pattern in fp_indicators.items():
            if re.search(pattern, text):
                non_technical_context = not any(
                    kw in text
                    for kw in (
                        "optimize",
                        "performance",
                        "latency",
                        "throughput",
                        "constraint",
                        "algorithm",
                        "complexity",
                        "time limit",
                        "memory limit",
                        "graph",
                        "tree",
                        "range query",
                    )
                )
                if non_technical_context:
                    return True

        crud_patterns = [
            r"crud",
            r"create.*endpoint",
            r"rest.*api",
            r"simple.*api",
        ]
        for pattern in crud_patterns:
            if re.search(pattern, text):
                has_no_constraints = not any(
                    kw in text
                    for kw in ("10^", "100000", "200000", "n=", "q=", "time limit")
                )
                if has_no_constraints:
                    return True

        return False

    def _suggest_algorithm(
        self, task_input: str, constraints: dict[str, int]
    ) -> str | None:
        """Suggest an algorithm based on the task and the algorithm selection map."""
        text = task_input.lower()
        best_match = None
        best_score = 0

        for mapping in self._algorithm_map:
            pattern = mapping.get("pattern", "")
            description = mapping.get("description", "").lower()
            keywords = pattern.replace("_", " ").split() + description.split()

            match_count = sum(1 for kw in keywords if kw in text and len(kw) > 3)
            if match_count > best_score:
                best_score = match_count
                best_match = mapping.get("suggested")

        return best_match

    def _build_rationale(
        self,
        tier: str,
        score: float,
        triggers_matched: list[str],
        constraints: dict[str, int],
        structural: _TriggerGroup,
        tier_3_keywords: list[str],
        anti_false_positive: bool,
    ) -> str:
        """Build human-readable rationale for the classification decision."""
        parts = []

        if tier == "tier_1_universal":
            parts.append("Task classified as general software engineering (Tier 1).")
            parts.append("No significant algorithmic complexity signals detected.")
            parts.append("Standard engineering patterns are sufficient.")
        elif tier == "tier_2_algorithmic":
            parts.append("Task classified as algorithmic optimization (Tier 2).")
            if constraints:
                constraint_str = ", ".join(f"{k}={v}" for k, v in constraints.items())
                parts.append(f"Large constraints detected: {constraint_str}.")
            if structural.matched_keywords:
                parts.append(
                    f"Structural patterns matched: {', '.join(structural.matched_keywords)}."
                )
            parts.append(f"Weighted score: {score:.1f}.")
        elif tier == "tier_3_competitive":
            parts.append("Task classified as competitive/frontier (Tier 3).")
            if tier_3_keywords:
                parts.append(
                    f"Frontier indicators detected: {', '.join(tier_3_keywords)}."
                )
            if constraints:
                constraint_str = ", ".join(f"{k}={v}" for k, v in constraints.items())
                parts.append(f"Large constraints detected: {constraint_str}.")
            parts.append(f"Weighted score: {score:.1f}.")

        if triggers_matched:
            parts.append(f"Triggers: {', '.join(triggers_matched)}.")

        if anti_false_positive and tier == "tier_1_universal":
            parts.append("Anti-false-positive guard prevented unnecessary escalation.")

        return " ".join(parts)
