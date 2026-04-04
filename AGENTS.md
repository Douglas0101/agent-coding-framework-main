# Native Swarm Rules — Agent Orchestration Framework

**Architecture:** Core domain-agnostic + Domain Packs (contractual extensions) + Agent Mode Contracts (operational layer)  
**Reference:** `.internal/specs/core/orchestration-contract.yaml`, `.internal/specs/core/agent-mode-contract.yaml`, `docs/CONSTITUTION_emendada.md`  
**Policy:** Only `docs/` is public surface. All improvements go to `.internal/`.

## Core Protocols (Nivel 0)

The following are **protocols** defined by the Core. Domain Packs may provide implementations but cannot alter the protocol definitions.

| Protocol | Role | Contract |
|----------|------|----------|
| `Verifier` | Mandatory pre-synthesis gate | Must validate evidence integrity, handoff compliance, boundary constraints |
| `Synthesizer` | Single final writer for run package | Must produce final artifact, summary report, trace links |
| `Handoff` | Formal transfer of control between agents | 12 required fields, 6 validation rules |
| `Evidence` | Immutable, auditable data produced by agents | Cryptographic integrity, cross-domain, forbidden operations |

## Agent Mode Contracts (Nivel 1)

Each operational mode is governed by a formal contract in `.internal/specs/modes/`. Contracts define mission, scope, budgets, memory policy, satisficing strategy, and handoff rules.

| Mode | Contract | Satisficing | Budget (tokens) | Priority |
|------|----------|-------------|-----------------|----------|
| `explore` | `modes/explore.yaml` | BALANCED | 36,000 | high |
| `reviewer` | `modes/reviewer.yaml` | DEEP | 52,000 | critical |
| `orchestrator` | `modes/orchestrator.yaml` | BALANCED | 68,000 | critical |
| `autocoder` | `modes/autocoder.yaml` | BALANCED | 72,000 | critical |

Mode contracts are validated in CI against the schema in `.internal/specs/core/agent-mode-contract.yaml`.

### Budget Governance
- Each mode declares explicit multidimensional budgets (input/output/context tokens, iterations, handoffs, timeout)
- Budget exceeded triggers `fail_fast` by default
- Handoff payloads use `summary+refs` compression with rehydration support
- Budget conservation: `sum(children) <= parent` for delegated workflows

### Memory Model
- **Operational Context:** Ephemeral, compressible, current operation state
- **Session State:** Session-scoped, compressible, run-level accumulations
- **Structural Memory:** Persistent, non-compressible, project conventions and architecture
- Evidence references must NEVER be compressed in handoffs

### Satisficing Profiles
- **URGENT:** Speed over quality, early exit permitted
- **ECONOMICAL:** Cost-optimized, acceptable quality floor
- **BALANCED:** Trade-off between quality and cost (default)
- **DEEP:** Thoroughness over speed, no early exit (reviewer)

## Swarm Rules

- Use MCP only for context that lives outside the repository or changes frequently.
- Check `/mcp` before starting a multi-agent swarm run and stop if a required server is missing.
- Use `docs_researcher` for version-sensitive facts or official external documentation lookups.
- Treat the workflow as artifact-first: worker outputs belong under `.internal/artifacts/codex-swarm/<run-id>/`.
- Keep `write_scope` disjoint across parallel workers.
- `verifier` is the mandatory gate before `synthesizer`.
- `synthesizer` is the single final writer for the run package.
- When live session state matters, pass a `--session-snapshot` JSON file to `.internal/scripts/codex_swarm_prepare.py` so the run manifest records the effective overrides.
- Mode contracts in `opencode.json` are light bindings; the source of truth is the YAML contract.

## Domain Packs

Domain Packs are contractual extensions registered via `registry/registry.yaml`. They implement Core protocols but do not define them.

| Pack | Type | Status | Description |
|------|------|--------|-------------|
| `software-engineering` | functional | active | Default development workflow capabilities |
| `ml-ai` | vertical | experimental | ML/AI training, optimization, experiment tracking (optional, illustrative) |
| `medical-imaging` | vertical | experimental | Medical image analysis and reporting (optional, illustrative) |
| `ioi-gold-compiler` | vertical | experimental | Advanced algorithmic and competitive programming (optional, illustrative) |

> **Note:** Only `software-engineering` is active by default. All vertical packs are optional extensions. The Core does not depend on any Domain Pack.

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
- 99 Python tests across 12 classes in 6 suites: TestModeContractExistence, TestModeContractSchema, TestModeContractDrift, TestModeContractHandoffs, TestModeContractConstitutionalCompliance, TestCommandRoutingRegression, TestStableExecutionGuardrails, TestOpenCodeConfigParity, TestRuntimeIntegration, TestPublicVsInternalBoundary, TestSanitizedPublicConfigurationContract, TestPublicRepoAllowlistGovernance, TestOpencodeGovernance
- Run: `python -m pytest .internal/tests/ -v`
- Budget validation: `python .internal/scripts/validate_mode_budgets.py --fail-on-violation`

### CI Integration
- Routing regression: `.github/workflows/routing-regression.yml`
- Constitutional compliance: `.github/workflows/constitutional-compliance.yml`
- Mode contract compliance: `.github/workflows/mode-contract-compliance.yml`
- Config parity validated by critical routing fields only (not full JSON equality)

## Built-in OpenCode Agents — Ignorar

O runtime do OpenCode injeta automaticamente agentes built-in que aparecem no cycling via Tab mas **não devem ser usados** neste framework. Eles são redundantes com as skills integradas nos nossos modos contratuais:

| Built-in OpenCode | Substituído por | Modo |
|---|---|---|
| `conformance-auditor` | Skill `conformance_audit` | `reviewer` |
| `impact-analyst` | Skill `impact_analysis` | `explore` |
| `memory-curator` | Skill `memory_curation` | `orchestrator` |
| `policy-guardian` | Skill `policy_gate` | `reviewer` |
| `spec-architect` | Skill `spec_architecture` | `orchestrator` |
| `spec-compiler` | Skill `spec_compilation` | `orchestrator` |

**Regra:** Use apenas os 4 modos contratuais (`explore`, `reviewer`, `orchestrator`, `autocoder`) + `general` como fallback. Os built-ins são injetados pelo runtime e não podem ser desabilitados via `opencode.json` (ver [upstream issue #12498](https://github.com/anomalyco/opencode/issues/12498)).
