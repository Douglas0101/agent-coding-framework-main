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
- `context/` — Contexto de sessão e estado operacional

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
│   ├── test_stable_execution.py           # Suite de execução estável (38 testes)
│   ├── test_public_config_sanitization.py # Testes de configuração sanitizada
│   └── test_public_repo_allowlist.py      # Testes de allowlist
└── artifacts/
    └── codex-swarm/
        ├── run-stable-execution/   # Relatórios de conformidade
        └── run-advanced-analysis/  # Relatórios de análise de segurança
```

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

1. **Paridade de Configuração**: `opencode.json` (raiz) e `.opencode/opencode.json` devem ser equivalentes
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

Execute a suite de testes de execução estável:

```bash
python -m pytest .internal/tests/test_stable_execution.py -v
```

A suite inclui:
- **ConfigIntegrity**: Testes de paridade de configuração
- **CommandRouting**: Testes de roteamento de comandos
- **SpecStructure**: Testes de estrutura de especificações
- **Invariants**: Testes de invariantes de execução
- **HandoffContract**: Testes de contrato de handoff
- **AgentsMdConsistency**: Testes de consistência do AGENTS.md
- **NegativePatterns**: Testes de padrões negativos

---

## Integração CI/CD

### Workflows Disponíveis

| Workflow | Descrição | Gatilho |
|----------|-----------|---------|
| `routing-regression.yml` | Testes de regressão de roteamento | Push/PR em config/spec |
| `public-artifacts-guard.yml` | Verificação de boundary público | Push/PR em main/master |
| `public-repo-guard.yml` | Scanner de padrões sensíveis | Push/PR em main/master |

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
