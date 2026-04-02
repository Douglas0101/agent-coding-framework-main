#!/usr/bin/env python3
"""
Design Token Validator for Vitruviano Frontend

Validates that CSS custom properties are used correctly throughout
the codebase and identifies any hardcoded values that should use tokens.
"""

import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar


@dataclass
class TokenViolation:
    """Represents a design token violation."""

    file: str
    line: int
    category: str
    found: str
    suggestion: str


class TokenValidator:
    """Validates design token usage in TSX and CSS files."""

    # Valid token patterns
    VALID_TOKENS: ClassVar[dict[str, list[str]]] = {
        "surface": [
            "--surface-0",
            "--surface-1",
            "--surface-2",
            "--surface-3",
            "--surface-glass",
        ],
        "text": ["--text-primary", "--text-secondary", "--text-muted"],
        "accent": [
            "--accent-teal",
            "--accent-teal-soft",
            "--accent-amber",
            "--accent-amber-soft",
            "--accent-red",
            "--accent-red-soft",
            "--accent-lilac",
        ],
        "heatmap": ["--heatmap-low", "--heatmap-mid", "--heatmap-high"],
        "border": ["--border-soft", "--border-strong"],
        "shadow": ["--shadow-soft", "--shadow-strong"],
        "radius": ["--radius-lg", "--radius-md", "--radius-sm"],
        "transition": ["--transition-fast", "--transition-slow"],
    }

    # Patterns that should use tokens
    HARDCODED_PATTERNS: ClassVar[list[tuple[str, str, str]]] = [
        # Hex colors (except for specific allowed values)
        (
            r"#[0-9a-fA-F]{3,6}(?![0-9a-fA-F])",
            "color",
            "Use var(--surface-*) or var(--accent-*)",
        ),
        # RGB/RGBA colors
        (r"rgba?\([^)]+\)", "color", "Use var(--*) with opacity modifier"),
        # Pixel values for spacing - large values only
        (
            r"\b(1[3-9]|[2-9][0-9]|[1-9][0-9]{2,})px\b",
            "spacing",
            "Consider using Tailwind spacing scale",
        ),
        # Hardcoded border-radius
        (r"border-radius:\s*\d+px", "radius", "Use var(--radius-lg/md/sm)"),
        # Hardcoded box-shadow (simplified pattern)
        (r"box-shadow:\s*\d+px", "shadow", "Use var(--shadow-soft/strong)"),
    ]

    # Allowed exceptions
    ALLOWED_PATTERNS: ClassVar[list[str]] = [
        r"var\(--",  # Already using CSS variable
        r"theme\.css",  # In theme file
        r"globals\.css",  # In globals file
        r"#06151a",  # Allowed dark background for contrast
        r"#fff",  # White text
        r"#000",  # Black text
        r"--color-",  # Tailwind theme definitions
        r"@theme",  # Tailwind theme block
        r":root",  # CSS root definitions
    ]

    def __init__(self) -> None:
        self.violations: list[TokenViolation] = []
        self.token_usage: dict[str, int] = defaultdict(int)

    def should_skip_line(self, line: str) -> bool:
        """Check if line should be skipped (contains allowed patterns)."""
        return any(re.search(p, line) for p in self.ALLOWED_PATTERNS)

    def check_file(self, file_path: Path) -> list[TokenViolation]:
        """Check a single file for token violations."""
        violations: list[TokenViolation] = []
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        # Track token usage
        for token_list in self.VALID_TOKENS.values():
            for token in token_list:
                count = content.count(token)
                if count > 0:
                    self.token_usage[token] += count

        for line_num, line in enumerate(lines, 1):
            if self.should_skip_line(line):
                continue

            for pattern, category, suggestion in self.HARDCODED_PATTERNS:
                matches = re.finditer(pattern, line)
                for match in matches:
                    violations.append(
                        TokenViolation(
                            file=str(file_path),
                            line=line_num,
                            category=category,
                            found=match.group(),
                            suggestion=suggestion,
                        )
                    )

        return violations

    def check_directory(self, directory: Path) -> list[TokenViolation]:
        """Recursively check all relevant files in a directory."""
        violations: list[TokenViolation] = []

        for pattern in ["*.tsx", "*.css"]:
            for file_path in directory.rglob(pattern):
                if "node_modules" in str(file_path):
                    continue
                if ".next" in str(file_path):
                    continue
                violations.extend(self.check_file(file_path))

        self.violations = violations
        return violations

    def print_report(self) -> None:
        """Print a formatted report of all violations and usage."""
        print("\n" + "=" * 60)
        print("DESIGN TOKEN VALIDATION REPORT")
        print("=" * 60)

        # Token usage summary
        print("\n📊 TOKEN USAGE SUMMARY")
        print("-" * 40)
        for category, tokens in self.VALID_TOKENS.items():
            print(f"\n{category.upper()}")
            for token in tokens:
                count = self.token_usage.get(token, 0)
                bar = "█" * min(count, 20)
                print(f"  {token}: {bar} ({count})")

        # Unused tokens warning
        unused = [
            t
            for tokens in self.VALID_TOKENS.values()
            for t in tokens
            if self.token_usage.get(t, 0) == 0
        ]
        if unused:
            print("\n⚠️  UNUSED TOKENS")
            print("-" * 40)
            for token in unused:
                print(f"  {token}")

        # Violations
        if self.violations:
            print("\n🔴 VIOLATIONS")
            print("-" * 40)

            by_category: dict[str, list[TokenViolation]] = defaultdict(list)
            for v in self.violations:
                by_category[v.category].append(v)

            for category, items in by_category.items():
                print(f"\n{category.upper()} ({len(items)} issues)")
                for v in items[:10]:  # Limit output
                    print(f"  {v.file}:{v.line}")
                    print(f"    Found: {v.found}")
                    print(f"    💡 {v.suggestion}")
                if len(items) > 10:
                    print(f"  ... and {len(items) - 10} more")
        else:
            print("\n✅ No token violations found!")

        print("\n" + "=" * 60)


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python validate_tokens.py <directory>")
        sys.exit(1)

    directory = Path(sys.argv[1])
    if not directory.exists():
        print(f"Error: Directory '{directory}' not found")
        sys.exit(1)

    validator = TokenValidator()
    validator.check_directory(directory)
    validator.print_report()

    # Exit with error code if there are violations
    sys.exit(1 if validator.violations else 0)


if __name__ == "__main__":
    main()
