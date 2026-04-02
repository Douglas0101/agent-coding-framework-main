---
name: dead-code-removal
description: Detecção e eliminação de código morto com vulture e análise AST
---

# Dead Code Removal Skill

## Objetivo

Identificar e remover código morto (funções não chamadas, imports não usados, variáveis nunca lidas) para reduzir complexidade e melhorar mantenibilidade.

## Ferramentas Utilizadas

| Ferramenta | Propósito |
|------------|-----------|
| **vulture** | Detecta código morto (funções, classes, variáveis) |
| **autoflake** | Remove imports não usados |
| **Ruff F401** | Imports não utilizados |
| **Ruff F841** | Variáveis não utilizadas |

## Comandos

### Detecção com Vulture

```bash
# Scan básico
vulture src/

# Com confidence mínimo (reduz falsos positivos)
vulture src/ --min-confidence 80

# Gerar whitelist de falsos positivos
vulture src/ --make-whitelist > vulture_whitelist.py
```

### Remoção de Imports

```bash
# Via Ruff (detecta)
ruff check --select F401 .

# Via Ruff (corrige)
ruff check --select F401 --fix .

# Via autoflake (mais agressivo)
autoflake --in-place --remove-all-unused-imports src/
```

### Via Script

```bash
python .agent/skills/dead-code-removal/scripts/dead_code_finder.py --scan
python .agent/skills/dead-code-removal/scripts/dead_code_finder.py --imports
python .agent/skills/dead-code-removal/scripts/dead_code_finder.py --report
```

## Tipos de Código Morto

### 1. Funções Não Chamadas
```python
def unused_helper():  # Nunca chamada
    pass
```

### 2. Imports Não Usados
```python
import os  # Nunca usado
from typing import List  # List nunca usado
```

### 3. Variáveis Não Lidas
```python
def process():
    result = compute()  # result nunca usado
    return True
```

### 4. Código Após Return
```python
def get_value():
    return 42
    print("never executed")  # Código morto
```

### 5. Condições Sempre False
```python
if False:
    do_something()  # Nunca executado
```

## Whitelist de Falsos Positivos

Vulture pode reportar falsos positivos para:
- Callbacks definidos mas chamados por frameworks
- Métodos mágicos (__init__, __str__)
- APIs públicas não usadas internamente

Crie `.vulture_whitelist.py`:
```python
# Callbacks usados por PyTorch
forward  # unused method
configure_optimizers  # unused method

# APIs públicas
predict  # unused method
serve  # unused function
```

Execute com whitelist:
```bash
vulture src/ .vulture_whitelist.py
```

## Workflow Seguro

### 1. Identificar
```bash
vulture src/ --min-confidence 90 > dead_code_candidates.txt
```

### 2. Verificar Manualmente
- Confirmar que não é API pública
- Verificar se não é callback de framework
- Checar se não é código de debug necessário

### 3. Remover com Backup
```bash
git stash  # Backup
# Remover código
git diff  # Verificar mudanças
pytest  # Garantir testes passam
```

### 4. Commitar
```bash
git commit -m "chore: remove dead code identified by vulture"
```

## Integração CI

```yaml
- name: Dead Code Check
  run: |
    vulture src/ .vulture_whitelist.py --min-confidence 80
```

## Métricas de Sucesso

- Zero código morto com confidence > 80%
- Zero imports não utilizados
- Redução de LOC após cleanup
- Testes continuam passando
