---
name: complexity-reduction
description: Análise e redução de complexidade ciclomática e cognitiva
---

# Complexity Reduction Skill

## Objetivo

Analisar e reduzir complexidade do código através de métricas objetivas (complexidade ciclomática, cognitiva, linhas de código) para melhorar mantenibilidade.

## Métricas de Complexidade

### Complexidade Ciclomática (McCabe)
Conta caminhos independentes no código.

| Score | Classificação | Ação |
|-------|---------------|------|
| 1-5 | A (Simples) | ✅ OK |
| 6-10 | B (Moderado) | ⚠️ Monitorar |
| 11-20 | C (Complexo) | 🔧 Refatorar |
| 21-30 | D (Alarmante) | 🚨 Urgente |
| 31+ | F (Inaceitável) | ⛔ Bloquear |

### Complexidade Cognitiva
Mede dificuldade de entender o código (nesting, breaks, recursão).

### Índice de Mantenibilidade
Score 0-100 baseado em volume, complexidade e duplicação.

| Score | Classificação |
|-------|---------------|
| 85-100 | Excelente |
| 65-84 | Normal |
| 0-64 | Difícil manutenção |

## Comandos

### Análise com radon

```bash
# Complexidade ciclomática
radon cc src/ -a -s

# Mostrar apenas complexos (C+)
radon cc src/ -a -nc

# Índice de mantenibilidade
radon mi src/ -s

# Métricas brutas (LOC, LLOC, etc)
radon raw src/ -s
```

### Análise com Ruff

```bash
# Verificar funções muito complexas
ruff check --select C901 .

# Com threshold específico
ruff check --select C901 . --max-complexity 10
```

### Via Script

```bash
python .agent/skills/complexity-reduction/scripts/complexity_analyzer.py --analyze
python .agent/skills/complexity-reduction/scripts/complexity_analyzer.py --hotspots
python .agent/skills/complexity-reduction/scripts/complexity_analyzer.py --report
```

## Configuração

Em `pyproject.toml`:

```toml
[tool.ruff.lint.mccabe]
max-complexity = 10  # Máximo permitido
```

## Técnicas de Redução

### 1. Extract Method
```python
# Antes (complexidade 8)
def process_order(order):
    if order.is_valid:
        if order.has_items:
            if order.payment_verified:
                # 20 linhas de lógica
                ...

# Depois (complexidade 2 cada)
def process_order(order):
    validate_order(order)
    process_payment(order)
    ship_order(order)
```

### 2. Replace Conditional with Polymorphism
```python
# Antes
def calculate_shipping(order):
    if order.type == "express":
        return order.weight * 2.5
    elif order.type == "standard":
        return order.weight * 1.0
    elif order.type == "free":
        return 0

# Depois
class ShippingStrategy(Protocol):
    def calculate(self, weight: float) -> float: ...

STRATEGIES = {
    "express": ExpressShipping(),
    "standard": StandardShipping(),
    "free": FreeShipping(),
}

def calculate_shipping(order):
    return STRATEGIES[order.type].calculate(order.weight)
```

### 3. Guard Clauses (Early Return)
```python
# Antes
def process(data):
    if data:
        if data.is_valid:
            if data.has_content:
                return data.content
    return None

# Depois
def process(data):
    if not data:
        return None
    if not data.is_valid:
        return None
    if not data.has_content:
        return None
    return data.content
```

### 4. Decompose Conditional
```python
# Antes
if (date.month >= 6 and date.month <= 8) or \
   (date.month == 12 and date.day >= 21):
    charge = base_charge * 1.5

# Depois
def is_summer(date):
    return date.month >= 6 and date.month <= 8

def is_holiday_season(date):
    return date.month == 12 and date.day >= 21

if is_summer(date) or is_holiday_season(date):
    charge = base_charge * 1.5
```

## Hotspots do Projeto

Arquivos tipicamente complexos em projetos ML:

```
src/training/engine.py      # Training loop - comum ser complexo
src/data/preprocessing.py   # Pipelines de dados
src/serving/inference.py    # Lógica de inferência
```

### Threshold por Camada

| Camada | Max Complexity |
|--------|---------------|
| `security/` | 8 |
| `serving/` | 10 |
| `training/` | 12 |
| `utils/` | 6 |

## Métricas de Sucesso

- Complexidade média < 5
- Nenhuma função com complexidade > 15
- Índice de mantenibilidade > 65
- Funções com > 50 linhas: 0
