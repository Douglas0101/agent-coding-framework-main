---
name: refactor-patterns
description: Governança obrigatória de design patterns com detecção de code smells e gate bloqueante no swarm
---

# Refactor Patterns Skill

## Objetivo

Aplicar governança de design patterns como regra obrigatória do sistema, com
gate bloqueante para detectar smells estruturais, acoplamento indevido e impacto
de deleção de módulos.

## Quando usar

- Sempre que houver refatoração, inclusão de endpoints, reorganização de módulos
  ou exclusão de arquivos Python.
- Sempre que rodar `scripts/rpa_swarm.py` (agente `design_patterns` faz parte do
  baseline dos goals principais).

## Gate oficial

Script canônico:

```bash
python .agent/skills/refactor-patterns/scripts/design_pattern_gate.py --report --scan-path src
```

Parâmetros úteis:

```bash
python .agent/skills/refactor-patterns/scripts/design_pattern_gate.py \
  --report \
  --scan-path src \
  --max-method-lines 50 \
  --max-class-lines 300 \
  --max-class-methods 20 \
  --max-if-chain 4
```

Para validação explícita de deleções (quando necessário):

```bash
python .agent/skills/refactor-patterns/scripts/design_pattern_gate.py \
  --report \
  --scan-path src \
  --deleted-python-file src/path/removido.py
```

## Regras (IDs)

- `DP001` (`high`): `Long Method` acima de `--max-method-lines`.
- `DP002` (`high`): `Large Class` por linhas totais ou quantidade de métodos.
- `DP003` (`critical`): cadeia `if/elif` excessiva; exigir Strategy/Polimorfismo.
- `DP004` (`medium`): endpoint HTTP com regra de negócio inline (router não
  deve carregar lógica de domínio).
- `DP900` (`critical`): impacto de deleção não resolvido.
  Se um módulo removido ainda for referenciado, falha.
  Em `CI=true`, se não for possível avaliar diff git, o gate falha em modo
  fail-closed.
- `DP901` (`high`): erro de sintaxe que impede análise AST.

## Critério de aprovação

- O gate falha (`exit 1`) se houver qualquer `critical` ou `high`.
- `medium/low/info` não bloqueiam sozinhos.
- Erro de execução retorna `exit 2` e também deve ser tratado como bloqueante no CI.

## Artefatos

- `artifacts/design_patterns/design_patterns_summary.json`
- `artifacts/design_patterns/design_patterns_report.txt`

Campos principais do JSON:

- `pass`
- `summary` (contagem por severidade)
- `findings`
- `breaches`

## Integração com o Swarm

- Agente: `design_patterns` (`skill_name=refactor-patterns`).
- Comando do agente: `design_pattern_gate.py --report --scan-path src`.
- `blocking=True` no registro.
- Rulebook padrão também força `design_patterns` como bloqueante
  (`config/swarm_policy_rulebook.json -> defaults.force_blocking_agents`).
- Remover esse agente via filtros (`include/exclude/skip`) quebra a execução.

## Runbook de remediação

1. Rodar o gate e identificar IDs críticos/altos.
2. Corrigir arquitetura com pattern apropriado (Extract Method/Class, Strategy,
   Service Layer/Use Case).
3. Em deleção de arquivos, remover imports/referências órfãs antes do merge.
4. Reexecutar gate até `pass=true` com `critical=0` e `high=0`.
