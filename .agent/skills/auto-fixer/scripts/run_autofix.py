#!/usr/bin/env python3
"""Run ruff fix and format, then capture the diff."""

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    mode = os.getenv("VITRUVIANO_AGENT_MODE", "read")
    if mode != "write":
        print(
            f"Agent executing in mode '{mode}'. Auto-fix requires 'write' mode."
        )
        return 0

    # We will target the Python source and tests
    targets = ["src", "scripts", "tests", ".agent"]

    print("Running ruff format...")
    subprocess.run(["ruff", "format", *targets], check=False)

    print("Running ruff check --fix...")
    subprocess.run(["ruff", "check", "--fix", *targets], check=False)

    # Capture diff
    try:
        diff_proc = subprocess.run(
            ["git", "diff", "--", *targets],
            capture_output=True,
            text=True,
            check=True,
        )
        diff_text = diff_proc.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error capturing git diff: {e}")
        return 1

    artifacts_dir = Path("artifacts/rpa/swarm")
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    diff_file = artifacts_dir / "auto_remediated.diff"

    if diff_text:
        diff_file.write_text(diff_text, encoding="utf-8")
        print(f"Auto-fixed changes recorded in {diff_file}")
    else:
        diff_file.write_text("No changes required.", encoding="utf-8")
        print("No changes were needed. Code is compliant.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
