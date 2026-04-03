---
description: "Faz revisão técnica com severity classification"
agent: reviewer
subtask: false
---

Faca revisao tecnica da mudanca atual ou do escopo: `$ARGUMENTS`.

## Verificacao obrigatoria

- Classifique CADA finding por severity: critical, major, minor, suggestion
- Verifique: bugs, regressoes, seguranca, performance, acoplamento, lacunas de testes
- Confirme conformidade com harness e regras do projeto

## Output esperado

JSON com: findings[], severity_matrix, overall_risk, confidence, recommendations[].

Se `overall_risk` for critical, declare explicitamente que a mudanca NAO deve prosseguir.

## Guardrails

- Este command permanece read-only: `write`, `edit`, `bash` e `webfetch` devem seguir negados.
- O fluxo de revisao nao deve tentar contornar limites de passos ou solicitar `doom_loop`.
