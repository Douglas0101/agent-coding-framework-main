#!/usr/bin/env bash
set -euo pipefail

root="${1:-.}"
shift || true

if [[ ! -f "$root/Makefile" || ! -f "$root/scripts/rpa_engineer.py" ]]; then
  echo "Expected repo root with Makefile and scripts/rpa_engineer.py (got: $root)" >&2
  exit 2
fi

python "$root/scripts/rpa_engineer.py" "$@"
