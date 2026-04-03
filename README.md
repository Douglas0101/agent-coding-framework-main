# Agent Coding Framework (Public Template)

Repositorio publico com artefatos sanitizados para bootstrap de ambientes de agent coding.

## Public vs Internal Artifacts

### Publico por padrao (este repositorio)
- `README.md`, `AGENTS.md` e documentacao de alto nivel.
- `.internal/scripts/` e `.internal/tests/` com validacoes voltadas ao boundary publico.
- Templates sanitizados em `.agent.example/`, `.codex.example/` e `.opencode.example/`.
- `opencode.json` com placeholders e notas de uso publico.

### Interno (repositório privado)
- `.agent/`, `.codex/` e `.opencode/` com runtime operacional completo.
- Segredos, chaves privadas, tokens e qualquer artefato sensivel.

Para detalhes expandidos, consulte `docs/README.md`.
