# ADR-004: Skill Contract

**Status:** aceito  
**Data:** 2026-04-04  
**Decisor:** core-team  
**Contexto:** PRD Framework 2.0, RF-06, ADR-001 (Taxonomia)

## Problema

Skills são capacidades incrementais por modo, mas sem contrato formal há risco de:
1. Skills ativando sem critério claro
2. Consumo de budget não monitorado
3. Saídas sem validação de qualidade
4. Proliferação sem lifecycle

## Decisão

### Skill Contract Schema

Toda skill deve declarar:

```yaml
skill_contract:
  metadata:
    name: string                    # Identificador único
    version: string                 # Semver
    target_mode: string             # Modo-alvo (explore|reviewer|orchestrator|autocoder)
    source: string                  # Origem (opencode-builtin, internal, domain-pack)

  activation:
    trigger: enum [automatic, manual, conditional]
    condition: string               # Expressão de ativação (se conditional)
    priority: enum [critical, high, medium, low]

  input_contract:
    schema: string                  # Schema de entrada esperado
    required_fields: list[FieldDef]
    optional_fields: list[FieldDef]

  output_contract:
    schema: string                  # Schema de saída produzido
    required_fields: list[FieldDef]
    format: string                  # json, markdown, yaml

  budget:
    budget_share: float             # Fração do budget do modo (0.0-1.0)
    max_tokens: integer             # Teto absoluto em tokens
    timeout_seconds: integer        # Timeout da skill

  evidence:
    policy: enum [none, minimal, full]
    artifacts: list[string]         # Artefatos de evidência produzidos
    retention: enum [ephemeral, session, persistent]

  testing:
    regression_tests: list[string]  # Testes obrigatórios
    golden_traces: list[string]     # Traces de referência

  justification:
    why_not_core: string            # Por que não pertence ao Core
    why_not_domain_pack: string     # Por que não pertence a um Domain Pack
```

### Regras de Validação

| Rule ID | Descrição |
|---------|-----------|
| SKL-001 | target_mode deve referenciar modo existente |
| SKL-002 | budget_share deve estar em [0.0, 1.0] |
| SKL-003 | Sum de budget_share por modo <= 1.0 |
| SKL-004 | source deve ser origem conhecida |
| SKL-005 | must have regression_tests se priority = critical |
| SKL-006 | why_not_core e why_not_domain_pack devem ser não-vazios |

### Lifecycle de Skill

1. **Proposta:** skill declarada com contrato completo
2. **Validação:** CI valida schema + regras
3. **Ativação:** skill vinculada ao modo-alvo
4. **Monitoramento:** consumo e evidência rastreados
5. **Revisão:** revisão periódica de relevância
6. **Depreciação:** remoção com migração se necessário

### Skills Existentes (Linha de Base)

| Modo | Skill | Budget Share | Verifier |
|------|-------|-------------|----------|
| explore | impact_analysis | 0.30 | false |
| reviewer | conformance_audit | 0.35 | true |
| reviewer | policy_gate | 0.25 | true |
| orchestrator | memory_curation | 0.15 | false |
| orchestrator | spec_architecture | 0.25 | true |
| orchestrator | spec_compilation | 0.20 | true |
| autocoder | *(nenhuma)* | 0.00 | n/a |

## Consequências

### Positivas
- Governança clara de novas capacidades
- Budget controlado por skill
- Justificativa obrigatória evita duplicação

### Negativas
- Overhead de documentação para skills simples
- Necessidade de manter contratos atualizados

## Alternativas rejeitadas

1. **Skills sem contrato:** rejeitado porque impede governança
2. **Skills como agentes independentes:** rejeitado porque viola princípio de 4 modos
