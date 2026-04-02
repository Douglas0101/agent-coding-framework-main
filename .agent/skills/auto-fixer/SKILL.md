---
name: auto-fixer
description: Agente responsável por auto-correções formativas
metadata:
  adapter: command
  mode: write
---

# Auto-Fixer Guard

O agente executa o `ruff check --fix` e o `ruff format` para adequar o código automaticamente antes de uma inspeção crítica.

## Instruções
O agente precisa rodar com permissões de `write`. Ele vai salvar as diffs como artefato sob o diretório `artifacts/rpa/swarm/auto_remediated.diff`.
