#!/usr/bin/env python3
"""Accessibility Checker Script for Vitruviano Frontend.

Analyzes React/TSX components for common accessibility issues:
- Missing alt text on images
- Missing aria-labels on interactive elements
- Missing keyboard handlers
- Color contrast issues in hardcoded values
- Missing focus states
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Generator


@dataclass
class A11yIssue:
    """Represents an accessibility issue found in code."""

    file: str
    line: int
    severity: str  # 'error', 'warning', 'info'
    rule: str
    message: str
    suggestion: str


class AccessibilityChecker:
    """Checks React/TSX files for accessibility issues."""

    def __init__(self) -> None:
        """Initialize the checker state."""
        self.issues: list[A11yIssue] = []

    def check_file(self, file_path: Path) -> list[A11yIssue]:
        """Check a single file for accessibility issues."""
        issues: list[A11yIssue] = []
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        for line_num, line in enumerate(lines, 1):
            issues.extend(self._check_line(str(file_path), line_num, line))

        return issues

    def _check_line(
        self, file: str, line_num: int, line: str
    ) -> Generator[A11yIssue]:
        """Check a single line for accessibility issues."""
        # Check for img without alt
        if re.search(r"<img\s+(?![^>]*alt=)", line):
            yield A11yIssue(
                file=file,
                line=line_num,
                severity="error",
                rule="img-alt",
                message="Image without alt attribute",
                suggestion=(
                    'Add alt="descriptive text" or alt="" for decorative images'
                ),
            )

        # Check for button without accessible name
        if re.search(r"<button[^>]*>\s*<[^/]", line) and not re.search(
            r"aria-label=", line
        ):
            yield A11yIssue(
                file=file,
                line=line_num,
                severity="warning",
                rule="button-name",
                message="Button with only icon may lack accessible name",
                suggestion="Add aria-label or visible text content",
            )

        # Check for onClick without keyboard handler
        if re.search(r"onClick=", line) and not re.search(
            r"(onKeyDown|onKeyUp|onKeyPress|role=.button|<button)", line
        ):
            yield A11yIssue(
                file=file,
                line=line_num,
                severity="warning",
                rule="keyboard-access",
                message=(
                    "onClick without keyboard handler on non-button element"
                ),
                suggestion="Add onKeyDown handler or use <button> element",
            )

        # Check for hardcoded colors
        if re.search(
            r"(#[0-9a-fA-F]{3,6}|rgb\(|rgba\()", line
        ) and not re.search(r"(theme\.css|globals\.css|--)", line):
            yield A11yIssue(
                file=file,
                line=line_num,
                severity="info",
                rule="color-token",
                message="Hardcoded color value instead of CSS variable",
                suggestion="Use var(--surface-*) or var(--text-*) tokens",
            )

        # Check for div/span with onClick (should be button)
        if re.search(r"<(div|span)[^>]*onClick=", line) and not re.search(
            r"role=[\"\']button[\"\']", line
        ):
            yield A11yIssue(
                file=file,
                line=line_num,
                severity="warning",
                rule="semantic-button",
                message=(
                    "Clickable div/span should be a button or have role='button'"
                ),
                suggestion=(
                    "Use <button> element or add role='button' and tabIndex={0}"
                ),
            )

        # Check for missing focus-visible styles
        if re.search(r"(hover:|:hover)", line) and not re.search(
            r"focus", line
        ):
            yield A11yIssue(
                file=file,
                line=line_num,
                severity="info",
                rule="focus-visible",
                message="Hover style without corresponding focus style",
                suggestion="Add focus-visible: styles for keyboard users",
            )

    def check_directory(self, directory: Path) -> list[A11yIssue]:
        """Recursively check all TSX files in a directory."""
        issues: list[A11yIssue] = []

        for file_path in directory.rglob("*.tsx"):
            if "node_modules" in str(file_path):
                continue
            issues.extend(self.check_file(file_path))

        self.issues = issues
        return issues

    def print_report(self) -> None:
        """Print a formatted report of all issues."""
        if not self.issues:
            print("\n✅ No accessibility issues found!")
            return

        errors = [i for i in self.issues if i.severity == "error"]
        warnings = [i for i in self.issues if i.severity == "warning"]
        infos = [i for i in self.issues if i.severity == "info"]

        print("\n" + "=" * 60)
        print("ACCESSIBILITY AUDIT REPORT")
        print("=" * 60)
        print(f"\n🔴 Errors: {len(errors)}")
        print(f"🟡 Warnings: {len(warnings)}")
        print(f"🔵 Info: {len(infos)}")
        print(f"📊 Total: {len(self.issues)}")

        for severity, emoji, items in [
            ("error", "🔴", errors),
            ("warning", "🟡", warnings),
            ("info", "🔵", infos),
        ]:
            if items:
                print(f"\n{'-' * 60}")
                print(f"{emoji} {severity.upper()}S ({len(items)})")
                print("-" * 60)
                for issue in items:
                    print(f"\n{issue.file}:{issue.line}")
                    print(f"  ├─ Rule: {issue.rule}")
                    print(f"  ├─ {issue.message}")
                    print(f"  └─ 💡 {issue.suggestion}")

        print("\n" + "=" * 60)


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python a11y_checker.py <directory>")
        sys.exit(1)

    directory = Path(sys.argv[1])
    if not directory.exists():
        print(f"Error: Directory '{directory}' not found")
        sys.exit(1)

    checker = AccessibilityChecker()
    checker.check_directory(directory)
    checker.print_report()

    # Exit with error code if there are errors
    errors = [i for i in checker.issues if i.severity == "error"]
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
