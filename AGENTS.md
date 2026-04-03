# Native Swarm Rules

- Use MCP only for context that lives outside the repository or changes frequently.
- Check `/mcp` before starting a multi-agent swarm run and stop if a required server is missing.
- Use `docs_researcher` for version-sensitive facts or official external documentation lookups.
- Treat the workflow as artifact-first: worker outputs belong under `.internal/artifacts/codex-swarm/<run-id>/`.
- Keep `write_scope` disjoint across parallel workers.
- `verifier` is the mandatory gate before `synthesizer`.
- `synthesizer` is the single final writer for the run package.
- When live session state matters, pass a `--session-snapshot` JSON file to `.internal/scripts/codex_swarm_prepare.py` so the run manifest records the effective overrides.

## Known Issues

### Routing Bug: `/autocode` command (OpenCode v1.3.13)

**Problem:** The `/autocode` command (defined in `.opencode/commands/autocode.md` with `agent: autocoder` in frontmatter) is NOT routed to the `autocoder` agent at runtime. Instead, it falls back to the `general` agent with `maxSteps: 50` (expected: `autocoder` with `maxSteps: 6`).

**Confirmed:** Bug persists with `--pure` flag (no plugins), confirming it is a runtime routing issue, not a plugin issue. Other commands with `agent:` in frontmatter work correctly (`/ship` → orchestrator, `/review` → reviewer, `/analyze` → explore).

**Workaround:** Use `--agent autocoder` flag explicitly:
```bash
opencode run --agent autocoder --command autocode "your task"
# Or use the wrapper script:
./.internal/scripts/run-autocode.sh "your task"
```

**Tracking:** Root cause appears to be silent config merge failure when `.opencode/opencode.json` does not exist. See `.internal/artifacts/codex-swarm/run-stable-execution/debug_autocode.log` for DEBUG evidence.

---

## Stable Execution Guarantees

This project now enforces stable execution through a comprehensive specification suite:

### Configuration Parity
- `opencode.json` (root) and `.opencode/opencode.json` must be structurally and semantically equivalent
- Routing-critical fields that MUST match: `default_agent`, `maxSteps`, `routing.commands.autocode`, `routing.agents.autocoder.maxSteps`
- Allowed divergence policy: only non-routing metadata/local runtime fields may differ (e.g., `note`, `template_refs`, provider credentials, local overrides). Any divergence that changes routing or step limits is forbidden.
- Automated test `test_root_and_dot_opencode_configs_match` fails on drift
- Both files define `default_agent: autocoder` with `maxSteps: 6`

### Invariant Enforcement
- **No unbounded retry:** `max_attempts ≤ 3` with exponential backoff
- **No silent fallback:** Agent routing failures require explicit logging and evidence
- **Verifier gate:** `verifier` is mandatory before `synthesizer` writes final output
- **Write scope isolation:** Parallel workers must have disjoint `write_scope`
- **No doom loop:** `doom_loop: deny` is enforced globally and per-agent
- **Idempotency:** Same idempotency key must imply same logical outcome

### State Machine
- 13 states with 20 valid transitions and 7 forbidden transitions
- Forbidden: `running→running` (no progress), `retrying→retrying` (infinite), `running→synthesized` (skip verified)
- Resume requires valid checkpoint; failed→running requires explicit invalidation

### Handoff Contract
- 12 required fields: schema_version, artifact_type, producer_agent, consumer_agent, spec_id, spec_version, run_id, timestamp, evidence_refs, risk_level, compatibility_assessment, trace_links
- 6 validation rules: no_partial_payload, no_missing_provenance, evidence_refs_resolvable, versioning_required, write_scope_disjoint, verifier_gate

### Test Coverage
- 8 Python tests in 2 suites: TestCommandRoutingRegression, TestStableExecutionGuardrails
- Run: `python -m pytest .internal/tests/test_stable_execution.py -v`

### CI Integration
- Routing regression: `.github/workflows/routing-regression.yml`
- Python test suite runs on push/PR to main/master when config or spec files change
