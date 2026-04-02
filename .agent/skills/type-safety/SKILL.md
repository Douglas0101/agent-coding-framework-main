---
name: type-safety
description: Verificação de tipos com MyPy em modo strict progressivo
---

# Type Safety Skill

## Objetivo

Garantir type safety através de verificação estática com MyPy, promovendo adoção progressiva de tipagem strict e eliminando bugs em tempo de desenvolvimento.

## Ferramentas Utilizadas

| Ferramenta | Propósito |
|------------|-----------|
| **MyPy** | Verificação estática de tipos |
| **pyright** | Alternativa/complemento para tipos complexos |

## Níveis de Strictness

### Nível 1: Básico (Atual)
```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
```

### Nível 2: Moderado
```toml
disallow_untyped_defs = true
disallow_incomplete_defs = true
```

### Nível 3: Strict
```toml
strict = true
disallow_any_generics = true
```

## Comandos

### Verificação Básica

```bash
# Verificar todo o projeto
mypy .

# Verificar módulo específico
mypy src/security/

# Com relatório detalhado
mypy . --html-report mypy_report/
```

### Análise de Cobertura

```bash
# Ver estatísticas de tipagem
mypy . --txt-report -

# Listar arquivos sem tipos
mypy . --any-exprs-report -
```

## Configuração Atual

```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false  # Progressivo

[[tool.mypy.overrides]]
module = [
    "torch.*",
    "torchvision.*",
    # ... libs sem stubs
]
ignore_missing_imports = true
```

## Erros Comuns e Soluções

### `error: Function is missing a type annotation`
```python
# Antes
def process(data):
    return data.strip()

# Depois
def process(data: str) -> str:
    return data.strip()
```

### `error: Incompatible return type`
```python
# Antes
def get_value() -> int:
    return None  # Error!

# Depois
def get_value() -> int | None:
    return None
```

### `error: Module has no attribute`
```python
# Adicione ao pyproject.toml:
[[tool.mypy.overrides]]
module = ["problematic_module"]
ignore_missing_imports = true
```

## Workflow de Adoção Progressiva

1. **Fase 1**: Anotar funções públicas em `src/`
2. **Fase 2**: Habilitar `disallow_untyped_defs` para `src/security/`
3. **Fase 3**: Expandir para `src/training/`
4. **Fase 4**: Full strict mode

## Padrões de Tipagem

### Generics
```python
from typing import TypeVar

T = TypeVar("T")

def first(items: list[T]) -> T | None:
    return items[0] if items else None
```

### Protocols (Duck Typing)
```python
from typing import Protocol

class Trainable(Protocol):
    def train(self, data: Dataset) -> None: ...
    def evaluate(self) -> float: ...
```

### TypedDict (Dicionários Tipados)
```python
from typing import TypedDict

class Config(TypedDict):
    learning_rate: float
    batch_size: int
    epochs: int
```

### NumPy ↔ Python Type Conversion

NumPy types (`np.int64`, `np.float64`) are incompatible with native Python types in type signatures.

```python
# ❌ Erro: Incompatible type "signedinteger[_64Bit]"; expected "int"
indices = np.argsort(probs)  # Returns np.int64
gradcam.generate(img, target_class=indices[0])

# ✅ Correto: Conversão explícita para tipo nativo
gradcam.generate(img, target_class=int(indices[0]))
```

**Padrões Comuns:**
```python
# Array → List nativa
int_list: list[int] = arr.tolist()

# Elemento único → tipo nativo
native_int: int = int(np_int64_value)
native_float: float = float(np_float64_value)

# Bool numpy → bool Python
native_bool: bool = bool(np_bool_value)
```

### no-any-return Pattern

Quando mypy reporta `Returning Any from function declared to return X`:

```python
# ❌ Erro: Linear.__call__ returns Any para mypy
def forward(self, x: torch.Tensor) -> torch.Tensor:
    return self.linear(x)

# ✅ Correto: Annotate intermediate result
def forward(self, x: torch.Tensor) -> torch.Tensor:
    result: torch.Tensor = self.linear(x)
    return result
```

## Métricas de Sucesso

- Zero erros MyPy em CI
- 80%+ de funções com type annotations
- Módulos críticos (`security/`, `serving/`) 100% tipados
- Conversões explícitas numpy → Python em interfaces typadas
