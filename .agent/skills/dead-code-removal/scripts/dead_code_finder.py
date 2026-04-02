#!/usr/bin/env python3
"""Script de automação para detecção de código morto.

Usa vulture e análise de imports para identificar código não utilizado.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class DeadCodeItem:
    """Item de código morto detectado."""

    file: str
    line: int
    name: str
    item_type: str
    confidence: int

    @property
    def is_high_confidence(self) -> bool:
        """Retorna True se confidence >= 80%."""
        return self.confidence >= 80


def run_vulture(
    paths: list[str], min_confidence: int = 60
) -> list[DeadCodeItem]:
    """Executa vulture e parseia resultados."""
    cmd = [
        "vulture",
        *paths,
        f"--min-confidence={min_confidence}",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parents[4],
    )

    items = []
    for line in (result.stdout + result.stderr).split("\n"):
        if not line.strip():
            continue

        # Format: file.py:line: unused function 'name' (confidence%)
        try:
            parts = line.split(":")
            if len(parts) >= 3:
                file_path = parts[0]
                line_num = int(parts[1])
                rest = ":".join(parts[2:]).strip()

                # Parse tipo e nome
                item_type = "unknown"
                name = "unknown"
                confidence = 60

                if "unused" in rest.lower():
                    for t in [
                        "function",
                        "method",
                        "class",
                        "variable",
                        "import",
                        "attribute",
                    ]:
                        if t in rest.lower():
                            item_type = t
                            break

                    # Extrai nome entre aspas
                    if "'" in rest:
                        name = rest.split("'")[1]

                    # Extrai confidence
                    if "%" in rest:
                        conf_str = rest.split("(")[-1].split("%")[0]
                        confidence = int(conf_str)

                items.append(
                    DeadCodeItem(
                        file=file_path,
                        line=line_num,
                        name=name,
                        item_type=item_type,
                        confidence=confidence,
                    )
                )
        except (ValueError, IndexError) as _:
            continue

    return items


def run_import_check() -> list[DeadCodeItem]:
    """Verifica imports não utilizados com Ruff."""
    cmd = [
        "ruff",
        "check",
        "--select=F401",
        "--output-format=json",
        ".",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parents[4],
    )

    import json

    items = []
    try:
        issues = json.loads(result.stdout) if result.stdout else []
        for issue in issues:
            items.append(
                DeadCodeItem(
                    file=issue.get("filename", ""),
                    line=issue.get("location", {}).get("row", 0),
                    name=issue.get("message", "").split("'")[1]
                    if "'" in issue.get("message", "")
                    else "unknown",
                    item_type="import",
                    confidence=100,
                )
            )
    except (json.JSONDecodeError, KeyError, IndexError) as _:
        pass

    return items


def format_report(items: list[DeadCodeItem]) -> str:
    """Formata relatório de código morto."""
    lines = [
        "=" * 70,
        "DEAD CODE ANALYSIS REPORT",
        f"Generated: {datetime.now(UTC).isoformat()}",
        "=" * 70,
        "",
    ]

    # Agrupa por tipo
    by_type: dict[str, list[DeadCodeItem]] = {}
    for item in items:
        by_type.setdefault(item.item_type, []).append(item)

    high_confidence = [i for i in items if i.is_high_confidence]
    low_confidence = [i for i in items if not i.is_high_confidence]

    lines.extend(
        [
            "SUMMARY",
            "-" * 70,
            f"Total items: {len(items)}",
            f"  High confidence (>=80%): {len(high_confidence)}",
            f"  Low confidence (<80%): {len(low_confidence)}",
            "",
        ]
    )

    for item_type, type_items in sorted(by_type.items()):
        emoji = {
            "function": "🔧",
            "method": "🔨",
            "class": "📦",
            "variable": "📝",
            "import": "📥",
            "attribute": "🏷️",
        }.get(item_type, "❓")

        lines.extend(
            [
                f"{emoji} {item_type.upper()}S ({len(type_items)})",
                "-" * 70,
            ]
        )

        for item in sorted(type_items, key=lambda x: (-x.confidence, x.file)):
            conf_indicator = (
                "🔴"
                if item.confidence >= 90
                else ("🟡" if item.confidence >= 70 else "🟢")
            )
            lines.append(
                f"  {conf_indicator} {item.file}:{item.line} - "
                f"'{item.name}' ({item.confidence}%)"
            )

        lines.append("")

    if high_confidence:
        lines.extend(
            [
                "RECOMMENDED ACTIONS",
                "-" * 70,
                "Items with >=80% confidence can likely be safely removed.",
                "Always verify with tests before removing.",
                "",
            ]
        )

    lines.append("=" * 70)

    return "\n".join(lines)


def main() -> int:
    """Função principal."""
    parser = argparse.ArgumentParser(
        description="Dead code detection automation"
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Run full dead code scan",
    )
    parser.add_argument(
        "--imports",
        action="store_true",
        help="Check unused imports only",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate detailed report",
    )
    parser.add_argument(
        "--min-confidence",
        type=int,
        default=60,
        help="Minimum confidence threshold (default: 60)",
    )

    args = parser.parse_args()

    project_root = Path(__file__).parents[4]

    all_items: list[DeadCodeItem] = []

    if args.imports:
        print("📥 Checking unused imports...")
        import_items = run_import_check()
        all_items.extend(import_items)
        print(f"Found {len(import_items)} unused imports")
    elif args.scan:
        print("🔍 Running full dead code scan...")

        # Vulture scan
        vulture_items = run_vulture(
            ["src/"],
            min_confidence=args.min_confidence,
        )
        all_items.extend(vulture_items)

        # Import check
        import_items = run_import_check()
        all_items.extend(import_items)

        print(f"Found {len(all_items)} dead code items")

    if args.report and all_items:
        report = format_report(all_items)
        print(report)

        report_path = project_root / "artifacts" / "dead_code_report.txt"
        report_path.parent.mkdir(exist_ok=True)
        report_path.write_text(report)
        print(f"\n📄 Report saved to: {report_path}")
    elif all_items:
        # Output resumido
        high_conf = [i for i in all_items if i.is_high_confidence]
        print(f"\n🔴 High confidence items: {len(high_conf)}")
        for item in high_conf[:10]:
            print(
                f"  {item.file}:{item.line} - {item.name} ({item.item_type})"
            )

        if len(high_conf) > 10:
            print(f"  ... and {len(high_conf) - 10} more")

    if not all_items:
        print("✅ No dead code detected!")

    return 0 if not all_items else 1


if __name__ == "__main__":
    sys.exit(main())
