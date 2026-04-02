---
name: gpu-profiler
description: "Profiling de GPU CUDA (PyTorch/NVIDIA) para identificar gargalos de kernel, memoria, transferencia e utilizacao. Usar quando precisar de: (1) analisar performance de treino/inferencia em GPU, (2) investigar consumo de VRAM e overhead de data transfer, (3) gerar traces com torch.profiler, nsys ou ncu."
---

# GPU Profiler Skill

## Objetivo

- Diagnosticar gargalos de GPU CUDA em treino/inferencia.
- Medir uso de VRAM, throughput e tempo por step.
- Gerar traces para visualizacao (TensorBoard, Nsight).

## Checklist rapido

1. Fixar batch size e seed.
2. Aquecer 5-10 steps antes de medir.
3. Medir janelas curtas (20-50 steps) para trace.
4. Isolar data loader vs compute quando possivel.

## Comandos

### Snapshot rapido (CUDA)

```bash
nvidia-smi
nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used,utilization.gpu,temperature.gpu --format=csv
nvidia-smi dmon -s pucm
```

### Torch profiler (PyTorch)

```python
import torch
from torch.profiler import (
    ProfilerActivity,
    profile,
    record_function,
    schedule,
    tensorboard_trace_handler,
)

with profile(
    activities=[ProfilerActivity.CPU, ProfilerActivity.CUDA],
    schedule=schedule(wait=1, warmup=1, active=3, repeat=1),
    on_trace_ready=tensorboard_trace_handler("logs/profiler"),
    record_shapes=True,
    profile_memory=True,
    with_stack=True,
) as prof:
    for step, batch in enumerate(loader):
        with record_function("forward"):
            outputs = model(batch)
        with record_function("backward"):
            loss = loss_fn(outputs)
            loss.backward()
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        prof.step()
```

### Visualizar trace

```bash
tensorboard --logdir logs/profiler
```

### Nsight Systems (nsys) - trace end-to-end

```bash
nsys profile --trace=cuda,nvtx,osrt --sample=none -o logs/nsys python scripts/train.py --profile gpu
```

### Nsight Compute (ncu) - kernel stats

```bash
ncu --set full --target-processes all -o logs/ncu python scripts/train.py --profile gpu
```

## Atalhos no projeto

- Usar `scripts/train.py --profile gpu` para forcar uso de GPU.
- Usar `scripts/benchmark_dataloader.py --profile --n-batches 20` para trace do dataloader.
- Adicionar `ProfilerActivity.CUDA` quando `torch.cuda.is_available()` se precisar de GPU no trace do dataloader.

## Dicas rapidas

- Chamar `torch.cuda.synchronize()` antes/depois de timers manuais.
- Usar batch size fixo e desativar validacao durante o trace.
- Marcar regioes criticas com `record_function("nome")` para facilitar leitura no trace.
