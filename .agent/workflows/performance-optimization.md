---
description: Workflow de otimização de performance com benchmarks e profiling
---

# Performance Optimization Workflow

Este workflow executa análise de performance e identifica oportunidades de otimização.

## Execução

### Fase 1: Baseline

// turbo
1. **Executar Benchmarks**
```bash
pytest --benchmark-only -v 2>/dev/null || echo "No benchmarks found"
```

// turbo
2. **Verificar Tempo de Startup**
```bash
time python -c "from src import cli" 2>&1 | tail -3
```

### Fase 2: Profiling

3. **CPU Profiling** (executar manualmente se necessário)
```bash
python -m cProfile -o profile.prof scripts/train.py --max-epochs 1 --dry-run
```

4. **Analisar Profile**
```bash
python -c "import pstats; p=pstats.Stats('profile.prof'); p.sort_stats('cumulative').print_stats(15)"
```

### Fase 3: Análise de Memória

5. **Memory Profiling** (opcional)
```bash
python -m memory_profiler scripts/train.py --max-epochs 1 --dry-run
```

### Fase 4: Análise de Dataloader

// turbo
6. **Benchmark Dataloader**
```bash
python scripts/benchmark_dataloader.py --samples 100 2>/dev/null || echo "Dataloader benchmark skipped"
```

### Fase 5: Identificar Hotspots

// turbo
7. **Funções Complexas**
```bash
ruff check --select C901 src/ --output-format=text | head -20
```

// turbo
8. **Arquivos Grandes**
```bash
find src/ -name "*.py" -exec wc -l {} + | sort -rn | head -10
```

## Métricas Alvo

| Componente | Métrica | Target |
|------------|---------|--------|
| Startup | Import time | < 5s |
| Dataloader | Throughput | > 1000 samples/s |
| Inference | Latency | < 50ms |
| Training | GPU Util | > 80% |

## Otimizações Comuns

### CPU
- Vectorização com NumPy
- Paralelização de I/O
- Caching de resultados

### Memória
- Generators em vez de listas
- Memory-mapped files
- Limpeza de cache

### GPU
- Mixed precision (fp16)
- Gradient checkpointing
- Batch size optimization

## Relatório

Após execução, resultados em:
```
artifacts/benchmark_report.txt
benchmark_results.json
```

## Comando Único

```bash
make skill-performance
```

## Skills Relacionadas

Consulte as skills avançadas para técnicas detalhadas:

| Skill | Descrição |
|-------|-----------|
| `performance-profiling` | HardwareProfiles, AMP, pre-flight |
| `advanced-ml-optimization` | PEFT, QLoRA, JAX/XLA, SAM |
| `training-circuit-quality` | Gradient accumulation, flush |

### Técnicas Avançadas Disponíveis

- **HardwareProfile System**: Auto-detecção GPU/CPU com configs otimizadas
- **Compound Scaling**: Escalonamento conjunto width×depth×resolution
- **QLoRA**: Treinamento 4-bit para modelos 70B+
- **Non-blocking Transfer**: `to(device, non_blocking=True)`
- **Polars**: 10x mais rápido que Pandas para ETL

Para consultar: `view_file .agent/skills/<skill>/SKILL.md`
