---
name: training-circuit-quality
description: Métricas avançadas e invariantes para circuitos de treinamento robustos
---

# Training Circuit Quality Skill

Técnicas avançadas para garantir qualidade, determinismo e reprodutibilidade em circuitos de treinamento de ML.

## Invariantes Fundamentais

### Invariante A: Gradient Accumulation Step Count

```
optimizer_steps = ceil(N / K) para N > 0
optimizer_steps = 0           para N = 0
```

Onde:
- `N` = micro-batches processados
- `K` = grad_accum_steps

**Problema Comum**: Loop de treinamento que esquece de "flush" os gradients acumulados no fim da época quando `N % K != 0`.

**Solução**: Implementar `flush_gradients()` que executa optimizer step se houver gradients pendentes:

```python
def flush_gradients(self) -> dict[str, Any]:
    """Flush pending accumulated gradients at end of epoch."""
    stats = {"flushed": False, "accum_counter_before": self._accum_counter}

    if self._accum_counter == 0:
        return stats  # Nothing to flush

    # Execute optimizer step
    if self.scaler is not None:
        self.scaler.unscale_(self.optimizer)
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm)
        self.scaler.step(self.optimizer)
        self.scaler.update()
    else:
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm)
        self.optimizer.step()

    self.optimizer.zero_grad(set_to_none=True)
    self._accum_counter = 0
    stats["flushed"] = True
    return stats
```

### Invariante B: Ordem AMP Correta

A sequência correta para Automatic Mixed Precision:

1. `scaler.scale(loss).backward()`
2. `scaler.unscale_(optimizer)` (antes de clip)
3. `torch.nn.utils.clip_grad_norm_(...)`
4. `scaler.step(optimizer)`
5. `scaler.update()`
6. `optimizer.zero_grad(set_to_none=True)`

### Invariante C: Zero Grad Eficiente

Preferir `set_to_none=True` para eficiência de memória:

```python
optimizer.zero_grad(set_to_none=True)  # ✅ Melhor
optimizer.zero_grad()                   # ❌ Menos eficiente
```

### Invariante D: Clip Timing

Gradiente clipping deve ocorrer apenas no momento do optimizer step, não a cada micro-batch.

---

## Técnicas de Refactoring para Complexidade

### Extração de Helpers para C901

Quando uma função atinge complexidade ciclomática > 10:

1. **Extrair verificações de condição**:
```python
def _check_interrupt_requested(self) -> bool:
    """Check if graceful stop was requested."""
    if self._interrupt_guard and self._interrupt_guard.stop_requested:
        self.interrupted = True
        self.interrupt_reason = self._interrupt_guard.reason
        return True
    return False
```

2. **Extrair processamento de batch**:
```python
def _process_batch(
    self,
    images: torch.Tensor,
    targets: torch.Tensor,
    batch_idx: int,
    accum_steps: int,
) -> float:
    """Process a single training batch."""
    images = images.to(self.device, non_blocking=True)
    targets = targets.to(self.device, non_blocking=True)

    if self.config.channels_last and self.config.device == "cuda":
        images = images.to(memory_format=torch.channels_last)

    if self.scaler is not None:
        return self._forward_backward_amp(images, targets, batch_idx, accum_steps)
    return self._forward_backward_standard(images, targets, batch_idx, accum_steps)
```

---

## Padronização de Artefatos

### CalibArtifact v1 (JSON)

Formato padronizado para artefatos de calibração:

```json
{
  "version": 1,
  "temperature": 1.0234,
  "method": "temperature_scaling",
  "created_at": "2026-01-16T04:06:08+00:00"
}
```

**Campos obrigatórios**:
- `version`: Inteiro para versionamento de schema
- `temperature`: Float com valor de temperatura
- `method`: String identificando método de calibração
- `created_at`: ISO 8601 timestamp

---

## SWA BatchNorm Update

Ao usar Stochastic Weight Averaging, atualizar estatísticas de BatchNorm após finalização:

```python
def finalize_swa(self, train_loader: Any = None) -> None:
    """Finalize SWA with optional BN stats update."""
    if self._swa_model is None:
        return

    # Check if model has BatchNorm layers
    has_bn = any(
        isinstance(m, torch.nn.BatchNorm1d | torch.nn.BatchNorm2d | torch.nn.BatchNorm3d)
        for m in self._model.modules()
    )

    if has_bn and train_loader is not None:
        from torch.optim.swa_utils import update_bn
        update_bn(train_loader, self._swa_model, device=self._device)
    elif has_bn:
        logger.warning("Model has BatchNorm but no train_loader provided.")

    self._model.load_state_dict(self._swa_model.module.state_dict())
```

---

## Testes para Invariantes

### Parametrização de Edge Cases

```python
@pytest.mark.parametrize("n_batches,accum_steps,expected_steps", [
    (5, 2, 3),   # ceil(5/2) = 3, flush occurs
    (4, 2, 2),   # ceil(4/2) = 2, no flush
    (1, 8, 1),   # ceil(1/8) = 1, flush occurs
    (8, 8, 1),   # ceil(8/8) = 1, no flush
    (10, 3, 4),  # ceil(10/3) = 4, flush occurs
])
def test_optimizer_steps_equal_ceil_division(
    self, n_batches: int, accum_steps: int, expected_steps: int
) -> None:
    """Verify optimizer_steps = ceil(N/K) invariant."""
    # ... test implementation
```

---

## Observability

### Logging de Eventos Críticos

```python
logger.info(
    "End-of-epoch flush: %d accumulated gradients applied",
    stats["accum_counter_before"],
)
```

### Callbacks para Flush

```python
self._notify_callbacks(
    "on_flush",
    epoch=epoch,
    flushed=True,
    accum_counter_before=count,
)
```

---

## Learning Rate Schedulers com Warmup

### Linear Warmup + Cosine Decay

O scheduler mais recomendado para treino de redes profundas:

```python
import torch
import math


class CosineAnnealingWarmupRestarts(torch.optim.lr_scheduler._LRScheduler):
    """Cosine annealing scheduler com warmup."""

    def __init__(
        self,
        optimizer: torch.optim.Optimizer,
        max_lr: float,
        warmup_epochs: int,
        total_epochs: int,
        min_lr: float = 1e-7,
        warmup_start_lr: float = 1e-8,
    ):
        """
        Args:
            optimizer: Otimizador PyTorch
            max_lr: Learning rate máxima após warmup
            warmup_epochs: Épocas de warmup
            total_epochs: Total de épocas de treino
            min_lr: LR mínima no final
            warmup_start_lr: LR inicial no warmup
        """
        self.max_lr = max_lr
        self.warmup_epochs = warmup_epochs
        self.total_epochs = total_epochs
        self.min_lr = min_lr
        self.warmup_start_lr = warmup_start_lr

        super().__init__(optimizer, last_epoch=-1)

    def get_lr(self):
        if self.last_epoch < self.warmup_epochs:
            # Linear warmup
            lr = self.warmup_start_lr + (
                (self.max_lr - self.warmup_start_lr) *
                self.last_epoch / self.warmup_epochs
            )
        else:
            # Cosine decay
            progress = (self.last_epoch - self.warmup_epochs) / (
                self.total_epochs - self.warmup_epochs
            )
            lr = self.min_lr + (self.max_lr - self.min_lr) * 0.5 * (
                1 + math.cos(math.pi * progress)
            )

        return [lr for _ in self.base_lrs]


# Uso
optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=0.05)
scheduler = CosineAnnealingWarmupRestarts(
    optimizer,
    max_lr=3e-4,
    warmup_epochs=5,
    total_epochs=50,
    min_lr=1e-6,
)

for epoch in range(50):
    train_one_epoch(model, train_loader, optimizer)
    scheduler.step()
    print(f"Epoch {epoch}: LR = {scheduler.get_last_lr()[0]:.2e}")
```

### One Cycle Policy

Scheduler agressivo que funciona bem com poucos epochs:

```python
from torch.optim.lr_scheduler import OneCycleLR


def create_one_cycle_scheduler(
    optimizer: torch.optim.Optimizer,
    max_lr: float,
    epochs: int,
    steps_per_epoch: int,
    pct_start: float = 0.3,
    div_factor: float = 25.0,
    final_div_factor: float = 1e4,
) -> OneCycleLR:
    """
    Cria scheduler OneCycle.

    Args:
        optimizer: Otimizador
        max_lr: LR máxima
        epochs: Total de épocas
        steps_per_epoch: Iterações por época
        pct_start: % do ciclo para warmup (default 30%)
        div_factor: max_lr / (div_factor) = lr_inicial
        final_div_factor: LR final = lr_inicial / final_div_factor
    """
    return OneCycleLR(
        optimizer,
        max_lr=max_lr,
        epochs=epochs,
        steps_per_epoch=steps_per_epoch,
        pct_start=pct_start,
        div_factor=div_factor,
        final_div_factor=final_div_factor,
        anneal_strategy='cos',
    )


# Uso - atualiza a cada batch!
scheduler = create_one_cycle_scheduler(
    optimizer,
    max_lr=3e-4,
    epochs=30,
    steps_per_epoch=len(train_loader),
)

for epoch in range(30):
    for batch in train_loader:
        loss = train_step(model, batch, optimizer)
        scheduler.step()  # Chamado a cada batch!
```

### Warmup Factory

```python
from typing import Literal


def create_scheduler(
    optimizer: torch.optim.Optimizer,
    scheduler_type: Literal["cosine_warmup", "one_cycle", "step", "plateau"],
    epochs: int,
    steps_per_epoch: int = 1,
    warmup_epochs: int = 5,
    max_lr: float = 3e-4,
    min_lr: float = 1e-6,
    **kwargs,
) -> torch.optim.lr_scheduler._LRScheduler:
    """Factory para criar schedulers."""

    if scheduler_type == "cosine_warmup":
        return CosineAnnealingWarmupRestarts(
            optimizer,
            max_lr=max_lr,
            warmup_epochs=warmup_epochs,
            total_epochs=epochs,
            min_lr=min_lr,
        )

    elif scheduler_type == "one_cycle":
        return OneCycleLR(
            optimizer,
            max_lr=max_lr,
            epochs=epochs,
            steps_per_epoch=steps_per_epoch,
            pct_start=warmup_epochs / epochs,
            anneal_strategy='cos',
        )

    elif scheduler_type == "step":
        return torch.optim.lr_scheduler.StepLR(
            optimizer,
            step_size=kwargs.get("step_size", epochs // 3),
            gamma=kwargs.get("gamma", 0.1),
        )

    elif scheduler_type == "plateau":
        return torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer,
            mode="min",
            factor=kwargs.get("factor", 0.1),
            patience=kwargs.get("patience", 10),
        )

    raise ValueError(f"Scheduler não suportado: {scheduler_type}")
```

### Comparativo de Schedulers

| Scheduler | Uso Recomendado | Warmup | Configuração |
|-----------|-----------------|--------|--------------|
| **CosineWarmup** | Geral, mais épocas | ✅ | Simples |
| **OneCycle** | Poucos epochs, agressivo | ✅ | Por batch |
| StepLR | Baseline antigo | ❌ | step_size |
| ReduceOnPlateau | Fine-tuning | ❌ | patience |

---

## Checklist de Qualidade

- [ ] Invariante A: `optimizer_steps = ceil(N/K)` testado
- [ ] Invariante B: Ordem AMP correta
- [ ] Invariante C: `zero_grad(set_to_none=True)` usado
- [ ] Invariante D: Clip no momento do step
- [ ] Artefatos em formato padronizado (CalibArtifact v1)
- [ ] SWA com BN update quando aplicável
- [ ] Logs de observabilidade para eventos de flush
- [ ] Testes cobrindo edge cases de acumulação
- [ ] Complexidade ciclomática ≤ 10 por função
