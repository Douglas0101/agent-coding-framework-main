---
description: Compila uma spec aprovada em DAG de TaskNodes com invariantes, policies e checks de verificação
usage: /compile-spec <spec_id> [--behavior <id>] [--policy <id>] [--verification <id>]
---

Este command compila um conjunto de specs versionadas em um DAG executável de TaskNodes.

## Pré-condições obrigatórias

1. A spec `<spec_id>` deve estar registrada com status `approved` no spec-registry.
2. A behavior spec, policy bundle e verification spec devem estar disponíveis.
3. O `run_id` atual deve ser fornecido ou gerado antes de chamar o compiler.

## Fluxo

1. Chame `assertSpecApproved(spec_id)` via `spec-registry` — aborte se falhar.
2. Resolva behavior, policy e verification specs associadas à capability spec.
3. Chame `compileDAG(...)` via `spec-compiler`.
4. Se `policy_violations.length > 0`, reporte cada violação como `[BLOCKED]` e não prossiga.
5. Se `requires_human_approval === true`, pause e solicite aprovação antes de executar.
6. Persista o DAG em `artifacts/codex-swarm/<run_id>/dag-compiled.json`.
7. Gere um `traceability-link` inicial da run com `run_id` real, `spec_id`, `dag_nodes` e requisitos/owners mínimos disponíveis.
8. Gere um `run-manifest` inicial com `status: running`, `dag_id` vinculado e `traceability_link_id` apontando para o artefato canônico de rastreabilidade.
9. Trate a completude de rastreabilidade como incremental: `code_refs`, `test_cases`, `evidence_refs` e `runtime_trace_ids` podem ser enriquecidos ao longo da run, mas o gate crítico continua em `assertMinimumLinks(...)` no momento de release/execução sensível.

## Output esperado

```json
{
  "dag_id": "dag_<run_id>_<timestamp>",
  "spec_id": "<spec_id>",
  "spec_version": "<version>",
  "nodes_count": <integer>,
  "execution_order": ["<task_id>", "..."],
  "policy_violations": [],
  "requires_human_approval": false
}
```

## Erros bloqueantes

- Spec não encontrada ou não aprovada → abortar com mensagem clara
- Policy violation → listar todas antes de abortar
- Sem transitions no behavior spec → abortar (DAG vazio não é válido)
- Dependência circular no DAG → abortar com nó problemático identificado
