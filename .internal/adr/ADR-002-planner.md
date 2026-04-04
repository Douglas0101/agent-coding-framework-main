# ADR-002: Planner Explícito

**Status:** aceito  
**Data:** 2026-04-04  
**Decisor:** core-team  
**Contexto:** PRD Framework 2.0, RF-02, planner-subcontract.yaml existente

## Problema

O planejamento era implícito no orquestrador, causando:
1. Planos não estruturados, sem pré/pós-condições formais
2. Budget allocation ad-hoc entre steps
3. Sem critério de encerramento explícito
4. Dificuldade de replay e auditoria

Já existe um `planner-subcontract.yaml` no Core, mas ele não está operacionalizado como módulo executável.

## Decisão

### Arquitetura

O planner será um **subcontrato formal do orchestrator**, não um agente independente. Isso preserva os 4 modos como superfície principal.

```
orchestrator
  └── planner (subcontrato)
        ├── input: task, available_modes, parent_budget
        ├── output: plan_id, steps[], dependencies, budget_allocation, risk_assessment
        └── validation: PLN-001 a PLN-006
```

### Contrato de Entrada

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| task | string | sim | Descrição de alto nível |
| available_modes | list[string] | sim | Modos disponíveis para assignment |
| parent_budget | dict | sim | Budget alocado pelo pai |
| constraints | list[string] | não | Restrições adicionais |
| previous_plan | string | não | Referência a plano anterior |

### Contrato de Saída

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| plan_id | string | sim | Identificador único |
| steps | list[Step] | sim | Steps ordenados |
| budget_allocation | dict | sim | Budget por step |
| dependencies | list[Dependency] | sim | Grafo de dependências |
| risk_assessment | dict | sim | Avaliação de risco |

### Lei de Conservação de Budget

```
sum(step.budget) * 1.10 <= parent_budget
```

O overhead de coordenação é 10% do budget total dos steps.

### Validações Obrigatórias

| Rule ID | Descrição |
|---------|-----------|
| PLN-001 | Steps referenciam modos válidos |
| PLN-002 | Sem dependências circulares |
| PLN-003 | Budget não excede parent |
| PLN-004 | Cada step tem ≥ 1 pre-condition |
| PLN-005 | Cada step tem ≥ 1 post-condition |
| PLN-006 | Steps paralelos têm write scopes disjuntos |

### Ferramentas Permitidas

- **Allowlist:** read, glob, grep, task, codesearch
- **Denylist:** edit, write, bash (planner não modifica arquivos)

## Consequências

### Positivas
- Planos estruturados e auditáveis
- Budget allocation verificável
- Replay de decisões de planejamento
- Separação clara entre planejar e executar

### Negativas
- Overhead de token para geração do plano
- Planner consome budget do orchestrator

## Alternativas rejeitadas

1. **Planner como 5º modo:** rejeitado porque viola princípio de 4 modos como superfície principal
2. **Planner implícito continuar:** rejeitado porque impede auditabilidade e replay
