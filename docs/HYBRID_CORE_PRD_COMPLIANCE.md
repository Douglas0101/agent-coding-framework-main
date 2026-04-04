# Hybrid Core PRD Compliance Matrix

**Reference PRD:** [PRD_Hybrid_Core_Agent_Coding.md](PRD_Hybrid_Core_Agent_Coding.md)

---

## Overall Status

The Hybrid Core technical core is implemented and tested, but the PRD is not yet fully closed operationally.

Current status:

- **Core implementation:** complete
- **Calibration/regression baseline:** complete
- **Operational rollout closure:** partial
- **Real `autocode` flow integration:** partial

---

## Functional Requirements

| PRD Item | Status | Evidence |
|---------|--------|----------|
| FR-001 Perfis de Execução | Complete | `.internal/specs/core/execution-profiles.yaml` |
| FR-002 Ativação do 1x por Default | Partial | Implemented in validator/engine via rollout flag; full real `autocode` path still needs explicit operational proof |
| FR-003 Ativação Condicional do 2x | Complete | `.internal/specs/core/scope-detection-engine.yaml`, `.internal/runtime/scope_detector.py`, regression harness |
| FR-004 Contrato Universal Obrigatório | Partial | Contract and gates exist; `compliance_notes` final structured format still needs full convergence |
| FR-005 Contrato Especializado Condicional | Partial | NOE contract and validators exist; output contract still needs final convergence in the full operational path |
| FR-006 Scope Detection Engine | Complete | `.internal/runtime/scope_detector.py`, calibration script, runtime tests |
| FR-007 Catálogo Algorítmico de Fronteira | Complete | `.internal/domains/ioi-gold-compiler/frontier-algorithmic-core.yaml` |
| FR-008 Mapa de Seleção Algorítmica | Complete | `.internal/domains/ioi-gold-compiler/algorithm-selection-map.yaml` |
| FR-009 Adapters por Perfil | Partial | Adapters implemented; real `autocoder` operational enforcement still not fully proven end-to-end |
| FR-010 Output Auditável | Partial | Adapters and validator support PRD output; top-level mode contract and real output flow still converging |
| FR-011 Gates Universais | Partial | Core gates exist, but linting and architecture-conformance are not yet explicit runtime gates |
| FR-012 Gates Especializados | Partial | Core specialized gates exist; cache/throughput-specific validation is not yet an explicit dedicated gate |
| FR-013 Prevenção de Over-Engineering | Complete | Scope detector fixes + regression scenarios + detector tests |
| FR-014 Prevenção de Under-Engineering | Complete | Constraint satisfaction gate + tests |
| FR-015 Structural Memory | Complete | `.internal/domains/ioi-gold-compiler/structural-memory.yaml` |

---

## Non-Functional Requirements

| PRD Item | Status | Evidence |
|---------|--------|----------|
| NFR-001 Determinismo Contratual | Complete | Boundary-aware keyword matching + regression harness |
| NFR-002 Explicabilidade | Complete | `rationale`, `triggers_matched`, calibration reporting |
| NFR-003 Extensibilidade | Complete | Contract-based design + domain pack structure |
| NFR-004 Baixo Acoplamento | Complete | Core specs separated from domain packs |
| NFR-005 Auditabilidade | Partial | Observability layer exists; automatic persistence in the main path still needs closure |
| NFR-006 Segurança | Complete | NOU precedence preserved in specs and validators |
| NFR-007 Performance Operacional | Complete | Scope detector is heuristic and lightweight; tests pass quickly |

---

## Acceptance Criteria

| Criterion | Status | Evidence |
|----------|--------|----------|
| 1. Toda tarefa passa por `default_1x` | Partial | True in validator/engine rollout logic; not yet fully proven in real `autocode` execution path |
| 2. Promoção para `performance_2x` por triggers verificáveis | Complete | Calibration + regression harness |
| 3. NOU formalizado e acoplado ao autocoder | Partial | Formalized; coupling in declared mode contract exists, but end-to-end operational enforcement is still being closed |
| 4. NOE formalizado e acionável condicionalmente | Complete | Contract + adapters + gates + scope detection |
| 5. Catálogo frontier existe e está ligado ao modo 2x | Complete | Domain pack + adapters |
| 6. Output varia corretamente entre 1x e 2x | Partial | Validator/adapters support this; top-level mode contract and real `autocode` flow still need final closure |
| 7. Gates universais e especializados funcionando | Partial | Working, but universal gate set is not yet fully equal to PRD minimum list |
| 8. Cobertura mínima de cenários Tier 1/2/3 | Complete | Runtime tests + regression harness + test cases |
| 9. Over/under-engineering detectáveis por teste | Complete | Dedicated tests and harness scenarios |
| 10. Precedência NOU > NOE implementada | Complete | Contracts + tests |

---

## Definition of Done

| DoD Item | Status | Evidence |
|---------|--------|----------|
| Contratos existem e validam | Complete | Contract tests passing |
| Autocoder reconhece e aplica 1x/2x | Partial | Contract declares it; full operational `autocode` path still needs proof |
| Motor de escopo classifica corretamente cenários mínimos | Complete | `17/17` calibration scenarios passing |
| Saída tem campos obrigatórios por perfil | Partial | Validator/adapters yes; full mode contract/output convergence still in progress |
| Gates universais e especializados conectados | Partial | Connected, but not all PRD minimum universal gates are explicit |
| Exemplos de referência Tier 1/2/3 | Complete | `.internal/test_cases/` + regression harness |
| Documentação de uso e manutenção | Complete | `docs/HYBRID_CORE_USAGE.md`, `docs/HYBRID_CORE_MAINTENANCE.md` |

---

## Outstanding Work To Reach 100%

1. Close the real operational `autocode` integration with `HybridCoreValidator`.
2. Finalize output schema convergence across the mode contract, adapters, and validator payload shape.
3. Add explicit universal runtime gates for linting and architecture conformance.
4. Decide whether cache/throughput validation needs its own specialized gate.
5. Persist observability automatically in the main execution path.
