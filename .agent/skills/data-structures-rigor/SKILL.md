---
name: data-structures-rigor
description: Static rigor checks for data-structure selection, loop complexity, and algorithmic hotspots.
---

# Data Structures Rigor Skill

## Objective

Scan Python code for complexity hotspots and data-structure anti-patterns that create reliability or scalability risk.

## Script

```bash
python .agent/skills/data-structures-rigor/scripts/data_structures_rigor.py --report
```

## Common Usage

```bash
python .agent/skills/data-structures-rigor/scripts/data_structures_rigor.py \
  --report \
  --scan-path src/engineering \
  --scan-path src/data \
  --max-loop-depth 3
```

```bash
python .agent/skills/data-structures-rigor/scripts/data_structures_rigor.py \
  --report \
  --max-critical 0 \
  --max-high 0
```

## Artifacts

- `artifacts/data_structures/ds_rigor_report.json`
- `artifacts/data_structures/ds_hotspots.txt`

## Exit Codes

- `0`: no threshold breach
- `1`: threshold breach
- `2`: execution error
