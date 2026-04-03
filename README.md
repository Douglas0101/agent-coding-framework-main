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

Este repositório segue o contrato de **configuração sanitizada** para todos os templates e arquivos públicos.
Qualquer valor operacional real é **private repository only**.

### Matriz de configuração sanitizada (permitido vs proibido)

| Categoria | Permitido (público) | Proibido (público) |
|-----------|----------------------|--------------------|
| API keys | `${OPENAI_API_KEY_PLACEHOLDER}` / `${ANTHROPIC_API_KEY_PLACEHOLDER}` | Tokens reais (`sk-...`, `ghp_...`, `xox...`) |
| Endpoints | `https://api.example.com/v1` | Hosts internos (`localhost`, `*.internal`, IPs RFC1918) |
| Chaves criptográficas | Texto explicativo e placeholders | Blocos `BEGIN ... PRIVATE KEY` |
| Config runtime | Notas de interface e exemplos mínimos | IDs internos, manifests operacionais, estado de sessão |

### Exemplos de credenciais

**Seguro (template público):**
- `OPENAI_API_KEY=${OPENAI_API_KEY_PLACEHOLDER}`
- `ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY_PLACEHOLDER}`

**Proibido (somente no repositório privado):**
- `OPENAI_API_KEY=sk-live-...`
- `AWS_SECRET_ACCESS_KEY=...`
- Qualquer chave privada PEM/OpenSSH completa.

## Skills Disponiveis (57)

### Engenharia de Codigo
- `code-quality`, `code-quality-pep`, `refactor-patterns`, `complexity-reduction`
- `dead-code-removal`, `type-safety`, `data-structures-rigor`
- `advanced-layered-engineering`, `layered-python-flow`

### Seguranca
- `security-audit`, `hardening`, `threat-modeling`, `compliance-checker`
- `vulnerability-scanner`, `security-resolver`, `dependency-audit`

### Performance
- `performance-profiling`, `deep-performance-tuning`, `gpu-profiler`
- `advanced-ml-optimization`

### ML/Data
- `data-augmentation`, `experiment-tracking`, `model-lineage`, `model-zoo`
- `ml-guardian`, `training-circuit-quality`, `inference-pipeline`
- `agentic-rag`, `agentic-reporting`, `specialist-ensemble`
- `specialist-group-a/b/c/d` (medical imaging specialists)

### DevOps/Observabilidade
- `ci-cd-optimization`, `devops-patterns`, `observability`
- `slo-sli-tracking`, `backend-reliability`, `dba-governance`
- `data-contracts`, `etl-ml-readiness`, `itch-pipeline`

### Arquitetura/Design
- `hexagonal-arch`, `enterprise-cv-refactoring`, `mas-orchestration`
- `documentation-as-code`, `semantic-versioning`

### Estrategia
- `vp-ai-strategy`, `ai-engineering-practices`, `ai-research-advisor`
- `scientific-logbook`, `ui-ux-engineering`

### Utilities
- `auto-fixer`, `test-coverage`, `rpa-engineer`

## Workflows Disponiveis (11)

| Workflow | Descricao |
|----------|-----------|
| `full-quality-check` | Verificacao completa de qualidade |
| `security-hardening` | Hardening de seguranca |
| `rpa-quality` | Pipeline RPA de qualidade |
| `code-quality` | Verificacao de qualidade de codigo |
| `performance-optimization` | Otimizacao de performance |
| `refactor-session` | Sessao de refatoracao |
| `etl-ml-readiness` | Readiness para ML pipeline |
| `validate-data` | Validacao de dados |
| `run-pipeline` | Execucao de pipeline |
| `run-tests` | Execucao de testes |
| `linux_remote_setup` | Setup remoto Linux |

## OpenCode Agents

### Primary Agent
- **orchestrator**: Orquestra analise, implementacao, revisao e validacao com confidence gates

### Subagents
| Agent | Funcao |
|-------|--------|
| `hypothesis` | Geracao de hipoteses testaveis |
| `evidence` | Coleta de evidencias com source grading |
| `citation` | Verificacao de credibilidade de fontes |
| `contradiction` | Deteccao e resolucao de contradicoes |
| `gap` | Identificacao de lacunas de cobertura |
| `synthesis` | Consolidacao de achados multiplos |
| `validation` | Verificacao independente |
| `reviewer` | Revisao tecnica com severity classification |
| `tester` | Execucao de harness de testes |
| `autocoder` | Coding agent com raciocinio sequencial |

## Codex Agents

| Agent | Funcao |
|-------|--------|
| `synthesizer` | Escrita final do pacote |
| `verifier` | Gatekeeper de completude |
| `docs-researcher` | Pesquisa de documentacao externa |
| `runbook-writer` | Documentacao artifact-first |
| `runtime-validator` | Validacao de baseline runtime |
| `viewer-consolidator` | Exploracao de contratos API/UI |

## Uso

### Como Template

1. Clone este repositorio no seu projeto:
   ```bash
   git clone <repo-url> /tmp/agent-framework
   cp -r /tmp/agent-framework/.opencode seu-projeto/
   cp -r /tmp/agent-framework/.codex seu-projeto/
   cp -r /tmp/agent-framework/.agent seu-projeto/
   cp /tmp/agent-framework/AGENTS.md seu-projeto/
   ```

2. Instale dependencias no `.opencode/`:
   ```bash
   cd seu-projeto/.opencode
   bun install
   ```

3. Customize `conventions.md` e `AGENTS.md` para seu projeto.

### Com OpenCode

O OpenCode detectara automaticamente os agents e commands ao iniciar no diretorio do projeto.

### Com Codex

O Codex usara `.codex/config.toml` para configurar o swarm multi-agent.

## Requisitos

- **Bun** runtime (para plugins/tools TypeScript)
- **OpenCode** CLI
- **Node.js** 20+ (para tree-sitter parsers)


## Padrao de IDE e Configuracoes Locais

Para manter o repositorio limpo e reproduzivel entre ferramentas:

- **Metadados pessoais de IDE nao sao versionados** (por exemplo, toda a pasta `.idea/` e ignorada no Git).
- **Configuracoes compartilhadas do time** devem ser registradas em arquivos neutros e portaveis, como `.editorconfig`.
- **Padrao suportado**: qualquer IDE/editor que respeite `.editorconfig` (IntelliJ IDEA, PyCharm, VS Code, Neovim, etc.).

### JetBrains (IntelliJ/PyCharm) sem commitar `.idea/`

1. Importe o projeto normalmente pela IDE.
2. Aplique as preferencias locais (tema, plugins, layout, run configs locais) apenas no seu ambiente.
3. Nao adicione arquivos de `.idea/` ao commit.
4. Antes de abrir PR, valide com:
   ```bash
   git status --short
   ```
   Se aparecer qualquer arquivo dentro de `.idea/`, mantenha fora do indice Git.

### Onde colocar convencoes de equipe

Quando precisar padronizar comportamento entre IDEs/editores, priorize:

1. `.editorconfig` para formatacao basica (indentacao, newline, trailing spaces).
2. Documentacao no `README.md` para processos operacionais.
3. Ferramentas de lint/formatter do projeto (quando aplicavel) para enforcement automatizado.

## Licenca

Proprietary -- All Rights Reserved.

---

Antes de publicar:
1. validar que diretórios internos (`.agent/`, `.codex/`, `.opencode/`) não estão versionados;
2. manter apenas templates sanitizados (`*.example` + READMEs de interface);
3. executar o check de boundary no CI.
