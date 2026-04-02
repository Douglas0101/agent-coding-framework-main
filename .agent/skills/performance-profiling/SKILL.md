---
name: performance-profiling
description: Benchmarks automatizados e profiling de CPU/memória
---

# Performance Profiling Skill

## Objetivo

Automatizar benchmarks de performance, detectar regressões, e identificar hotspots de CPU e memória para otimização.

## Ferramentas Utilizadas

| Ferramenta | Propósito |
|------------|-----------|
| **pytest-benchmark** | Benchmarks automatizados |
| **cProfile** | Profiling de CPU |
| **memory_profiler** | Profiling de memória |
| **py-spy** | Sampling profiler (baixo overhead) |

## Comandos

### Benchmarks

```bash
# Executar todos os benchmarks
pytest --benchmark-only

# Com comparação a baseline
pytest --benchmark-only --benchmark-compare

# Salvar resultados
pytest --benchmark-only --benchmark-autosave

# Histograma de distribuição
pytest --benchmark-only --benchmark-histogram
```

### Profiling

```bash
# CPU profiling com cProfile
python -m cProfile -o profile.prof scripts/train.py

# Visualizar resultados
python -c "import pstats; p=pstats.Stats('profile.prof'); p.sort_stats('cumulative').print_stats(20)"

# Memory profiling
python -m memory_profiler scripts/train.py
```

### Via Script

```bash
python .agent/skills/performance-profiling/scripts/run_benchmarks.py --compare
python .agent/skills/performance-profiling/scripts/run_benchmarks.py --profile-cpu
python .agent/skills/performance-profiling/scripts/run_benchmarks.py --profile-memory
```

## Benchmarks Existentes

O projeto já possui benchmarks em `tests/perf/`:

```python
# tests/perf/test_dataloader_bench.py
def test_dataloader_throughput(benchmark):
    result = benchmark(dataloader.load_batch, batch_size=32)
    assert result.stats.mean < 0.1  # < 100ms
```

## Métricas Importantes

### Dataloader
- **Throughput**: samples/segundo
- **Latência**: tempo para primeiro batch
- **Memória**: pico de uso durante carregamento

### Modelo
- **Tempo de inferência**: ms/sample
- **GPU Utilization**: % durante training
- **Batch processing time**: tempo total por batch

### API/Serving
- **Latência P50/P95/P99**: tempo de resposta
- **Throughput**: requests/segundo
- **Cold start**: tempo de inicialização

## Detecção de Regressões

Configure em CI:

```yaml
- name: Run Benchmarks
  run: |
    pytest --benchmark-only \
           --benchmark-compare \
           --benchmark-compare-fail=mean:10%
```

Falha se performance piorar >10%.

## Profiling em Produção

### Sampling Profiler (py-spy)

```bash
# Attach a processo rodando
py-spy record -o profile.svg --pid $PID

# Durante execução
py-spy top --pid $PID
```

### Flame Graphs

```bash
# Gerar flame graph
py-spy record -o flamegraph.svg --format speedscope -- python train.py
```

## Otimizações Comuns

### CPU
1. Vectorização com NumPy
2. JIT compilation (numba)
3. Paralelização (joblib, multiprocessing)

### Memória
1. Generators em vez de listas
2. Memory-mapped files para grandes datasets
3. Garbage collection manual em training loops

### GPU
1. Mixed precision (fp16)
2. Gradient checkpointing
3. Batch size optimization

---

## Técnicas Avançadas de Hardware

### HardwareProfile System

O projeto implementa um sistema de profiles de hardware em `src/config/hardware.py`:

```python
from src.config.hardware import get_profile, optimize_model_for_hardware

# Selecionar profile por nome ou auto-detectar
profile = get_profile("auto")  # Detecta GPU/CPU automaticamente

# Aplicar otimizações ao modelo
model = optimize_model_for_hardware(model, profile)
```

**Profiles Disponíveis:**

| Profile | Device | Batch | Workers | AMP | Compile |
|---------|--------|-------|---------|-----|---------|
| `cpu` | CPU | 16 | 4 | ❌ | ❌ |
| `cpu_low` | CPU | 8 | 2 | ❌ | ❌ |
| `gpu` | CUDA | 64 | 8 | ✅ | ✅ |
| `gpu_rtx3060` | CUDA | 96 | 12 | ✅ | ✅ |
| `gpu_low_vram` | CUDA | 32 | 4 | ✅ | ✅ |

### Memory Format Optimization

```python
# Channels Last para GPU (melhor aproveitamento de cache)
if profile.device == "cuda":
    model = model.to(memory_format=torch.channels_last)
```

### DataLoader Optimization

```python
from src.config.hardware import get_dataloader_kwargs

kwargs = get_dataloader_kwargs(profile)
# Returns: {num_workers, pin_memory, prefetch_factor, persistent_workers}

loader = DataLoader(dataset, **kwargs)
```

---

## Controle de Memória Vetorial

### Gradient Checkpointing (Tradeoff Compute ↔ Memory)

```python
from torch.utils.checkpoint import checkpoint_sequential

# Reduz uso de memória em 70%, aumenta tempo em 20%
output = checkpoint_sequential(modules, segments=4, input)
```

### Memory Pinning para GPU

```python
# pin_memory=True: Acelera transferência CPU→GPU
# Evita cópia extra para memória paginada
loader = DataLoader(dataset, pin_memory=True, num_workers=8)
```

### VRAM Estimation (Pre-flight)

```python
from src.config.hardware_intel import HardwareIntelligence

hw = HardwareIntelligence()
estimate = hw.estimate_resources(
    batch_size=32,
    epochs=10,
    dataset_size=10000,
    model_params=5_000_000,
)
print(f"Total Memory: {estimate.total_memory_gb:.2f} GB")
print(f"Recommended Batch: {estimate.recommended_batch_size}")
```

---

## Processamento Paralelo com Cache

### DataLoader Workers

```python
# Regra: num_workers = min(cpu_cores, 4 * num_gpus)
# Evita contenção em disco com muitos workers

loader = DataLoader(
    dataset,
    num_workers=8,
    prefetch_factor=4,        # Batches em cache por worker
    persistent_workers=True,  # Mantém workers vivos entre epochs
)
```

### Prefetch Factor Tuning

| Hardware | prefetch_factor | Motivo |
|----------|-----------------|--------|
| SSD + GPU | 4 | I/O rápido, prefetch agressivo |
| HDD + GPU | 2 | I/O lento, evita starvation |
| CPU-only | 2 | Menos paralelismo |

### Non-blocking Data Transfer

```python
# non_blocking=True: Não espera término da transferência
images = images.to(device, non_blocking=True)
targets = targets.to(device, non_blocking=True)

# CUDA streams executam em paralelo com compute
```

---

## Mixed Precision (AMP)

```python
from torch.cuda.amp import autocast, GradScaler

scaler = GradScaler()

with autocast(dtype=torch.float16):
    output = model(input)
    loss = criterion(output, target)

scaler.scale(loss).backward()
scaler.unscale_(optimizer)
torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
scaler.step(optimizer)
scaler.update()
```

**Benefícios:**
- 2x menos memória para ativações
- ~50% mais rápido em GPUs com Tensor Cores
- Precision mantida via loss scaling

---

## Pre-flight Validation

```python
from src.config.hardware_intel import run_preflight_checks

result = run_preflight_checks(
    batch_size=32,
    epochs=10,
    dataset_size=10000,
    strict=True,
    verbose=True,
)

if not result.can_proceed:
    raise RuntimeError(f"Pre-flight failed: {result.errors}")
```

**Validações:**
- Memória suficiente para batch size
- Disk space para checkpoints
- GPU compute capability
- Estimativa de tempo de treinamento

---

## torch.compile() Optimization

```python
# PyTorch 2.0+ JIT compilation
model = torch.compile(model, mode="reduce-overhead")
# Modos: default, reduce-overhead, max-autotune
```

**Ganhos típicos:**
- 10-30% mais rápido após warmup
- Funciona melhor com modelos estáticos
- Compatível com AMP

---

## Métricas de Sucesso

- Benchmarks passando sem regressões
- Dataloader throughput > 1000 samples/s
- Inferência < 50ms/sample
- Memória estável durante training (sem memory leaks)
- Pre-flight score > 80/100
- GPU utilization > 80% durante training
