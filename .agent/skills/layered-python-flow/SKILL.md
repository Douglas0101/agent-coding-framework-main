---
name: layered-python-flow
description: Fluxo de desenvolvimento em 5 camadas (PEP - Type - Complexity - Arch
  - Deep Logic)
---

# Layered Python Development Flow

## Objetivo
Padronizar o ciclo de desenvolvimento através de 5 camadas progressivas de validação, garantindo que o código evolua de "sintaticamente correto" para "arquiteturalmente robusto".

## As 5 Camadas (The 5 Layers)

### Layer 1: Foundation (Sintaxe & Padrões)
**Foco:** O código roda e é legível?
- **Ferramentas:** Ruff (lint/format), Black, Isort.
- **Checklist:**
    - [ ] Nenhuh erro de sintaxe.
    - [ ] Formatação compatível com PEP8 (via Black).
    - [ ] Imports ordenados.
    - [ ] Sem variáveis não usadas.

### Layer 2: Type Safety (Robustez Estática)
**Foco:** Os tipos de dados são consistentes?
- **Ferramentas:** Mypy (Strict mode).
- **Checklist:**
    - [ ] `strict = true` no pyproject.toml.
    - [ ] Sem `Any` implícito.
    - [ ] Generics usados corretamente.
    - [ ] Tratamento de `Optional` exaustivo.

### Layer 3: Code Health (Complexidade)
**Foco:** O código é manutenível?
- **Ferramentas:** Radon (CC/MI), Xenon.
- **Metrics:**
    - Cyclomatic Complexity <= 10.
    - Halstead Metrics saudáveis.
    - Maintainability Index > 65 (B).

### Layer 4: Architecture (Design Patterns)
**Foco:** O código respeita os limites arquiteturais?
- **Ferramentas:** Import-Linter, Pylint (dependências).
- **Checklist:**
    - [ ] Domain não depende de Infra/App.
    - [ ] Adapters dependem de Ports (não o inverso).
    - [ ] Sem ciclos de dependência.
    - [ ] DTOs usados nas fronteiras.

### Layer 5: Deep Logic & Compliance (Segurança & Docs)
**Foco:** O código é seguro e bem documentado?
- **Ferramentas:** Bandit (SAST), Docstrings (Google Style).
- **Checklist:**
    - [ ] Nenhuma vulnerabilidade de segurança (Bandit).
    - [ ] Docstrings em todos os módulos/classes/funções públicas.
    - [ ] Tratamento de exceções específico (sem `except Exception`).

## Comandos

### Executar Verificação Completa
```bash
python .agent/skills/layered-python-flow/scripts/verify_layers.py --all
```

### Executar por Camada
```bash
# Layer 1
python .agent/skills/layered-python-flow/scripts/verify_layers.py --layer 1

# Layer 2
python .agent/skills/layered-python-flow/scripts/verify_layers.py --layer 2
```

## Workflow Recomendado

1. **Desenvolvimento (Loop Rápido)**: Rode Layer 1 e 2 frequentemente.
2. **Review (Pre-Commit)**: Rode Layer 3 para garantir que não introduziu dívida técnica.
3. **CI/CD (Build)**: Todas as camadas (1-5) devem passar.

## Troubleshooting

### Falha na Layer 2 (Types)
- Use `cast` apenas se necessário.
- Prefira `Protocol` a herança complexa.

### Falha na Layer 4 (Architecture)
- Se `Domain` precisa de algo externo, inverta a dependência (Defina uma Interface/Port no Domain).
