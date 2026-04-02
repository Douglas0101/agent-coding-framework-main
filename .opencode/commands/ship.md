---
description: "Orquestra entrega de código com pipeline completo"
agent: orchestrator
subtask: false
---

Orquestre a entrega de codigo com pipeline completo.

## Pipeline obrigatorio

1. **Analise**: `@explore` — mapear escopo, impacto, riscos, harness
2. **Hipoteses** (se complexo): `@hypothesis` — gerar abordagens testaveis
3. **Evidencia** (se riscoso): `@evidence` — coletar fatos verificaveis
4. **Verificacao de fontes** (se ha citacoes): `@citation` — grading de credibilidade
5. **Implementacao**: `@general` — codificar mudancas
6. **Revisao**: `@reviewer` — severity classification
7. **Validacao**: `@tester` — harness discovery + execucao
8. **Verificacao independente** (se critico): `@validation` — confirmar
9. **Deteccao de contradicoes** (se multiplas fontes): `@contradiction` — resolver conflitos
10. **Sintese**: `@synthesis` — consolidar achados
11. **Identificacao de lacunas**: `@gap` — verificar cobertura

## Confidence gates

- confidence < 0.75 apos qualquer etapa → replan com `@hypothesis`
- reviewer severity = critical → retorna para implementacao
- validation verdict = fail → retorna para review com feedback
- evidence coverage < 0.60 → bloqueia sintese, pede mais evidencia
- contradicao detectada → invoke `@contradiction` antes de sintese
- `@gap` critical_gaps_count > 0 → resolva antes de concluir
- orcamento de steps excedido → simplifique o plano ou solicite aprovacao humana

## Escopo

`$ARGUMENTS`
