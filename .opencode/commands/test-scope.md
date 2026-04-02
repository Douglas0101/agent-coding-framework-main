---
description: "Executa a menor validação relevante com harness discovery"
agent: tester
subtask: false
---

Execute a menor validacao relevante para o escopo: `$ARGUMENTS`.

## Harness discovery protocol

1. Verifique Makefile: `make test`, `make lint`, `make typecheck`
2. Verifique pytest: `pytest tests/test_<modulo>.py`
3. Verifique ruff: `ruff check src/`
4. Verifique mypy: `mypy src/`
5. Fallback: reporte `harness_not_found`

## Output esperado

JSON com: harness_discovered, tests_run[], passed, failed, skipped, blockers[], confidence, recommendation.

Execute apenas testes necessarios para validar as mudancas. Nao faca mudancas de codigo.
