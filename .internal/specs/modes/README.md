# Mode Contracts

This directory contains the formal Agent Mode Contracts for the Orchestration Framework.

## Structure

```
modes/
├── explore.yaml          # Repository exploration and analysis mode
├── reviewer.yaml         # Technical review and quality gate mode
├── orchestrator.yaml     # Swarm orchestration and workflow coordination mode
├── autocoder.yaml        # Primary autocode execution mode
└── README.md             # This file
```

## What is a Mode Contract?

A Mode Contract is the **source of truth** for how an operational mode behaves. It defines:

- **Mission:** What the mode is designed to accomplish
- **Scope:** Input/output schemas, allowed and forbidden tools
- **Resources:** Multidimensional budget (tokens, iterations, handoffs, timeout)
- **Memory:** Operational context, session state, and structural memory policies
- **Satisficing:** Quality/cost trade-off strategy (URGENT, ECONOMICAL, BALANCED, DEEP)
- **Handoff:** Target modes, compression mode, verifier requirements
- **Error Policy:** Retry limits, timeout, failure handling

## Schema

All mode contracts conform to `.internal/specs/core/agent-mode-contract.yaml`.

## Validation

Mode contracts are validated in CI via:
- `test_mode_contracts.py` — Schema, drift, handoff, and constitutional compliance tests
- `validate_mode_budgets.py` — Budget instrumentation and violation detection

## Adding a New Mode

1. Create `<mode-name>.yaml` in this directory
2. Conform to the schema in `agent-mode-contract.yaml`
3. Add `mode_contract` reference in `opencode.json` and `.opencode/opencode.json`
4. Add tests in `test_mode_contracts.py`
5. Validate: `python .internal/scripts/validate_mode_budgets.py --mode <mode-name>`
6. Run full test suite: `python -m pytest .internal/tests/ -v`

## Budget Summary

| Mode | Satisficing | Total Tokens | Max Iterations | Timeout |
|------|-------------|-------------|----------------|---------|
| explore | BALANCED | 36,000 | 15 | 300s |
| reviewer | DEEP | 52,000 | 20 | 600s |
| orchestrator | BALANCED | 68,000 | 30 | 1800s |
| autocoder | BALANCED | 72,000 | 25 | 900s |
