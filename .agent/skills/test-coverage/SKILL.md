---
name: test-coverage
description: Análise e melhoria de cobertura de testes com pytest-cov
---

# Test Coverage Skill

## Objetivo

Analisar cobertura de testes, identificar gaps críticos, e fornecer recomendações para alcançar o threshold de 85%.

## Ferramentas Utilizadas

| Ferramenta | Propósito |
|------------|-----------|
| **pytest-cov** | Cobertura durante testes |
| **coverage.py** | Análise detalhada de cobertura |

## Threshold Atual

Configurado em `pyproject.toml`:

```toml
[tool.coverage.report]
fail_under = 85
```

## Comandos

### Execução Básica

```bash
# Testes com cobertura
pytest --cov=src --cov-report=term

# Com relatório HTML
pytest --cov=src --cov-report=html

# Com fail-under
pytest --cov=src --cov-fail-under=85
```

### Relatórios Detalhados

```bash
# Relatório por arquivo
coverage report --show-missing

# Relatório HTML interativo
coverage html
open htmlcov/index.html

# Exportar para XML (CI)
coverage xml
```

### Via Script

```bash
python .agent/skills/test-coverage/scripts/coverage_analyzer.py --gaps
python .agent/skills/test-coverage/scripts/coverage_analyzer.py --recommend
python .agent/skills/test-coverage/scripts/coverage_analyzer.py --report
```

## Configuração

```toml
[tool.coverage.run]
source = ["src"]
omit = ["tests/*", "scripts/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]
```

## Interpretando Relatórios

### Métricas

- **Statements**: Linhas de código executáveis
- **Missing**: Linhas não cobertas
- **Branch**: Cobertura de condicionais (if/else)
- **Partial**: Branches parcialmente cobertos

### Exemplo de Output

```
Name                          Stmts   Miss  Cover   Missing
-----------------------------------------------------------
src/security/crypto.py          150     12    92%   45-48, 120-125
src/data/preprocessing.py       200     70    65%   ...
-----------------------------------------------------------
TOTAL                          2000    300    85%
```

## Identificando Gaps Críticos

### Prioridade Alta (Segurança)
```
src/security/*.py         # Deve ser 95%+
src/data/pseudonym.py     # Dados sensíveis
```

### Prioridade Média (Core)
```
src/training/engine.py    # Training loop
src/serving/inference.py  # API de inferência
```

### Prioridade Baixa
```
src/utils/*.py            # Helpers
scripts/*.py              # Scripts auxiliares
```

---

## 🔬 Padrões Avançados de Teste (Enterprise)

### Mock de Imports Condicionais

Quando uma função é importada dentro de `try/except`, ela não existe como atributo do módulo. Use esta técnica:

```python
from unittest.mock import MagicMock, patch

def test_conditional_import():
    """Test para código com imports opcionais (ex: OpenTelemetry)."""
    mock_span = MagicMock()
    mock_span.is_recording.return_value = True
    mock_span.get_span_context.return_value.is_valid = True
    mock_span.get_span_context.return_value.trace_id = 0x1234

    # 1. Injetar módulo fake em sys.modules
    with patch.dict("sys.modules", {"opentelemetry.trace": MagicMock()}):
        import sys
        mock_otel = sys.modules["opentelemetry.trace"]
        mock_otel.get_current_span = MagicMock(return_value=mock_span)

        # 2. Importar módulo alvo
        import src.telemetry.client as client_module

        # 3. Injetar função no namespace do módulo
        original_flag = client_module.OTEL_AVAILABLE
        client_module.OTEL_AVAILABLE = True
        client_module.get_current_span = mock_otel.get_current_span

        try:
            ctx = client_module._get_otel_context()
            assert ctx["trace_id"] == f"{0x1234:032x}"
        finally:
            # 4. Cleanup
            client_module.OTEL_AVAILABLE = original_flag
            if hasattr(client_module, "get_current_span"):
                delattr(client_module, "get_current_span")
```

**Quando usar:**
- Bibliotecas opcionais (OpenTelemetry, CUDA, etc.)
- Feature flags que controlam imports
- Código com `try/except ImportError`

---

### Mock de Hardware/GPU

```python
@pytest.fixture
def mock_cuda():
    """Mock CUDA para testes sem GPU."""
    with patch("torch.cuda.is_available", return_value=False):
        with patch("torch.cuda.device_count", return_value=0):
            yield


def test_cpu_fallback(mock_cuda):
    """Verifica fallback para CPU quando CUDA não disponível."""
    device = get_device()
    assert device == "cpu"
```

---

### Fixtures para Dados Sensíveis (HIPAA)

```python
@pytest.fixture
def synthetic_patient_data(tmp_path):
    """Gera dados sintéticos para testes sem PHI real."""
    data = {
        "patient_id": str(uuid.uuid4()),  # Fake ID
        "diagnosis": "synthetic_condition",
        "created_at": datetime.now(UTC).isoformat(),
    }
    path = tmp_path / "test_data.json"
    path.write_text(json.dumps(data))
    return path
```

---

### Testes de Timeout e Async

```python
@pytest.mark.timeout(5)
def test_with_timeout():
    """Garante que operação não trava."""
    result = potentially_slow_operation()
    assert result is not None


@pytest.mark.asyncio
async def test_async_operation():
    """Testa código assíncrono."""
    result = await async_fetch_data()
    assert result["status"] == "ok"
```

---

### Skip Condicional (CI-Aware)

```python
import os

CI_ENV = os.getenv("CI", "false").lower() == "true"

@pytest.mark.skipif(CI_ENV, reason="Flaky em ambientes de CI")
def test_timing_sensitive():
    """Teste que depende de timing preciso."""
    pass


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA required")
def test_gpu_operation():
    """Teste que requer GPU."""
    pass
```

---

## Métricas Enterprise

| Métrica | Target | Verificação |
|---------|--------|-------------|
| Cobertura Geral | ≥ 85% | `pytest --cov-fail-under=85` |
| `src/security/` | ≥ 95% | Audit manual |
| `src/serving/` | ≥ 90% | CI check |
| Branch Coverage | ≥ 70% | `--cov-branch` |
| Mock Isolation | 100% | Sem side-effects |
| Test Duration | < 60s (unit) | `pytest --durations=10` |
| Flaky Tests | 0 | `pytest-rerunfailures` |

---

## Troubleshooting

### Erro: `module does not have attribute 'X'`

**Causa**: Função importada dentro de `try/except`
**Solução**: Use `patch.dict("sys.modules", ...)` conforme exemplo acima

### Erro: `CUDA not available`

**Causa**: Teste requer GPU mas CI não tem
**Solução**: `@pytest.mark.skipif(not torch.cuda.is_available(), ...)`

### Erro: `Timeout` em testes

**Causa**: Operação bloqueante ou loop infinito
**Solução**: `@pytest.mark.timeout(N)` + mock de I/O
