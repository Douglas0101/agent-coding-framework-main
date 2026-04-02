---
description: "Executa tarefas de coding com raciocinio sequencial planejado"
agent: autocoder
subtask: false
---

Execute tarefas de engenharia ponta a ponta com raciocínio sequencial planejado.

## Fluxo

1. Analise o escopo: `$ARGUMENTS`
2. Se complexo/riscoso: colete evidências com `@evidence` antes de implementar
3. Implemente com `@general`
4. Revise com `@reviewer` (severity classification obrigatória)
5. Valide com `@tester` (harness discovery protocol)
6. Se crítico: verifique com `@validation` (independente)
7. Entrega relatório operacional estruturado

## Output esperado

Relatório JSON com: objective, scope_executed, agents_activated, decisions, files_changed, confidence, remaining_risks, next_steps.
