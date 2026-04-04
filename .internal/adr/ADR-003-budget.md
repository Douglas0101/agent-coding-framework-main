# ADR-003: Budget Multidimensional

**Status:** aceito  
**Data:** 2026-04-04  
**Decisor:** core-team  
**Contexto:** PRD Framework 2.0, RF-03, agent-mode-contract.yaml §resources

## Problema

O framework já declara budgets por modo em `opencode.json` (maxSteps), mas isso é insuficiente para controle real de custo. O PRD exige budget multidimensional verificável com bloqueio runtime de excesso.

## Decisão

### Dimensões de Budget

Cada modo opera com 7 dimensões de budget:

| Dimensão | Descrição | Unidade |
|----------|-----------|---------|
| input_tokens | Tokens de entrada do LLM | integer |
| output_tokens | Tokens de saída do LLM | integer |
| context_tokens | Janela de contexto total | integer |
| retrieval_chunks | Chunks de retrieval por query | integer |
| iterations | Iterações de execução | integer |
| handoffs | Handoffs para outros modos | integer |
| timeout | Wall-clock execution time | segundos |

### Política de Enforcement

| Situação | Ação |
|----------|------|
| Budget excedido | `fail_fast` por padrão |
| Budget > 80% | Warning + memory curation trigger |
| Budget > 90% | Warning crítico + early exit se habilitado |
| Budget = 100% | Bloqueio imediato, registro de causa |

### Hierarquia de Budget

```
parent_budget >= sum(children_budgets) * 1.10
```

O planner aloca budget para cada step com 10% de overhead de coordenação.

### Tracking Runtime

Cada execução deve registrar:
- Budget inicial por dimensão
- Consumo acumulado por dimensão
- Causa de falha se budget excedido
- Timestamp de cada checkpoint de consumo

### Regras de Validação

| Rule ID | Descrição |
|---------|-----------|
| BUD-001 | Todos os valores devem ser inteiros positivos |
| BUD-002 | handoff_payload_budget.max_tokens <= max_context_tokens |
| BUD-003 | Sum de skill budget_share <= 1.0 por modo |
| BUD-004 | retry_max <= 3 (invariante constitucional) |
| BUD-005 | Budget de children <= budget do parent |

### Formato de Registro de Consumo

```json
{
  "run_id": "run-xxx",
  "mode": "explore",
  "budget": {
    "input_tokens": {"allocated": 8000, "consumed": 6200, "remaining": 1800},
    "output_tokens": {"allocated": 12000, "consumed": 9400, "remaining": 2600},
    "context_tokens": {"allocated": 16000, "consumed": 14000, "remaining": 2000},
    "retrieval_chunks": {"allocated": 20, "consumed": 15, "remaining": 5},
    "iterations": {"allocated": 15, "consumed": 12, "remaining": 3},
    "handoffs": {"allocated": 2, "consumed": 1, "remaining": 1},
    "timeout_seconds": {"allocated": 300, "consumed": 245, "remaining": 55}
  },
  "status": "within_budget",
  "timestamp": "2026-04-04T00:00:00Z"
}
```

## Consequências

### Positivas
- Controle real de custo por execução
- Prevenção de runaway token consumption
- Auditabilidade de consumo por modo

### Negativas
- Overhead de tracking em cada operação
- Complexidade adicional no runtime

## Alternativas rejeitadas

1. **Budget único (apenas tokens):** rejeitado porque não captura custo real de iterações, handoffs e tempo
2. **Budget sem bloqueio (apenas warning):** rejeitado porque não previne custos excessivos
