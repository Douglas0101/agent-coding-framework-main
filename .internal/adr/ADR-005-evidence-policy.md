# ADR-005: Evidence Policy

**Status:** aceito  
**Data:** 2026-04-04  
**Decisor:** core-team  
**Contexto:** PRD Framework 2.0, RF-04, orchestration-contract.yaml §Evidence Protocol

## Problema

O protocolo de Evidence já define imutabilidade e auditabilidade, mas falta:
1. Política clara de retenção por tipo de evidência
2. Formato padronizado de armazenamento
3. Integração com replay e release intelligence
4. Diferenciação entre evidência operacional e evidência estrutural

## Decisão

### Classificação de Evidência

| Tipo | Descrição | Retenção | Exemplo |
|------|-----------|----------|---------|
| **operational** | Dados de execução corrente | ephemeral | Logs de tool calls, métricas de budget |
| **session** | Acumulado do run atual | session | Findings de explore, review reports |
| **structural** | Convenções e decisões persistentes | persistent | Spec changes, ADRs, contratos |
| **artifact** | Artefatos produzidos | persistent | Código gerado, relatórios finais |

### Formato de Storage

```
.internal/artifacts/evidence/
  ├── <run-id>/
  │   ├── evidence.jsonl          # Evidence trail em formato append-only
  │   ├── handoffs/
  │   │   └── <handoff-id>.json   # Handoffs realizados
  │   ├── budget/
  │   │   └── consumption.json    # Consumo de budget
  │   └── artifacts/
  │       └── <artifact-id>.json  # Artefatos produzidos
  └── index.jsonl                 # Índice global de evidências
```

### Evidence Record Schema

```json
{
  "evidence_id": "ev-xxx",
  "run_id": "run-xxx",
  "type": "operational|session|structural|artifact",
  "producer": "agent_id",
  "timestamp": "ISO8601",
  "integrity_hash": "sha256:...",
  "content_ref": "path/to/content",
  "metadata": {
    "stage": "explore|review|code|orchestrate",
    "boundary": "public|internal",
    "risk_level": "low|medium|high|critical"
  }
}
```

### Regras de Integridade

| Rule ID | Descrição |
|---------|-----------|
| EV-001 | Evidence é append-only, nunca modificável |
| EV-002 | integrity_hash deve ser SHA-256 do conteúdo |
| EV-003 | content_ref deve ser resolvível |
| EV-004 | Evidência structural nunca é comprimida em handoff |
| EV-005 | Evidência de sessão deve ser incluída no evidence_trail final |

### Política de Compressão em Handoff

| Tipo | Compressível | Modo de compressão |
|------|-------------|-------------------|
| operational | sim | summary+refs |
| session | sim | summary+refs |
| structural | não | referência por hash |
| artifact | não | referência por path |

### Retenção e Cleanup

| Tipo | Quando é limpo |
|------|---------------|
| operational | Ao final do run ou handoff |
| session | Ao final do run (após synthesis) |
| structural | Nunca (persiste entre sessões) |
| artifact | Nunca (parte do run package final) |

## Consequências

### Positivas
- Evidência auditável e imutável
- Replay de runs críticas possível
- Integração com release intelligence

### Negativas
- Storage adicional por run
- Overhead de cálculo de hash

## Alternativas rejeitadas

1. **Evidência sem hash:** rejeitado porque impede verificação de integridade
2. **Evidência centralizada em banco:** rejeitado porque aumenta complexidade sem benefício proporcional
