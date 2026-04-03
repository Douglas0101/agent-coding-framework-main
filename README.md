# Agent Coding Framework

Framework de agent coding para orquestração multi-agente com OpenCode e Codex. Este repositório implements um sistema robusto de execução estável com verificação de conformidade, contratos de handoff entre agentes e guardrails de segurança.

## Visão Geral

O **Agent Coding Framework** é uma infraestrutura de desenvolvimento orientada por agentes que combina:

- **OpenCode**: Runtime de execução de agentes com suporte a commands, plugins e tools
- **Codex**: Orquestrador de swarm multi-agente para tarefas complexas
- **Skills**: Agentes especializados para diferentes fases do ciclo de desenvolvimento
- **Stable Execution**: Sistema de garantias de execução com verificação de conformidade

### Propósito

Este framework foi projetado para automatizar e otimizar o ciclo de desenvolvimento de software através de:

1. **Automação de tarefas repetitivas**: Geração de código, refatoração, documentação
2. **Análise de código**: Detecção de vulnerabilidades, code smells, padrões problemáticos
3. **Pesquisa e investigação**: Exploração de bases de código, documentação externa, resolução de conflitos
4. **Validação e verificação**: Testes automatizados, reviews técnicos, verificação de conformidade

---

## Arquitetura do Sistema

### Componentes Principais

```
agent-coding-framework/
├── .opencode/          # Configuração do OpenCode (agents, commands, tools, plugins)
├── .codex/             # Configuração do Codex (swarm, multi-agent orchestration)
├── .agent/             # Skills e workflows dos agentes
├── .internal/          # Scripts, testes e artefatos operacionais
├── .github/            # workflows de CI/CD
├── docs/               # Documentação técnica
└── templates/          # Templates sanitizados para distribuição
```

### Fluxo de Execução

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌─────────────┐
│   Input    │────▶│   Explorer   │────▶│   Evidence   │────▶│  Reviewer   │
│  (Command) │     │   (Explore)   │     │  (Collect)   │     │  (Analyze)  │
└─────────────┘     └──────────────┘     └──────────────┘     └─────────────┘
                                                                          │
                         ┌──────────────────────────────────────────────┘
                         ▼
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌─────────────┐
│   Output    │◀────│  Synthesizer │◀────│   Verifier   │◀────│   Gap       │
│  (Artifact)│     │   (Write)    │     │   (Gate)     │     │  (Identify) │
└─────────────┘     └──────────────┘     └──────────────┘     └─────────────┘
```

---

## Estrutura de Diretórios

### `.opencode/` — Configuração do OpenCode

Diretório contendo a configuração completa do ambiente OpenCode:

- `opencode.json` — Arquivo de configuração principal
- `agents/` — Definições dos agentes (autocoder, explore, reviewer, etc.)
- `commands/` — Comandos disponíveis (/analyze, /review, /autocode, etc.)
- `plugins/` — Plugins TypeScript para extensibilidade
- `tools/` — Ferramentas adicionais disponíveis aos agentes
- `specs/` — Specifications de comportamento e contratos
  - `handoff-contract.sanitized.json` — Contrato de handoff entre agentes
  - `README.md` — Documentação das specs
- `manifests/` — Manifestos de execução
  - `sanitized/run-manifest.example.json` — Exemplo de manifesto sanitizado
  - `README.md` — Documentação dos manifests
- `context/` — Contexto de sessão e estado operacional

#### Public vs Internal Artifacts

Para governança de repositório público, a pasta `.opencode/` é tratada como **deny-by-default**, com exceções explícitas apenas para contratos sanitizados.

| Subpasta / Arquivo | Classificação | Política |
|--------------------|---------------|----------|
| `.opencode/opencode.json` | **Público** | Contrato de configuração sanitizada versionável |
| `.opencode/specs/*.sanitized.json` | **Público** | Specs de contrato sem estado de runtime |
| `.opencode/manifests/sanitized/*.json` | **Público** | Exemplos de manifests sanitizados |
| `.opencode/node_modules/` | **Interno** | Dependências efêmeras (não versionar) |
| `.opencode/memory/` | **Interno** | Memória/estado transitório de agentes |
| `.opencode/context/` | **Interno** | Contexto de sessão e dados operacionais |
| `.opencode/evidence/`, `.opencode/artifacts/`, `.opencode/tmp/` | **Interno** | Evidências e artefatos transitórios |

> Regra prática: qualquer dado live/sensível fica fora do Git; somente contratos e exemplos sanitizados entram no repositório público.

### `.codex/` — Orquestração Multi-Agente

Configuração do Codex para swarms multi-agente:

- `config.toml` — Configuração principal do swarm
- `agents/` — Definições de agentes Codex (synthesizer, verifier, etc.)
- `workflows/` — Fluxos de trabalho para diferentes cenários

### `.agent/` — Skills e Workflows

Conjunto completo de skills especializadas:

- `skills/` — 57+ skills covering different domains
- `workflows/` — Workflows pré-definidos para tarefas comuns

### `.internal/` — Scripts e Testes Operacionais

Scripts, testes e artefatos de validação:

```
.internal/
├── scripts/
│   ├── security_patterns.py        # Padrões de segurança compartilhados
│   ├── scan_sensitive_patterns.py # Scanner de padrões sensíveis
│   ├── check-public-boundary.sh   # Verificação de boundary público
│   └── run-autocode.sh            # Wrapper para /autocode
├── tests/
│   ├── test_stable_execution.py           # Regressão de routing + guardrails (8 testes)
│   ├── test_public_boundary.py            # Boundary público vs interno (4 testes)
│   ├── test_public_config_sanitization.py # Contrato de config/doc sanitizados (5 testes)
│   └── test_public_repo_allowlist.py      # Governança de allowlist pública (3 testes)
└── artifacts/
    └── codex-swarm/
        ├── run-stable-execution/   # Relatórios de conformidade
        └── run-advanced-analysis/  # Relatórios de análise de segurança
```

---


## Public vs Internal Artifacts

Este repositório público mantém apenas artefatos sanitizados. Diretórios operacionais (`.agent/`, `.codex/`, `.opencode/`) permanecem fora do versionamento público e devem ser materializados localmente em ambiente interno.

Para garantir execução estável sem expor dados sensíveis:

- `opencode.json` (raiz) define a interface pública sanitizada e os campos críticos de routing.
- `.opencode/opencode.json` é a configuração operacional local e deve manter paridade nos campos críticos.
- Campos não críticos podem divergir conforme a política documentada na seção **Execução Estável (Stable Execution)**.

---

## Uso como Template

### Instalação

Para usar este framework como template em um novo projeto:

```bash
# 1. Clone o repositório template
git clone https://github.com/organization/agent-coding-framework.git /tmp/agent-framework

# 2. Copie a estrutura para seu projeto
cp -r /tmp/agent-framework/.opencode seu-projeto/
cp -r /tmp/agent-framework/.codex seu-projeto/
cp -r /tmp/agent-framework/.agent seu-projeto/
cp /tmp/agent-framework/AGENTS.md seu-projeto/

# 3. Instale as dependências
cd seu-projeto/.opencode
bun install

# 4. Customize para seu projeto
# - Edite conventions.md para refletir convenções do seu projeto
# - Atualize AGENTS.md com agentes específicos do seu contexto
# - Configure credenciais em .env (não versionar!)
```

### Configuração de Ambiente

Crie um arquivo `.env` no diretório `.opencode/` com suas credenciais:

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic (opcional)
ANTHROPIC_API_KEY=sk-ant-...

# Outras variáveis de ambiente necessárias
```

> ⚠️ **Importante**: O arquivo `.env` deve ser adicionado ao `.gitignore` e nunca deve ser versionado.

---

## Comandos Disponíveis

O framework oferece comandos especializados para diferentes tarefas:

| Comando | Agente | Descrição |
|---------|--------|-----------|
| `/analyze` | explore | Análise rápida de código |
| `/autocode` | autocoder | Geração e refatoração de código |
| `/review` | reviewer | Revisão técnica com classificação de severidade |
| `/check` | validation | Verificação de conclusões |
| `/test` | tester | Execução de testes e validação |
| `/search` | docs_researcher | Pesquisa de documentação externa |

### Executando Comandos

```bash
# Usando OpenCode diretamente
opencode run --agent autocoder --command autocode "gere uma função para..."

# Usando o wrapper (recomendado para /autocode)
.internal/scripts/run-autocode.sh "sua tarefa aqui"
```

---

## Skills Disponíveis

O framework oferece 57+ skills especializadas organizadas por domínio:

### Skills de Análise e Pesquisa

| Skill | Descrição |
|-------|-----------|
| `explore` | Exploração rápida de codebases, busca de arquivos e padrões |
| `hypothesis` | Geração de hipóteses testáveis a partir de requisitos |
| `evidence` | Coleta de evidências com source grading |
| `citation` | Verificação de credibilidade de fontes |
| `contradiction` | Detecção e resolução de contradições |
| `gap` | Identificação de lacunas de cobertura |

### Skills de Desenvolvimento

| Skill | Descrição |
|-------|-----------|
| `autocoder` | Coding agent com raciocínio sequencial |
| `code-quality` | Análise de qualidade de código com Ruff |
| `complexity-reduction` | Redução de complexidade ciclomática |
| `refactor-patterns` | Governança de design patterns |
| `dead-code-removal` | Detecção e eliminação de código morto |

### Skills de Segurança

| Skill | Descrição |
|-------|-----------|
| `security-audit` | Auditoria SAST com Bandit |
| `vulnerability-scanner` | Scanner enterprise de CVEs e secrets |
| `threat-modeling` | STRIDE threat modeling |
| `hardening` | Hardening de segurança OWASP/CIS |
| `compliance-checker` | Verificação de compliance HIPAA/SOC2 |

### Skills de Infraestrutura e DevOps

| Skill | Descrição |
|-------|-----------|
| `ci-cd-optimization` | Otimização de pipelines CI/CD |
| `docker-patterns` | Melhores práticas Docker |
| `observability` | Instrumentação OpenTelemetry |
| `backend-reliability` | Verificação de contratos de API |

### Skills de ML/AI

| Skill | Descrição |
|-------|-----------|
| `ai-research-advisor` | Diagnóstico de problemas de treinamento |
| `advanced-ml-optimization` | Otimização de LLMs e PEFT |
| `data-augmentation` | Técnicas de augmentation para imagens médicas |
| `deep-performance-tuning` | Otimização de performance multi-camada |
| `experiment-tracking` | Gestão de experimentos ML |
| `model-lineage` | Rastreamento de proveniência de modelos |

### Skills Especializadas por Domínio

| Skill | Descrição |
|-------|-----------|
| `agentic-rag` | RAG para diretrizes médicas |
| `agentic-reporting` | Geração de laudos médicos estruturados |
| `specialist-ensemble` | Ensemble de especialistas |
| `specialist-group-a` | Especialista em opacidades pulmonares |
| `specialist-group-b` | Especialista em anomalias estruturais |
| `specialist-group-c` | Especialista em lesões focais |
| `specialist-group-d` | Especialista em interação coração-pulmão |

---

## Execução Estável (Stable Execution)

O framework implementa um sistema robusto de garantias de execução:

### Garantias Implementadas

1. **Fail-fast de Configuração**: o wrapper `.internal/scripts/run-autocode.sh` falha imediatamente quando `.opencode/opencode.json` está ausente (evita fallback silencioso)

1. **Paridade de Configuração**: `opencode.json` (raiz) e `.opencode/opencode.json` devem ser equivalentes
   - Campos críticos de routing (obrigatoriamente idênticos): `default_agent`, `maxSteps`, `routing.commands.autocode`, `routing.agents.autocoder.maxSteps`
   - Campos permitidos a divergir: metadados e contexto não-crítico de runtime (ex.: `note`, `template_refs`, `providers`, segredos/overrides locais). Divergências nesses campos não podem alterar roteamento ou limites de steps.
2. **Invariantes de Execução**:
   - Sem retry ilimitado (`max_attempts ≤ 3`)
   - Sem fallback silencioso de agente
   - Gate obrigatório do verifier antes do synthesizer
   - Isolamento de write_scope entre workers paralelos
   - Prevenção de doom loops
   - Idempotência garantida

3. **Máquina de Estados**: 13 estados, 20 transições válidas, 7 proibidas
4. **Contrato de Handoff**: 12 campos obrigatórios, 6 regras de validação

### Testes de Conformidade

Execute a suite dedicada de stable execution:

```bash
python -m pytest .internal/tests/test_stable_execution.py -v
```

Classes e foco atuais:
- **TestCommandRoutingRegression** (4): casos mínimos para `/autocode` sem `--agent`, com `--agent autocoder` e ausência de fallback silencioso.
- **TestStableExecutionGuardrails** (4): asserts de verifier gate, write_scope disjoint e fail-fast em drift de config.

---

## Public vs Internal Artifacts

Este repositório público publica apenas interfaces e templates sanitizados.
Toda configuração/runtime operacional real permanece em **private repository only**.

- Superfície pública: `opencode.json`, `.opencode.example/`, `.codex.example/`, `.agent.example/`.
- Superfície interna: `.opencode/`, `.codex/`, `.agent/` (não versionadas neste repositório público).

---

## Integração CI/CD

### Workflows Disponíveis

| Workflow | Descrição | Gatilho |
|----------|-----------|---------|
| `routing-regression.yml` | Regressão de routing + paridade de config + evidências auditáveis | Push/PR em config/spec |
| `public-artifacts-guard.yml` | Verificação de boundary público | Push/PR em main/master |
| `public-repo-guard.yml` | Scanner de padrões sensíveis | Push/PR em main/master |

> **Merge gate obrigatório**: configure o status check `Routing Regression (Required)` como *required* na proteção de branch para bloquear merge em caso de regressão de routing.

### Execução Local

Para validar antes de push:

```bash
# Testes de execução estável
python -m pytest .internal/tests/ -v

# Verificação de boundary
.internal/scripts/check-public-boundary.sh

# Scanner de padrões sensíveis
python .internal/scripts/scan_sensitive_patterns.py

# Pre-commit hooks
pre-commit run --all-files
```

---

## Segurança e Compliance

### Política de Configuração Sanitizada

Este repositório segue uma política rigorosa de configuração sanitizada:

| Categoria | Permitido (público) | Proibido (público) |
|-----------|---------------------|--------------------|
| API keys | Placeholders (`${API_KEY}`) | Tokens reais |
| Endpoints | URLs públicas | Hosts internos/IPs RFC1918 |
| Chaves criptográficas | Texto explicativo/placeholders | Blocos PEM privados |
| Config runtime | Interface e exemplos mínimos | IDs internos/estados de sessão |

### Pre-commit hooks

Configure hooks locais para validação:

```bash
# Instale dependências
python -m pip install pre-commit detect-secrets

# Configure hooks
pre-commit install

# Execute validação
pre-commit run --all-files
```

---

## Problema Conhecido: Routing Bug no `/autocode`

### Descrição

No OpenCode v1.3.13, o comando `/autocode` não é roteado corretamente para o agente `autocoder`. Em vez disso, faz fallback para o agente `general` com `maxSteps: 50`.

### Solução de contorno (Workaround)

Use o wrapper script fornecido:

```bash
# Execute via wrapper (recomendado)
.internal/scripts/run-autocode.sh "sua tarefa aqui"

# Ou use o flag --agent diretamente
opencode run --agent autocoder --command autocode "sua tarefa aqui"
```

### Tracking

O bug está sendo rastreado em `.internal/artifacts/codex-swarm/run-stable-execution/debug_autocode.log` (artefato sanitizado e versionável).

---

## Requisitos do Sistema

- **Runtime**: Bun (para plugins/tools TypeScript)
- **CLI**: OpenCode
- **Node.js**: 20+ (para tree-sitter parsers)
- **Python**: 3.10+ (para testes)
- **Ferramentas**: Git, pre-commit

---

## Configuração de IDE

O projeto segue o padrão `.editorconfig` para consistência entre editores:

### JetBrains (IntelliJ/PyCharm)

1. Importe o projeto normalmente
2. Aplique preferências locais (tema, plugins, layout)
3. **Não** adicione arquivos de `.idea/` ao commit
4. Valide com `git status --short` antes de abrir PR

### VS Code / Neovim

O projeto inclui configuração `.editorconfig` que será aplicada automaticamente.

---

## Contribuindo

### Fluxo de Trabalho

1. **Fork** o repositório
2. **Crie** uma branch para sua feature (`feature/nova-feature`)
3. **Faça** suas alterações seguindo as convenções
4. **Execute** testes localmente
5. **Abra** um PR com descrição detalhada

### Convenções de Commit

Siga o padrão Conventional Commits:

```
<tipo>(<escopo>): <descrição>

[corpo opcional]

[footer opcional]
```

Exemplos:
- `feat(autocoder): adicionar suporte a novo padrão de código`
- `fix(routing): corrigir fallback silencioso do /autocode`
- `docs(readme): atualizar seção de configuração`

---

## Licença

**Proprietary — All Rights Reserved**

Este projeto contém configurações operacionais sensíveis. Para uso em produção, entre em contato com a organização.

---

## Referências

- [OpenCode Documentation](https://opencode.ai/docs)
- [Codex Documentation](https://codex.io)
- [AGENTS.md](./AGENTS.md) — Regras nativas do swarm
- [.internal/MANIFEST.md](./.internal/MANIFEST.md) — Manifesto de interconectividade
- [docs/README.md](./docs/README.md) — Documentação adicional
