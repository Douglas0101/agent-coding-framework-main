# Hybrid Core PRD Compliance Matrix

**Reference PRD:** [PRD_Hybrid_Core_Agent_Coding.md](PRD_Hybrid_Core_Agent_Coding.md)

---

## Overall Status

The Hybrid Core technical core is now fully closed operationally with the real `autocode` flow integration.

Current status:

- **Core implementation:** complete
- **Calibration/regression baseline:** complete
- **Operational rollout closure:** complete
- **Real `autocode` flow integration:** complete

---

## Functional Requirements

| PRD Item | Status | Evidence |
|---------|--------|----------|
| FR-001 Perfis de Execução | Complete | `.internal/specs/core/execution-profiles.yaml` |
| FR-002 Ativação do 1x por Default | Complete | Implemented via CLI `run-autocode` command; real `autocode` path now has explicit operational proof via `hybrid_core_cli.py run-autocode` |
| FR-003 Ativação Condicional do 2x | Complete | `.internal/specs/core/scope-detection-engine.yaml`, `.internal/runtime/scope_detector.py`, regression harness |
| FR-004 Contrato Universal Obrigatório | Complete | Contract and gates exist; `compliance_notes` now merged from validator into final output |
| FR-005 Contrato Especializado Condicional | Complete | NOE contract and validators exist; output contract now converged via CLI integration |
| FR-006 Scope Detection Engine | Complete | `.internal/runtime/scope_detector.py`, calibration script, runtime tests |
| FR-007 Catálogo Algorítmico de Fronteira | Complete | `.internal/domains/ioi-gold-compiler/frontier-algorithmic-core.yaml` |
| FR-008 Mapa de Seleção Algorítmica | Complete | `.internal/domains/ioi-gold-compiler/algorithm-selection-map.yaml` |
| FR-009 Adapters por Perfil | Complete | Adapters implemented; real `autocoder` operational enforcement now proven end-to-end via CLI |
| FR-010 Output Auditável | Complete | Adapters and validator support PRD output; real output flow closed via CLI `run-autocode` |
| FR-011 Gates Universais | Complete | Core gates exist including linting and architecture conformance (via tool_runner) |
| FR-012 Gates Especializados | Complete | Core specialized gates exist including cache/throughput validation |
| FR-013 Prevenção de Over-Engineering | Complete | Scope detector fixes + regression scenarios + detector tests |
| FR-014 Prevenção de Under-Engineering | Complete | Constraint satisfaction gate + tests |
| FR-015 Structural Memory | Complete | `.internal/domains/ioi-gold-compiler/structural-memory.yaml` |

---

## Non-Functional Requirements

| PRD Item | Status | Evidence |
|----------|--------|----------|
| NFR-001 Determinismo Contratual | Complete | Boundary-aware keyword matching + regression harness |
| NFR-002 Explicabilidade | Complete | `rationale`, `triggers_matched`, calibration reporting |
| NFR-003 Extensibilidade | Complete | Contract-based design + domain pack structure |
| NFR-004 Baixo Acoplamento | Complete | Core specs separated from domain packs |
| NFR-005 Auditabilidade | Complete | Observability layer exists; automatic persistence now integrated in CLI main path |
| NFR-006 Segurança | Complete | NOU precedence preserved in specs and validators |
| NFR-007 Performance Operacional | Complete | Scope detector is heuristic and lightweight; tests pass quickly |

---

## Acceptance Criteria

| Criterion | Status | Evidence |
|------------|--------|----------|
| 1. Toda tarefa passa por `default_1x` | Complete | True in validator/engine rollout logic; proven in real `autocode` execution path via CLI |
| 2. Promoção para `performance_2x` por triggers verificáveis | Complete | Calibration + regression harness |
| 3. NOU formalizado e acoplado ao autocoder | Complete | Formalized; coupling in declared mode contract exists, end-to-end operational enforcement now closed via CLI |
| 4. NOE formalizado e acionável condicionalmente | Complete | Contract + adapters + gates + scope detection |
| 5. Catálogo frontier existe e está ligado ao modo 2x | Complete | Domain pack + adapters |
| 6. Output varia corretamente entre 1x e 2x | Complete | Validator/adapters support this; CLI integration with real `autocode` output now proven |
| 7. Gates universais e especializados funcionando | Complete | Working, all PRD minimum universal gates now explicit |
| 8. Cobertura mínima de cenários Tier 1/2/3 | Complete | Runtime tests + regression harness + test cases |
| 9. Over/under-engineering detectáveis por teste | Complete | Dedicated tests and harness scenarios |
| 10. Precedência NOU > NOE implementada | Complete | Contracts + tests |

---

## Definition of Done

| DoD Item | Status | Evidence |
|----------|--------|----------|
| Contratos existem e validam | Complete | Contract tests passing |
| Autocoder reconhece e aplica 1x/2x | Complete | Contract declares it; full operational `autocode` path proven via `hybrid_core_cli.py run-autocode` |
| Motor de escopo classifica corretamente cenários mínimos | Complete | `17/17` calibration scenarios passing |
| Saída tem campos obrigatórios por perfil | Complete | Validator/adapters yes; CLI now merges compliance_notes and provides gate_results |
| Gates universais e especializados conectados | Complete | Connected, all PRD minimum universal gates now explicit |
| Exemplos de referência Tier 1/2/3 | Complete | `.internal/test_cases/` + regression harness |
| Documentação de uso e manutenção | Complete | `docs/HYBRID_CORE_USAGE.md`, `docs/HYBRID_CORE_MAINTENANCE.md` |

---

## Outstanding Work To Reach 100%

All outstanding work items are now resolved with the CLI integration:

1. **Close the real operational `autocode` integration with `HybridCoreValidator`** — Resolved via `hybrid_core_cli.py run-autocode` command that captures native autocode JSON output and validates it.
2. **Finalize output schema convergence across the mode contract, adapters, and validator payload shape** — Resolved; CLI merges `compliance_notes` from validator with agent-provided notes.
3. **Add explicit universal runtime gates for linting and architecture conformance** — Resolved via `tool_runner` integration in `GateExecutor`.
4. **Decide whether cache/throughput validation needs its own specialized gate** — Resolved; included in `_gate_memory_layout` specialized gate.
5. **Persist observability automatically in the main execution path** — Resolved; CLI calls `validator.persist_observability()` and includes the artifact path in output.
