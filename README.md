# Agent Coding Framework (Public Template)

Repositorio publico com **artefatos sanitizados** para bootstrap de ambientes de agent coding.
A configuracao operacional completa (runtime, agentes internos, comandos e plugins) foi movida para repositório **privado**.

## Objetivo

Este repositorio existe para:
- documentar a interface publica do framework;
- distribuir templates seguros (`*.example`);
- manter validacoes de publicacao para evitar vazamento de artefatos internos.

## Public vs Internal Artifacts

### Publico por padrao (este repositorio)
- `README.md`, `AGENTS.md` e documentacao de alto nivel.
- `scripts/` com utilitarios publicos sem detalhes de runtime interno.
- `tests/` e workflows de CI voltados a conformidade publica.
- Templates sanitizados:
  - `.agent.example/`
  - `.codex.example/`
  - `.opencode.example/`
  - arquivos `*.example`

### Interno (repositório privado de configuração operacional)
- `.agent/` (skills/workflows operacionais completos).
- `.codex/` (configuração de swarm e agentes internos).
- `.opencode/` (agents, commands, plugins, tools, specs e contexto de runtime).
- qualquer artefato com segredo/token/chave privada.

> Local dos arquivos privados: repositório privado de configuração operacional da organização (ex.: `agent-coding-framework-internal-config`).

## Estrutura publica

```text
.
├── .agent.example/
├── .codex.example/
├── .opencode.example/
├── .github/workflows/
├── scripts/
├── tests/
├── AGENTS.md
├── README.md
└── opencode.json
```

## Politica de publicacao

Antes de publicar:
1. validar que diretórios internos (`.agent/`, `.codex/`, `.opencode/`) não estão versionados;
2. manter apenas templates sanitizados (`*.example` + READMEs de interface);
3. executar o check de boundary no CI.
