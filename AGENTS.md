# Native Swarm Rules — Agent Orchestration Framework

**Architecture:** Core domain-agnostic + Domain Packs (contractual extensions)  
**Reference:** `specs/core/orchestration-contract.yaml`, `docs/CONSTITUTION_emendada.md`

## Core Protocols (Nivel 0)

The following are **protocols** defined by the Core. Domain Packs may provide implementations but cannot alter the protocol definitions.

| Protocol | Role | Contract |
|----------|------|----------|
| `Verifier` | Mandatory pre-synthesis gate | Must validate evidence integrity, handoff compliance, boundary constraints |
| `Synthesizer` | Single final writer for run package | Must produce final artifact, summary report, trace links |
| `Handoff` | Formal transfer of control between agents | 12 required fields, 6 validation rules |
| `Evidence` | Immutable, auditable data produced by agents | Cryptographic integrity, cross-domain, forbidden operations |

## Swarm Rules

- Use MCP only for context that lives outside the repository or changes frequently.
- Check `/mcp` before starting a multi-agent swarm run and stop if a required server is missing.
- Use `docs_researcher` for version-sensitive facts or official external documentation lookups.
- Treat the workflow as artifact-first: worker outputs belong under `.internal/artifacts/codex-swarm/<run-id>/`.
- Keep `write_scope` disjoint across parallel workers.
- `verifier` is the mandatory gate before `synthesizer`.
- `synthesizer` is the single final writer for the run package.
- When live session state matters, pass a `--session-snapshot` JSON file to `.internal/scripts/codex_swarm_prepare.py` so the run manifest records the effective overrides.

## Domain Packs

Domain Packs are contractual extensions registered via `registry/registry.yaml`. They implement Core protocols but do not define them.

| Pack | Type | Status | Description |
|------|------|--------|-------------|
| `software-engineering` | functional | active | Default development workflow capabilities |
| `ml-ai` | vertical | experimental | ML/AI training, optimization, experiment tracking |
| `medical-imaging` | vertical | experimental | Medical image analysis and reporting |

To add a new Domain Pack:
1. Create `domains/<domain-name>/` with `contract.yaml` and `manifest.json`
2. Register in `registry/registry.yaml`
3. Validate against Core protocols

## Known Issues

### Routing Bug: `/autocode` command (OpenCode v1.3.13)

**Current finding:** The prior routing diagnosis was based on repository configs that used an invalid/stale config schema for OpenCode v1.3.13. The governing root cause in this snapshot is repository configuration, not an upstream runtime defect.

**Supported fix:** When `opencode.json` and `.opencode/opencode.json` use top-level `agent` and `command`, `/autocode` routes natively to the `autocoder` agent without `--agent`.

**Usage:** Native routing is now the supported path:
```bash
opencode run --command autocode "your task"
# Or use the wrapper script with parity pre-flight:
./.internal/scripts/run-autocode.sh "your task"
```

**Tracking:** Historical investigation evidence remains in `.internal/artifacts/codex-swarm/run-stable-execution/debug_autocode.log`, but the repository fix is the schema migration to the runtime-supported layout.

---

---

## Stable Execution Guarantees

This project now enforces stable execution through a comprehensive specification suite:

### Configuration Parity
- `opencode.json` (root) and `.opencode/opencode.json` must match on **critical routing fields only**
- Routing-critical fields that MUST match: `default_agent`, `command.autocode.agent`, `agent.autocoder.maxSteps`, `agent.general.maxSteps`
- Allowed divergence: supported non-routing fields (for example `providers` or `instructions` in sanitized examples)
- Policy enforced by: wrapper script, tests, and CI workflow
- Both files now define `default_agent: autocoder`, `command.autocode.agent: autocoder`, and bounded agent step limits in `agent.*`

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
- 33 Python tests across 7 classes in 5 suites: TestCommandRoutingRegression, TestStableExecutionGuardrails, TestOpenCodeConfigParity, TestRuntimeIntegration, TestPublicVsInternalBoundary, TestSanitizedPublicConfigurationContract, TestPublicRepoAllowlistGovernance, TestOpencodeGovernance
- Run: `python -m pytest .internal/tests/ -v`

### CI Integration
- Routing regression: `.github/workflows/routing-regression.yml`
- Constitutional compliance: `.github/workflows/constitutional-compliance.yml`
- Config parity validated by critical routing fields only (not full JSON equality)
