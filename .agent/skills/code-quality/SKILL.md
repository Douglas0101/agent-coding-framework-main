---
name: code-quality
description: Automacao de qualidade de codigo com Ruff e gates avancados de algoritmo, seguranca e engenharia
---

# Code Quality Skill

## Objetivo

Automatizar qualidade de codigo durante desenvolvimento e geracao de algoritmos,
combinando lint/format com guardrails de seguranca para reduzir risco tecnico
antes de CI/release.

## Ferramentas Utilizadas

| Ferramenta | Proposito |
|------------|-----------|
| **Ruff** | Linting e formatacao rapida (`check` + `format`) |
| **AST Gates** | Regras avancadas para complexidade algoritmica e seguranca |
| **Engineering Gate** | Contratos de dependencia, metadados de packaging e paridade de CI |
| **MyPy** | Reforco de contratos de tipo em fluxos criticos |

## Comandos

### Verificacao padrao (sem modificar arquivos)

```bash
ruff check .
ruff format --check .
```

### Verificacao avancada para geracao de algoritmos

```bash
python .agent/skills/code-quality/scripts/lint_fix.py \
  --check \
  --paths src \
  --ignore D,E501,W291,W293 \
  --algorithm-gate \
  --security-gate \
  --engineering-gate \
  --max-loop-depth 3 \
  --report
```

### Correcao automatica de lint/format

```bash
python .agent/skills/code-quality/scripts/lint_fix.py --fix --paths src
```

## Regras Avancadas do Gate

### Algoritmos

- `ALG001`: profundidade de loops acima do limite configurado.
- `ALG002`: `while True` sem limite/saida explicita.
- `ALG900`: arquivo sem AST valido para analise automatica.

### Seguranca

- `SEC001`: uso de `eval`/`exec`.
- `SEC002`: uso de `os.system`.
- `SEC003`: `subprocess` com `shell=True`.
- `SEC004`: desserializacao insegura (`pickle`, `marshal`, etc.).
- `SEC005`: `yaml.load` sem `SafeLoader`.
- `SEC006`: hash inseguro (`md5`/`sha1`).
- `SEC007`: `random.*` em contexto sensivel (auth/secret/token/crypto).

### Engenharia e Performance (Baseline)

- `ENG001`: secao `[project]` ausente no `pyproject.toml`.
- `ENG002`: `project.version` ausente (quebra install/editable no CI).
- `ENG003`: `project.requires-python` ausente.
- `ENG004`: `setup.py` sem `python_requires`.
- `ENG005`: divergencia entre `pyproject.requires-python` e `setup.py`.
- `ENG006`: modulo de seguranca usa `cryptography`, mas dependencia nao declarada.
- `ENG007`: `tests/test_security.py` importa `torch`, mas workflow nao instala `torch`.
- `ENG008`: workflow testa Python abaixo do baseline definido no projeto.
- Cumprimento mandatory do DoD (Definition of Done) para testes, coverage e memory profiling em PRs complexos.

## Integracao com RPA

O RPA executa este gate automaticamente na fase `CodeQuality`:

```bash
python scripts/rpa_engineer.py --strict-enterprise
```

Para desabilitar apenas esta fase:

```bash
python scripts/rpa_engineer.py --skip-code-quality
```

## Referencias de Seguranca (consultadas via MCP)

- OWASP ASVS 5.0.0 para verificacao de controles de seguranca.
- NIST SP 800-218 (SSDF 1.1) para praticas de desenvolvimento seguro.
- NIST SP 800-218A para requisitos de IA generativa e modelos fundacionais.
- CWE Top 25 (2024) para priorizacao de fraquezas recorrentes.

## Workflow Recomendado

1. Rodar gate local com `--algorithm-gate --security-gate --engineering-gate`.
2. Corrigir findings criticos antes de abrir PR.
3. Em CI, usar RPA em modo estrito (`--strict-enterprise`).
4. Publicar `artifacts/quality_report.txt` para auditoria.
