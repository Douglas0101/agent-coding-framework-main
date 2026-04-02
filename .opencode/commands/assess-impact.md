---
description: Analisa o blast radius de uma mudança proposta — serviços, contratos, datastores, SLOs e consumidores afetados — antes de qualquer implementação
usage: /assess-impact <spec_id> [--change-surface <code|api|data|auth>] [--run-id <id>]
---

Este command quantifica o impacto de uma mudança antes que ela ocorra.
Produz um `impact-report` com `compatibility_assessment` e `blast_radius`.

## Fluxo obrigatório

1. **Resolver spec**: obtenha a spec via `getSpec(spec_id)` e extraia objetivos, contratos e invariantes.
2. **Mapear blast radius**: identifique:
   - arquivos de código potencialmente afetados (por grep de spec_id, capability_ref)
   - contratos OpenAPI, protobuf ou JSON Schema que referenciam a capability
   - datastores (presença de `datastores` na impact_scope da spec)
   - consumers agente-a-agente (handoffs que referenciam o contrato)
3. **Classificar compatibilidade**: use `spec-diff` se houver uma versão anterior da spec, ou classifique manualmente com base no `change_surface` fornecido:
   - `code` only → provável `behavior-compatible`
   - `api` → provável `risky-compatible` ou `breaking`
   - `data` + `auth` → provável `breaking`
4. **Calcular risk_level**: baseie-se em `blast_radius` total + `change_surface` + presença de SLOs afetados.
5. **Gerar evidence_refs mínimos**: liste arquivos analisados como refs.
6. **Persistir**: salve em `artifacts/codex-swarm/<run_id>/impact-report.json`.

## Output esperado

```json
{
  "schema_version": "1.0.0",
  "artifact_type": "impact-report",
  "producer_agent": "impact-analyst",
  "spec_id": "<spec_id>",
  "spec_version": "<version>",
  "run_id": "<run_id>",
  "compatibility_assessment": "risky-compatible",
  "payload": {
    "impact_scope": {
      "services": ["<serviço>"],
      "contracts": ["<contrato>"],
      "datastores": ["<datastore>"],
      "slos": ["<slo>"]
    },
    "risk_level": "high",
    "blast_radius": {
      "files": 12,
      "apis": 3,
      "consumers": 7,
      "databases": 2
    }
  },
  "trace_links": ["trace://requirement/<id>"],
  "evidence_refs": ["evidence://repo/<path>"]
}
```

## Regras

- Todo impacto classificado como `breaking` deve gerar alerta de bloqueio imediato.
- `blast_radius.consumers > 5` eleva automaticamente o risk_level para `high`.
- O impact-report é pré-requisito para `/compile-spec` quando `risk_level >= high`.
