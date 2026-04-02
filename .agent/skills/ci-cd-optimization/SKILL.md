---
name: ci-cd-optimization
description: Otimizar pipelines CI/CD (GitHub Actions) para performance, confiabilidade e troubleshooting em projetos Python/ML. Usar quando houver lentidão de jobs, falhas de cache, testes flaky, diferenças entre ambiente local e runner, ou necessidade de hardening no workflow.
---

# CI/CD Optimization Skill

## Objetivo

Otimizar pipelines de CI/CD para velocidade, confiabilidade e custo, com foco em projetos Python/ML.

---

## Cache de Dependências

### ✅ Padrão Correto (actions/cache separado)

```yaml
- name: Setup Python
  uses: actions/setup-python@v5
  with:
    python-version: ${{ matrix.python-version }}

- name: Cache pip dependencies
  uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ matrix.python-version }}-${{ hashFiles('**/requirements.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-${{ matrix.python-version }}-
      ${{ runner.os }}-pip-

- name: Install Dependencies
  run: |
    mkdir -p ~/.cache/pip  # Garante que diretório existe
    pip install -r requirements.txt
```

### ❌ Padrão Problemático

```yaml
# Pode falhar com: "Cache folder path doesn't exist on disk"
- name: Setup Python
  uses: actions/setup-python@v5
  with:
    python-version: "3.11"
    cache: 'pip'  # Cache embutido pode falhar
```

**Erro comum:**
```
Error: Cache folder path is retrieved for pip but doesn't exist on disk:
/home/runner/.cache/pip
```

**Solução:** Use `actions/cache@v4` separadamente + `mkdir -p ~/.cache/pip`

---

## Otimizações de Performance

### 1. PyTorch CPU-Only (CI)

```yaml
# ~200MB vs ~2GB com CUDA
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### 2. OpenCV Headless

```yaml
# Sem dependências X11
pip install opencv-python-headless>=4.8.0
```

### 3. Paralelização de Jobs

```yaml
strategy:
  fail-fast: false  # Continua outros jobs se um falhar
  matrix:
    python-version: ["3.11", "3.12"]
```

### 4. Cancelamento de Runs Duplicados

```yaml
concurrency:
  group: ci-${{ github.workflow }}-${{ github.head_ref || github.run_id }}
  cancel-in-progress: true
```

---

## Caching Avançado

### Cache de Múltiplos Paths

```yaml
- name: Cache dependencies
  uses: actions/cache@v4
  with:
    path: |
      ~/.cache/pip
      ~/.cache/pre-commit
      .mypy_cache
    key: ${{ runner.os }}-deps-${{ hashFiles('**/requirements*.txt', '.pre-commit-config.yaml') }}
```

### Cache de Rust/Cargo

```yaml
- name: Cache Rust
  uses: actions/cache@v4
  with:
    path: |
      ~/.cargo/registry
      ~/.cargo/git
      target/
    key: ${{ runner.os }}-cargo-${{ hashFiles('**/Cargo.lock') }}
```

---

## Troubleshooting

### Erro: Cache folder doesn't exist

**Causa:** Cache embutido do `setup-python` falha em runners limpos
**Solução:**
```yaml
- name: Cache pip dependencies
  uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}

- name: Install
  run: |
    mkdir -p ~/.cache/pip
    pip install -r requirements.txt
```

### Erro: Teste de CLI falha só no CI por truncamento de output

**Sintoma:** testes de `typer`/`rich` passam localmente e falham no runner porque o output mostra `…` no caminho.

**Causa:** `rich.Table` usa elipse na coluna longa por padrão (`overflow="ellipsis"`), escondendo sufixos importantes como `data`/`models`.

**Solução no código da CLI:**
```python
table.add_column("Path", style="dim", overflow="fold")
```

**Solução no teste:**
```python
result = runner.invoke(app, ["status"], env={"COLUMNS": "200"})
assert "Data Directory" in result.stdout
assert "Models Directory" in result.stdout
assert "data" in result.stdout
```

**Checklist de robustez:**
1. Rodar o teste alvo com largura pequena (`COLUMNS=80`) para confirmar que o caminho continua legível.
2. Rodar o teste alvo com largura ampla (`COLUMNS=200`) para manter estabilidade no CI.
3. Rodar `make ci-gh-tests` antes do push.

### Erro: Timeout em instalação

**Causa:** Rede lenta ou pacote grande
**Solução:**
```yaml
pip install --timeout 300 -r requirements.txt
```

### Erro: Disk space

**Causa:** Runners têm ~14GB livres
**Solução:**
```yaml
- name: Free disk space
  run: |
    sudo rm -rf /usr/share/dotnet
    sudo rm -rf /opt/ghc
    df -h
```

### Erro: `PermissionError` com `SemLock` em testes de DataLoader multiprocess

**Sintoma:** falhas em testes de throughput/stress com traceback em `multiprocessing.synchronize.SemLock`.

**Causa:** ambiente sandbox local sem permissão para semáforos compartilhados; não é necessariamente defeito do código.

**Solução:**
1. Reexecutar a suíte fora do sandbox quando houver suporte a multiprocess.
2. Confirmar no runner do GitHub Actions antes de alterar código produtivo.
3. Tratar como problema de ambiente se o CI oficial estiver verde.

---

## Métricas de CI/CD

| Métrica | Target | Verificação |
|---------|--------|-------------|
| Build Time | < 5 min | Workflow summary |
| Cache Hit Rate | > 80% | Cache step output |
| Flaky Tests | 0 | `pytest-rerunfailures` |
| Coverage | ≥ 85% | `--cov-fail-under` |
| Matrix Success | 100% | All Python versions |

---

## Security Hardening

### Pin Actions por SHA

```yaml
# ✅ Correto: SHA pinado
uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4

# ❌ Evitar: Tag mutável
uses: actions/checkout@v4
```

### Minimal Permissions

```yaml
permissions:
  contents: read  # Apenas leitura
```

### Secrets Seguros

```yaml
env:
  API_KEY: ${{ secrets.API_KEY }}  # Nunca em logs
```

---

## Comandos

```bash
# Testar workflow localmente
act -j quality-gate  # Requer Docker

# Reproduzir gate completo do projeto
make ci-gh-tests

# Validar YAML
yamllint .github/workflows/ci.yml

# Ver cache usage
gh cache list
gh cache delete --all  # Limpar cache
```
