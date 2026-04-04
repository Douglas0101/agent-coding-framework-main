"""Structural Memory Loader — Runtime implementation.

Loads and provides access to persistent structural memory including:
- Project conventions
- Architectural decisions (ADRs)
- Algorithm pattern map
- Technique-specific pitfalls

Usage:
    from structural_memory_loader import StructuralMemoryLoader

    loader = StructuralMemoryLoader()
    pitfalls = loader.get_pitfalls_for_technique("segment_tree")
    conventions = loader.get_project_conventions()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STRUCTURAL_MEMORY_PATH = (
    REPO_ROOT / ".internal" / "domains" / "ioi-gold-compiler" / "structural-memory.yaml"
)


@dataclass
class TechniquePitfall:
    """Pitfall information for a specific technique."""

    technique: str
    pitfalls: list[str]


@dataclass
class ArchitecturalDecision:
    """An architectural decision record."""

    id: str
    decision: str
    rationale: str
    date: str
    status: str


@dataclass
class StructuralMemory:
    """Loaded structural memory data."""

    project_conventions: list[str] = field(default_factory=list)
    architectural_decisions: list[ArchitecturalDecision] = field(default_factory=list)
    algorithmic_patterns: dict[str, str] = field(default_factory=dict)
    technique_pitfalls: list[TechniquePitfall] = field(default_factory=list)


class StructuralMemoryLoader:
    """Loads and provides access to structural memory."""

    def __init__(self, memory_path: Path | None = None):
        self._memory_path = memory_path or STRUCTURAL_MEMORY_PATH
        self._memory: StructuralMemory | None = None
        self._load_memory()

    def _load_memory(self) -> None:
        """Load structural memory from YAML file."""
        if not self._memory_path.exists():
            self._memory = StructuralMemory()
            return

        data = yaml.safe_load(self._memory_path.read_text(encoding="utf-8"))

        conventions = data.get("project_conventions", {}).get("items", [])
        decisions = [
            ArchitecturalDecision(
                id=item.get("id", ""),
                decision=item.get("decision", ""),
                rationale=item.get("rationale", ""),
                date=item.get("date", ""),
                status=item.get("status", ""),
            )
            for item in data.get("architectural_decisions", {}).get("items", [])
        ]

        patterns = {}
        key_patterns = data.get("algorithmic_pattern_map", {}).get("key_patterns", [])
        for pattern in key_patterns:
            parts = pattern.split(" → ")
            if len(parts) == 2:
                patterns[parts[0].strip()] = parts[1].strip()

        pitfalls = []
        for item in data.get("pitfall_notes", {}).get("items", []):
            pitfalls.append(
                TechniquePitfall(
                    technique=item.get("technique", ""),
                    pitfalls=item.get("pitfalls", []),
                )
            )

        self._memory = StructuralMemory(
            project_conventions=conventions,
            architectural_decisions=decisions,
            algorithmic_patterns=patterns,
            technique_pitfalls=pitfalls,
        )

    def get_project_conventions(self) -> list[str]:
        """Get all project conventions."""
        return self._memory.project_conventions if self._memory else []

    def get_architectural_decisions(self) -> list[ArchitecturalDecision]:
        """Get all architectural decisions."""
        return self._memory.architectural_decisions if self._memory else []

    def get_algorithmic_pattern(self, problem_pattern: str) -> str | None:
        """Get the recommended algorithm for a problem pattern."""
        return (
            self._memory.algorithmic_patterns.get(problem_pattern)
            if self._memory
            else None
        )

    def get_pitfalls_for_technique(self, technique: str) -> list[str]:
        """Get pitfalls for a specific technique."""
        if not self._memory:
            return []
        for tp in self._memory.technique_pitfalls:
            if tp.technique.lower() == technique.lower():
                return tp.pitfalls
        return []

    def get_all_technique_pitfalls(self) -> dict[str, list[str]]:
        """Get all technique pitfalls as a dictionary."""
        if not self._memory:
            return {}
        return {tp.technique: tp.pitfalls for tp in self._memory.technique_pitfalls}

    def search_pitfalls(self, keyword: str) -> list[dict[str, Any]]:
        """Search for pitfalls containing a keyword."""
        results = []
        if not self._memory:
            return results

        keyword_lower = keyword.lower()
        for tp in self._memory.technique_pitfalls:
            for pitfall in tp.pitfalls:
                if keyword_lower in pitfall.lower():
                    results.append(
                        {
                            "technique": tp.technique,
                            "pitfall": pitfall,
                        }
                    )
        return results


def create_loader() -> StructuralMemoryLoader:
    """Factory function to create a loader."""
    return StructuralMemoryLoader()


if __name__ == "__main__":
    loader = StructuralMemoryLoader()

    print("Project Conventions:")
    for conv in loader.get_project_conventions():
        print(f"  - {conv}")

    print("\nArchitectural Decisions:")
    for ad in loader.get_architectural_decisions():
        print(f"  [{ad.id}] {ad.decision} ({ad.status})")
        print(f"      {ad.rationale}")

    print("\nTechnique Pitfalls:")
    for tech, pitfalls in loader.get_all_technique_pitfalls().items():
        print(f"  {tech}:")
        for p in pitfalls:
            print(f"    - {p}")
