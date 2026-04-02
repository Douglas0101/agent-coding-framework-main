---
description: "Analisa escopo, arquitetura, impacto e harness"
agent: explore
subtask: false
---

Analise o escopo fornecido em `$ARGUMENTS`.

## Verificacao obrigatoria

- Examine a arquitetura do modulo/componente
- Identifique impacto em outros modulos
- Mapeie o harness aplicavel (Makefile, pytest, ruff, mypy)
- Identifique riscos de regressao

## Output esperado

JSON estruturado com: scope, architecture_analysis, impact_map, harness_available, risks[], recommendations[].

Nao execute mudancas, apenas analise e reporte.
