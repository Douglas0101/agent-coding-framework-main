"""Programmatic registry for .internal/ path resolution and integrity checking.

This module provides a central way to resolve paths to scripts, tests, and artifacts
within the .internal/ directory structure.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

INTERNAL_ROOT = Path(__file__).resolve().parent
REPO_ROOT = INTERNAL_ROOT.parent

ComponentPaths = Dict[str, Path]

_COMPONENTS: ComponentPaths = {
    "scripts": INTERNAL_ROOT / "scripts",
    "tests": INTERNAL_ROOT / "tests",
    "artifacts": INTERNAL_ROOT / "artifacts",
}

# Known dependency edges: (source_file, target_file, relationship_type)
DEPENDENCY_EDGES: List[Tuple[str, str, str]] = [
    # Import dependencies
    ("scripts/security_patterns.py", "tests/test_stable_execution.py", "import"),
    (
        "scripts/security_patterns.py",
        "tests/test_public_config_sanitization.py",
        "import",
    ),
    ("scripts/security_patterns.py", "scripts/check-public-boundary.sh", "import"),
    # CI/CD triggers
    ("scripts/scan_sensitive_patterns.py", ".pre-commit-config.yaml", "ci_trigger"),
    (
        "scripts/scan_sensitive_patterns.py",
        ".github/workflows/public-repo-guard.yml",
        "ci_trigger",
    ),
    (
        "scripts/check-public-boundary.sh",
        ".github/workflows/public-artifacts-guard.yml",
        "ci_trigger",
    ),
    (
        "tests/test_stable_execution.py",
        ".github/workflows/routing-regression.yml",
        "ci_trigger",
    ),
    # Evidence relationships
    (
        "tests/test_stable_execution.py",
        "artifacts/codex-swarm/run-stable-execution/",
        "generates",
    ),
    (
        "artifacts/codex-swarm/run-stable-execution/conformance-report.json",
        "scripts/run-autocode.sh",
        "evidence_ref",
    ),
    (
        "artifacts/codex-swarm/run-stable-execution/conformance-report.json",
        "tests/test_stable_execution.py",
        "evidence_ref",
    ),
    # Cross-references
    ("scripts/run-autocode.sh", "tests/test_stable_execution.py", "fallback_ref"),
]


def resolve_path(component: str, relative_path: str) -> Path:
    """Resolve a path within a .internal/ component.

    Args:
        component: One of 'scripts', 'tests', 'artifacts'
        relative_path: Path relative to the component root

    Returns:
        Absolute path to the resolved file/directory

    Raises:
        ValueError: If component is not recognized
    """
    if component not in _COMPONENTS:
        raise ValueError(
            f"Unknown component: {component!r}. "
            f"Valid components: {sorted(_COMPONENTS.keys())}"
        )
    return _COMPONENTS[component] / relative_path


def resolve_script(name: str) -> Path:
    """Resolve a script path. Shortcut for resolve_path('scripts', name)."""
    return resolve_path("scripts", name)


def resolve_test(name: str) -> Path:
    """Resolve a test path. Shortcut for resolve_path('tests', name)."""
    return resolve_path("tests", name)


def resolve_artifact(name: str) -> Path:
    """Resolve an artifact path. Shortcut for resolve_path('artifacts', name)."""
    return resolve_path("artifacts", name)


def get_internal_root() -> Path:
    """Return the .internal/ root directory."""
    return INTERNAL_ROOT


def get_repo_root() -> Path:
    """Return the repository root directory."""
    return REPO_ROOT


def list_component_files(component: str) -> List[Path]:
    """List all files in a component directory.

    Args:
        component: One of 'scripts', 'tests', 'artifacts'

    Returns:
        Sorted list of file paths in the component
    """
    base = resolve_path(component, "")
    if not base.exists():
        return []
    return sorted(f for f in base.rglob("*") if f.is_file())


def validate_integrity() -> List[str]:
    """Validate that all known dependency edges resolve to existing files.

    Returns:
        List of error messages (empty if all dependencies resolve)
    """
    errors: List[str] = []

    for source, target, relationship in DEPENDENCY_EDGES:
        # Determine the base path for resolution
        if source.startswith("scripts/"):
            source_path = resolve_path("scripts", source[len("scripts/") :])
        elif source.startswith("tests/"):
            source_path = resolve_path("tests", source[len("tests/") :])
        elif source.startswith("artifacts/"):
            source_path = resolve_path("artifacts", source[len("artifacts/") :])
        elif source.startswith("."):
            source_path = REPO_ROOT / source
        else:
            continue

        if not source_path.exists():
            errors.append(
                f"Missing source: {source_path} (referenced in {relationship})"
            )

        # Target might be external (like .github/workflows/*.yml)
        if target.startswith("."):
            target_path = REPO_ROOT / target
            if not target_path.exists():
                errors.append(f"Missing target: {target_path} (from {source})")

    return errors


def print_dependency_graph() -> None:
    """Print the dependency graph in a human-readable format."""
    print("=== .internal/ Dependency Graph ===\n")

    # Group by source
    by_source: Dict[str, List[Tuple[str, str]]] = {}
    for source, target, rel in DEPENDENCY_EDGES:
        by_source.setdefault(source, []).append((target, rel))

    for source, targets in sorted(by_source.items()):
        print(f"  {source}")
        for target, rel in sorted(targets):
            print(f"    └── [{rel}] → {target}")
        print()


if __name__ == "__main__":
    print(f"Internal root: {INTERNAL_ROOT}")
    print(f"Repo root: {REPO_ROOT}")
    print()

    print("=== Component Files ===")
    for component in ("scripts", "tests", "artifacts"):
        files = list_component_files(component)
        print(f"\n  {component}/ ({len(files)} files)")
        for f in files:
            print(f"    - {f.relative_to(INTERNAL_ROOT)}")

    print()
    print("=== Integrity Check ===")
    errors = validate_integrity()
    if errors:
        print("ERRORS FOUND:")
        for error in errors:
            print(f"  ✗ {error}")
    else:
        print("  All dependencies resolve correctly.")

    print()
    print_dependency_graph()
