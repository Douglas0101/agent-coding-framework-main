---
description: Planeja uma mudança de sistema a partir de uma intent ou RFC, gerando specs mínimas e avaliando impacto antes de qualquer implementação
usage: /plan-system "<intent>" [--domain <domain>] [--risk <low|medium|high|critical>]
---

Este command implementa o fluxo spec-first: `intent → canonical spec → compiled plan`.
Nenhuma linha de código é escrita antes de uma spec aprovada existir.

## Fluxo obrigatório

1. **Capturar intent**: receba a descripção de negócio ou RFC como entrada livre.
2. **Gerar rascunho de capability spec**: crie um arquivo draft em `.opencode/specs/capabilities/<domain>.capability.yaml` com:
   - `spec_id`, `version: 1.0.0`, `status: draft`
   - `objective` derivado da intent
   - `inputs` e `outputs` inferidos
   - `invariants` mínimos (ao menos 2)
3. **Gerar rascunho de behavior spec**: crie `.opencode/specs/behaviors/<domain>.behavior.yaml` com estados e transições derivados da intent.
4. **Gerar rascunho de verification spec**: crie `.opencode/specs/verification/<domain>.verification.yaml` com acceptance_criteria derivados das invariantes.
5. **Avaliar impacto**: identifique quais serviços, contratos, datastores e SLOs são afetados pela mudança planejada.
6. **Calcular risk_level**: use os critérios do relatório (scope, blast radius, change_surface).
7. **Apresentar**: entregue um resumo estruturado com spec IDs criados, risk_level calculado, impacto estimado e próximos passos.

## Saída esperada

```
PLANO DE SISTEMA
================
Intent: <resumo da intent>
Domain: <domain>
Risk Level: <risk>

Specs rascunhadas:
  - capability: .opencode/specs/capabilities/<domain>.capability.yaml [draft]
  - behavior:   .opencode/specs/behaviors/<domain>.behavior.yaml [draft]
  - verification: .opencode/specs/verification/<domain>.verification.yaml [draft]

Impacto estimado:
  - Serviços afetados: <lista>
  - Contratos impactados: <lista>
  - Datastores: <lista>
  - SLOs em risco: <lista>

Próximos passos:
  1. Revisar e aprovar specs com stakeholders
  2. Executar /compile-spec <spec_id> após aprovação
  3. Executar /assess-impact para blast radius detalhado
```

## Regras

- Não iniciar implementação antes de spec em status `approved`.
- Não criar specs com `objective` genérico — deve ser verificável e mensurável.
- `invariants` devem ter ao menos 2 itens verificáveis por máquina.
