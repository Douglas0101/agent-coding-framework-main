# Agent Orchestration Framework

**Status:** Core is Domain-Agnostic  
**Architecture:** Spec-Driven Architecture (SDA)  
**Reference:** [CONSTITUTION_emendada.md](docs/CONSTITUTION_emendada.md)

---

## Visão Geral

O **Agent Orchestration Framework** é uma infraestrutura de orquestração multi-agente de propósito geral. O **Core** é domain-agnostic — não contém lógica de negócio específica de ML, Medical, Finance ou outros domínios verticais.

O framework combina:
- **Core de Orquestração**: Gramática de execução, verificação, síntese e handoff
- **Domain Packs**: Extensões contratuais que fornecem capacidades específicas de domínio
- **Extension Registry**: Catálogo de packs disponíveis para ativação

### Propósito

Este framework foi projetado para automatizar orquestração de agentes em qualquer domínio computacional:

1. **Execução Estável**: Verificação de conformidade, fail-fast de configuração
2. **Contratos Formais**: Handoff entre agentes com validação estrutural
3. **Extensibilidade**: Novas capacidades via Domain Packs registrados
4. **Neutralidade**: Core independente de domínio vertical

---

## Arquitetura do Sistema

### Modelo: Core Domain-Agnostic + Domain Packs

```
agent-orchestration-framework/
├── docs/                  # ÚNICA superfície pública documental
│   ├── CONSTITUTION_emendada.md
│   ├── PRD_desverticalizacao_framework.md
│   ├── ADOPTION_RUNBOOK.md
│   └── README.md
├── .internal/             # TODA a estrutura operacional
│   ├── specs/core/           # Core domain-agnostic (nível 0)
│   ├── domains/              # Domain Packs (extensões contratuais)
│   ├── registry/             # Extension Registry
│   ├── templates/            # Templates para novos packs
│   ├── scripts/              # Scripts operacionais
│   ├── tests/                # Suite de testes
│   └── artifacts/            # Artefatos de execução
├── .opencode/              # Configuração OpenCode (interno)
├── .codex/                 # Orquestração multi-agente (interno)
├── .agent/                 # Skills operacionais (interno)
├── README.md               # Interface pública
├── AGENTS.md               # Regras de swarm
└── opencode.json           # Config pública sanitizada
```

### Camadas Arquiteturais

1. **Core (Nível 0)**: Gramática de orquestração — interfaces, protocolos, invariantes
2. **Domain Packs**: Semântica de domínio implementada como extensões contratuais
3. **Runtime**: Execução concreta via OpenCode/Codex

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

> **Regra**: apenas `docs/` é superfície pública. Toda estrutura operacional (`specs/`, `domains/`, `registry/`, `templates/`, scripts, testes) reside em `.internal/`.

### `.internal/` — Núcleo Operacional

Todo aprimoramento do framework acontece aqui:

| Subdiretório | Conteúdo |
|--------------|----------|
| `.internal/specs/core/` | Contratos de orquestração domain-agnostic |
| `.internal/domains/` | Domain Packs (software-engineering, ml-ai, medical-imaging) |
| `.internal/registry/` | Extension Registry (catálogo de packs) |
| `.internal/templates/` | Templates para criação de novos packs |
| `.internal/scripts/` | Scripts operacionais e wrappers |
| `.internal/tests/` | Suite de testes de regressão |
| `.internal/artifacts/` | Artefatos de execução e evidências |

### `docs/` — Superfície Pública Documental

Único diretório exposto publicamente:

| Arquivo | Conteúdo |
|---------|----------|
| `CONSTITUTION_emendada.md` | Fonte da verdade arquitetural |
| `PRD_desverticalizacao_framework.md` | Plano de desverticalização |
| `ADOPTION_RUNBOOK.md` | Guia de adoção para mantenedores |
| `README.md` | Índice de documentação |

---

## Public vs Internal Artifacts

**Regra fundamental**: apenas `docs/` é superfície pública. Todo aprimoramento, spec, contract, registry, template, script e teste reside em `.internal/`.

| Camada | Localização | Acesso |
|--------|-------------|--------|
| Documentação pública | `docs/` | Público |
| Especificações do Core | `.internal/specs/` | Interno |
| Domain Packs | `.internal/domains/` | Interno |
| Extension Registry | `.internal/registry/` | Interno |
| Templates | `.internal/templates/` | Interno |
| Scripts e testes | `.internal/scripts/`, `.internal/tests/` | Interno |
| Config OpenCode pública | `opencode.json` (raiz) | Público (sanitizado) |
| Config OpenCode operacional | `.opencode/` | Interno |
| Runtime e skills | `.agent/`, `.codex/` | Interno |

---

## Domain Packs Disponíveis

### Software Engineering Pack (Default)

O pack funcional padrão fornece capacidades de desenvolvimento:

| Agente | Descrição |
|--------|-----------|
| `analyze` | Exploração de codebase, identificação de padrões |
| `reviewer` | Análise de código, segurança e qualidade |
| `autocoder` | Geração e refatoração de código |

### ML/AI Pack (Experimental, Opcional)

Disponível em `.internal/domains/ml-ai/`. Fornece:

| Agente | Descrição |
|--------|-----------|
| `ml-researcher` | Pesquisa de técnicas e papers |
| `ml-engineer` | Desenvolvimento de modelos |
| `ml-optimizer` | Otimização de hiperparâmetros |

### Medical Imaging Pack (Experimental, Opcional)

Disponível em `.internal/domains/medical-imaging/`. Requer ML/AI Pack. Fornece:

| Agente | Descrição |
|--------|-----------|
| `radiologist-assistant` | Análise de imagens médicas |
| `specialist-group-a` | Opacidades pulmonares difusas |
| `specialist-group-b` | Anomalias estruturais grosseiras |
| `specialist-group-c` | Lesões focais e fibrose |
| `specialist-group-d` | Interação coração-pulmão |
| `medical-reporter` | Geração de laudos estruturados |

> **Nota**: ML/AI e Medical Imaging são Domain Packs opcionais, não parte do Core. O Core permanece domain-agnostic.

---

## Execução Estável (Stable Execution)

O framework implementa um sistema robusto de garantias de execução:

### Garantias Implementadas

1. **Fail-fast de Configuração**: o wrapper `.internal/scripts/run-autocode.sh` falha imediatamente quando `.opencode/opencode.json` está ausente ou diverge nos campos críticos de routing

1. **Paridade de Configuração**: `opencode.json` (raiz) e `.opencode/opencode.json` devem ser equivalentes
   - Campos críticos de routing (obrigatoriamente idênticos): `default_agent`, `command.autocode.agent`, `agent.autocoder.maxSteps`, `agent.general.maxSteps`
   - Campos permitidos a divergir: campos suportados não críticos de runtime ou templates sanitizados (ex.: `providers`, `instructions`). Divergências nesses campos não podem alterar roteamento ou limites de steps.
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
- **TestCommandRoutingRegression** (4): casos mínimos para `/autocode` com roteamento nativo e documentação da causa raiz corrigida.
- **TestStableExecutionGuardrails** (4): asserts de verifier gate, write_scope disjoint e fail-fast em drift de config.

---

## Public vs Internal Artifacts

Este repositório público publica apenas interfaces e templates sanitizados.
Toda configuração/runtime operacional real permanece em **private repository only**.

- Superfície pública: `opencode.json`, `.opencode/opencode.json`, `.opencode/specs/README.md`, `.opencode/specs/*.sanitized.json`, `.opencode/manifests/README.md`, `.opencode/manifests/sanitized/*.json`, `.opencode.example/`, `.codex.example/`, `.agent.example/`.
- Superfície interna: `.opencode/` operacional (commands/plugins/runtime state), `.codex/`, `.agent/` e qualquer artefato com estado de sessão ou segredo (não versionados neste repositório público).

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

## Root Cause Corrigida: Routing do `/autocode`

### Descrição

O problema observado neste repositório vinha de configs com schema inválido ou obsoleto para o OpenCode v1.3.13. As chaves top-level antigas como `maxSteps` e `routing` não eram suportadas no formato usado aqui, o que invalidava a configuração efetiva.

### Solução

Use o schema suportado com top-level `agent` e `command`. Com isso, o runtime resolve `/autocode` nativamente para `autocoder` sem `--agent`:

```bash
# Execute via wrapper (recomendado)
.internal/scripts/run-autocode.sh "sua tarefa aqui"

# Ou use o comando nativo diretamente
opencode run --command autocode "sua tarefa aqui"
```

### Tracking

A investigação histórica está registrada em `.internal/artifacts/codex-swarm/run-stable-execution/debug_autocode.log`, mas a interpretação atual correta para este snapshot e este repositório é: schema inválido/stale no repositório, não bug upstream como hipótese principal.

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
