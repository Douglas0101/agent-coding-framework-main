# Conventions do Projeto

> Placeholder — populado pelos agents durante execucao.

## Padrões de Código

- Python 3.13+ com type hints
- PEP 8/20/257/484
- Ruff para linting e formatação
- MyPy para verificação de tipos

## Padrões de Teste

- pytest com markers: unit, integration, security, performance, slow
- Harness via Makefile: `make test`, `make lint`, `make typecheck`

## Padrões de Commit

- Conventional Commits
- Pre-commit hooks ativos

## Padrões de Agentes

- Output JSON estruturado obrigatório
- Confidence score 0.0-1.0 por claim
- Source reference rastreavel
- Severity classification: critical, major, minor, suggestion
