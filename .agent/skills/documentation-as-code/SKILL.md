---
name: documentation-as-code
description: Documentação como código versionado, testável e automatizado
---

# Documentation as Code Skill

## Objetivo

Tratar documentação como código de primeira classe: versionada, testável, automatizada e integrada ao CI/CD.

---

## Princípios

1. **Single Source of Truth**: Documentação no repositório junto ao código
2. **Versioned**: Histórico completo via Git
3. **Testable**: Validação automática de links, exemplos, schemas
4. **Generated**: Documentação de API gerada automaticamente
5. **Reviewed**: Documentação passa por code review

---

## Componentes

### 1. Architecture Decision Records (ADRs)

Template em `.docs/adr/`:

```markdown
# ADR-{NUMBER}: {TITLE}

## Status
{Proposed | Accepted | Deprecated | Superseded by ADR-XXX}

## Context
{Descrição do problema e contexto}

## Decision
{Decisão tomada}

## Consequences
{Impactos positivos e negativos}

## Alternatives Considered
{Alternativas avaliadas}
```

**Comandos:**
```bash
# Listar ADRs
ls .docs/adr/

# Criar novo ADR
echo "# ADR-XXX: Title" > .docs/adr/XXX-title.md
```

---

### 2. API Documentation

**OpenAPI/Swagger:**
```yaml
# openapi.yaml
openapi: 3.1.0
info:
  title: Project Vitruviano API
  version: 1.0.0
paths:
  /health:
    get:
      summary: Health check endpoint
      responses:
        '200':
          description: Service healthy
```

**Validação:**
```bash
# Validar schema OpenAPI
npx @redocly/cli lint openapi.yaml

# Gerar documentação
npx @redocly/cli build-docs openapi.yaml -o docs/api.html
```

---

### 3. Docstring Coverage

**Verificação:**
```bash
# Interrogate para coverage de docstrings
pip install interrogate
interrogate src/ -v --fail-under 80

# Relatório detalhado
interrogate src/ --generate-badge docs/docstring-coverage.svg
```

**Configuração em pyproject.toml:**
```toml
[tool.interrogate]
ignore-init-method = true
ignore-init-module = true
ignore-magic = false
ignore-semiprivate = false
ignore-private = false
ignore-property-decorators = false
ignore-module = false
ignore-nested-functions = false
ignore-nested-classes = true
ignore-setters = false
fail-under = 80
exclude = ["tests", "docs"]
verbose = 2
```

---

### 4. Changelog Automation

**Conventional Commits:**
```
feat: add new training pipeline
fix: resolve memory leak in dataloader
docs: update API documentation
refactor!: BREAKING CHANGE: rename config keys
```

**Geração automática:**
```bash
# Gerar CHANGELOG com conventional-changelog
npx conventional-changelog -p angular -i CHANGELOG.md -s

# Ou com git-cliff
git cliff --output CHANGELOG.md
```

---

### 5. README Linting

**Verificação:**
```bash
# Lint de markdown
npx markdownlint-cli2 "**/*.md"

# Verificar links quebrados
npx markdown-link-check README.md
```

---

## Integração CI/CD

```yaml
# .github/workflows/docs.yml
name: Documentation

on: [push, pull_request]

jobs:
  docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Lint Markdown
        run: npx markdownlint-cli2 "**/*.md"

      - name: Check Links
        run: npx markdown-link-check README.md

      - name: Docstring Coverage
        run: |
          pip install interrogate
          interrogate src/ --fail-under 80

      - name: Validate OpenAPI
        run: npx @redocly/cli lint openapi.yaml
```

---

## Estrutura Recomendada

```
.docs/
├── adr/                    # Architecture Decision Records
│   ├── 001-use-pytorch.md
│   └── 002-hipaa-compliance.md
├── api/                    # API Documentation
│   └── openapi.yaml
├── runbooks/               # Operational Runbooks
│   ├── incident-response.md
│   └── deployment.md
└── diagrams/               # Architecture Diagrams (Mermaid/PlantUML)
    └── system-context.mmd

README.md                   # Project overview
CHANGELOG.md                # Version history
CONTRIBUTING.md             # Contribution guidelines
```

---

## Métricas

| Métrica | Target | Ferramenta |
|---------|--------|------------|
| Docstring Coverage | ≥ 80% | interrogate |
| Link Health | 100% válido | markdown-link-check |
| ADR Count | ≥ 1 per major decision | Manual |
| README Freshness | Updated per release | Git history |

---

## Workflow

1. **Ao criar feature**: Criar ADR se necessário
2. **Ao modificar API**: Atualizar OpenAPI spec
3. **Ao mergear**: Gerar CHANGELOG entry
4. **Ao lançar**: Atualizar README e version
