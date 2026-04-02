---
name: deep-performance-tuning
description: Técnicas avançadas de otimização de performance em múltiplas camadas
  para modelos de classificação de imagens médicas
metadata:
  version: 1.0
---

# 🚀 Deep Model Performance Tuning

Skill para otimização profunda de modelos de classificação de imagens médicas, cobrindo desde hardware até algoritmos de treinamento.

---

## Arquitetura de Camadas de Performance

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CAMADAS DE OTIMIZAÇÃO DE PERFORMANCE                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ CAMADA 6: ENSEMBLE & CALIBRAÇÃO                                        │ │
│  │ • Temperature Scaling • Platt Scaling • Model Fusion                   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    ▲                                         │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ CAMADA 5: REGULARIZAÇÃO AVANÇADA                                       │ │
│  │ • Label Smoothing • MixUp/CutMix • SWA • EMA                          │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    ▲                                         │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ CAMADA 4: LOSS ENGINEERING                                             │ │
│  │ • Focal Loss • Asymmetric Loss • Class-Balanced • Poly Loss           │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    ▲                                         │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ CAMADA 3: OTIMIZAÇÃO DE GRADIENTES                                     │ │
│  │ • SAM • LION • AdamW • Gradient Accumulation • Gradient Clipping      │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    ▲                                         │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ CAMADA 2: DATA PIPELINE                                                │ │
│  │ • Progressive Resizing • Smart Augmentation • Prefetching             │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    ▲                                         │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ CAMADA 1: HARDWARE & COMPILAÇÃO                                        │ │
│  │ • torch.compile • Channels Last • AMP • CUDA Graphs                   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Camada 1: Hardware & Compilação

### 1.1 torch.compile() com TensorRT

```python
import torch

def optimize_model_for_inference(model: nn.Module) -> nn.Module:
    """Otimiza modelo para inferência com torch.compile."""

    # Modo max-autotune busca os melhores kernels CUDA
    model = torch.compile(
        model,
        mode="max-autotune",
        fullgraph=True,
        dynamic=False,  # Shapes fixos para melhor otimização
    )

    return model


def optimize_model_for_training(model: nn.Module) -> nn.Module:
    """Otimiza modelo para treinamento."""

    # reduce-overhead minimiza latência de dispatch
    model = torch.compile(
        model,
        mode="reduce-overhead",
        fullgraph=False,  # Permite fallback para operações não suportadas
    )

    return model
```

### 1.2 Channels Last Memory Format

```python
def enable_channels_last(model: nn.Module) -> nn.Module:
    """
    Converte modelo para memory format NHWC.

    Benefício: ~10-30% speedup em GPUs NVIDIA devido ao Tensor Cores.
    """
    model = model.to(memory_format=torch.channels_last)
    return model


def process_batch_channels_last(images: torch.Tensor) -> torch.Tensor:
    """Converte batch para channels_last."""
    return images.to(memory_format=torch.channels_last)
```

### 1.3 Automatic Mixed Precision (AMP) Correto

```python
from torch.cuda.amp import autocast, GradScaler


class AMPTrainer:
    """Trainer com AMP implementado corretamente."""

    def __init__(self, model: nn.Module, optimizer: torch.optim.Optimizer):
        self.model = model
        self.optimizer = optimizer
        self.scaler = GradScaler()

    def train_step(self, images: torch.Tensor, targets: torch.Tensor) -> float:
        """
        Ordem CORRETA para AMP:
        1. autocast forward
        2. scaler.scale(loss).backward()
        3. scaler.unscale_(optimizer)
        4. clip_grad_norm
        5. scaler.step(optimizer)
        6. scaler.update()
        7. zero_grad(set_to_none=True)
        """
        self.optimizer.zero_grad(set_to_none=True)

        # 1. Forward com autocast
        with autocast(dtype=torch.float16):
            logits = self.model(images)
            loss = self.criterion(logits, targets)

        # 2. Backward com scaling
        self.scaler.scale(loss).backward()

        # 3. Unscale antes do clipping
        self.scaler.unscale_(self.optimizer)

        # 4. Gradient clipping
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)

        # 5-6. Step e update
        self.scaler.step(self.optimizer)
        self.scaler.update()

        return loss.item()
```

### 1.4 CUDA Graphs para Latência Ultra-Baixa

```python
def capture_cuda_graph(model: nn.Module, sample_input: torch.Tensor):
    """
    Captura CUDA Graph para inferência determinística.

    Benefício: ~2-3x speedup em inferência de batch único.
    Limitação: Shapes devem ser fixos.
    """
    # Warmup
    for _ in range(3):
        _ = model(sample_input)

    # Capturar graph
    g = torch.cuda.CUDAGraph()
    with torch.cuda.graph(g):
        output = model(sample_input)

    def run_graph(x: torch.Tensor) -> torch.Tensor:
        sample_input.copy_(x)
        g.replay()
        return output.clone()

    return run_graph
```

---

## Camada 2: Data Pipeline

### 2.1 Progressive Resizing

```python
class ProgressiveResizer:
    """
    Treina com resolução crescente para convergência mais rápida.

    Benefícios:
    1. Épocas iniciais 4x mais rápidas
    2. Regularização implícita
    3. Melhor generalização
    """

    def __init__(
        self,
        initial_size: int = 224,
        final_size: int = 448,
        warmup_epochs: int = 5,
        total_epochs: int = 50,
    ):
        self.initial_size = initial_size
        self.final_size = final_size
        self.warmup_epochs = warmup_epochs
        self.total_epochs = total_epochs

    def get_size(self, epoch: int) -> int:
        if epoch < self.warmup_epochs:
            return self.initial_size

        # Linear interpolation
        progress = (epoch - self.warmup_epochs) / (self.total_epochs - self.warmup_epochs)
        size = int(self.initial_size + (self.final_size - self.initial_size) * progress)

        # Arredondar para múltiplo de 32 (eficiência de GPU)
        return (size // 32) * 32
```

### 2.2 Smart Augmentation Pipeline

```python
import albumentations as A
from albumentations.pytorch import ToTensorV2


def create_specialist_augmentation(group: str) -> A.Compose:
    """Cria pipeline de augmentation específico para cada especialista."""

    base_transforms = [
        A.Resize(448, 448),
        A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ]

    group_transforms = {
        "group_a_opacities": [
            A.CLAHE(clip_limit=2.0, p=0.7),
            A.Sharpen(alpha=(0.2, 0.5), p=0.3),
            A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.5),
            A.GridDropout(ratio=0.3, p=0.4),
        ],
        "group_b_structural": [
            A.ShiftScaleRotate(shift_limit=0.1, scale_limit=0.2, rotate_limit=15, p=0.7),
            A.ElasticTransform(alpha=100, sigma=10, p=0.3),
            A.OpticalDistortion(distort_limit=0.1, p=0.3),
        ],
        "group_c_nodules": [
            A.RandomResizedCrop(448, 448, scale=(0.8, 1.0), p=0.7),
            A.CoarseDropout(max_holes=8, max_height=32, max_width=32, p=0.5),
            A.RandomGamma(gamma_limit=(80, 120), p=0.4),
            A.GaussNoise(var_limit=(10, 30), p=0.3),
        ],
    }

    return A.Compose(
        base_transforms + group_transforms.get(group, []) + [ToTensorV2()]
    )
```

### 2.3 Async Data Prefetching

```python
class CUDAPrefetcher:
    """
    Prefetch data para GPU em stream separado.

    Benefício: Elimina tempo de transferência CPU→GPU.
    """

    def __init__(self, loader, device):
        self.loader = iter(loader)
        self.device = device
        self.stream = torch.cuda.Stream()
        self.preload()

    def preload(self):
        try:
            self.next_images, self.next_targets = next(self.loader)
        except StopIteration:
            self.next_images = None
            self.next_targets = None
            return

        with torch.cuda.stream(self.stream):
            self.next_images = self.next_images.to(self.device, non_blocking=True)
            self.next_targets = self.next_targets.to(self.device, non_blocking=True)

    def next(self):
        torch.cuda.current_stream().wait_stream(self.stream)
        images = self.next_images
        targets = self.next_targets
        self.preload()
        return images, targets
```

---

## Camada 3: Otimização de Gradientes

### 3.1 SAM (Sharpness-Aware Minimization)

```python
class SAM(torch.optim.Optimizer):
    """
    Sharpness-Aware Minimization.

    Busca mínimos "planos" para melhor generalização.
    Custo: 2x forward-backward por step.
    """

    def __init__(self, params, base_optimizer, rho=0.05):
        defaults = dict(rho=rho)
        super().__init__(params, defaults)
        self.base_optimizer = base_optimizer
        self.param_groups = self.base_optimizer.param_groups

    @torch.no_grad()
    def first_step(self, zero_grad=False):
        """Perturbação para encontrar direção de maior perda."""
        grad_norm = self._grad_norm()

        for group in self.param_groups:
            scale = group["rho"] / (grad_norm + 1e-12)
            for p in group["params"]:
                if p.grad is None:
                    continue
                e_w = p.grad * scale
                p.add_(e_w)  # Perturbar pesos
                self.state[p]["e_w"] = e_w

        if zero_grad:
            self.zero_grad()

    @torch.no_grad()
    def second_step(self, zero_grad=False):
        """Step real após remover perturbação."""
        for group in self.param_groups:
            for p in group["params"]:
                if p.grad is None:
                    continue
                p.sub_(self.state[p]["e_w"])  # Remover perturbação

        self.base_optimizer.step()

        if zero_grad:
            self.zero_grad()

    def _grad_norm(self):
        norm = torch.norm(
            torch.stack([
                p.grad.norm(p=2)
                for group in self.param_groups
                for p in group["params"]
                if p.grad is not None
            ]),
            p=2
        )
        return norm
```

### 3.2 LION Optimizer

```python
class Lion(torch.optim.Optimizer):
    """
    LION: Evolved Sign Momentum.

    Benefícios vs AdamW:
    - 10x menos memória (não guarda variance)
    - Melhor generalização em tasks visuais
    - Requer 3x menor learning rate
    """

    def __init__(self, params, lr=1e-4, betas=(0.9, 0.99), weight_decay=0.0):
        defaults = dict(lr=lr, betas=betas, weight_decay=weight_decay)
        super().__init__(params, defaults)

    @torch.no_grad()
    def step(self):
        for group in self.param_groups:
            for p in group["params"]:
                if p.grad is None:
                    continue

                grad = p.grad
                state = self.state[p]

                # Inicializar momentum
                if len(state) == 0:
                    state["exp_avg"] = torch.zeros_like(p)

                exp_avg = state["exp_avg"]
                beta1, beta2 = group["betas"]

                # Weight decay
                if group["weight_decay"] != 0:
                    p.mul_(1 - group["lr"] * group["weight_decay"])

                # Update: sign(interpolation between gradient and momentum)
                update = exp_avg * beta1 + grad * (1 - beta1)
                p.add_(torch.sign(update), alpha=-group["lr"])

                # Update momentum
                exp_avg.mul_(beta2).add_(grad, alpha=1 - beta2)
```

### 3.3 Gradient Accumulation com Sync Correto

```python
class GradientAccumulator:
    """
    Acumulação de gradientes com sync correto para DDP.
    """

    def __init__(self, accum_steps: int, model: nn.Module):
        self.accum_steps = accum_steps
        self.model = model
        self.step_count = 0

    def backward(self, loss: torch.Tensor):
        """
        Backward com normalização e sync correto.

        Para DDP: desabilitar sync nos passos intermediários.
        """
        normalized_loss = loss / self.accum_steps

        # Para DDP: no_sync() nos passos intermediários
        if hasattr(self.model, 'no_sync'):
            if self.step_count < self.accum_steps - 1:
                with self.model.no_sync():
                    normalized_loss.backward()
            else:
                normalized_loss.backward()
        else:
            normalized_loss.backward()

        self.step_count += 1

    def should_step(self) -> bool:
        return self.step_count >= self.accum_steps

    def reset(self):
        self.step_count = 0
```

---

## Camada 4: Loss Engineering

### 4.1 Poly Loss (Melhora sobre CE)

```python
class PolyLoss(nn.Module):
    """
    Polynomial Loss: generalização de Cross-Entropy.

    L_poly = L_ce + epsilon * (1 - p_t)^n

    Melhor que CE para classes desbalanceadas.
    """

    def __init__(self, epsilon: float = 1.0, n: int = 1):
        super().__init__()
        self.epsilon = epsilon
        self.n = n

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        p = torch.sigmoid(logits)
        pt = p * targets + (1 - p) * (1 - targets)

        ce_loss = F.binary_cross_entropy_with_logits(logits, targets, reduction='none')
        poly_term = self.epsilon * (1 - pt) ** self.n

        return (ce_loss + poly_term).mean()
```

### 4.2 Distribution-Balanced Loss

```python
class DistributionBalancedLoss(nn.Module):
    """
    Rebalanceia loss baseado em distribuição de classes.

    Ideal para multi-label com alta co-ocorrência.
    """

    def __init__(
        self,
        class_freq: torch.Tensor,
        rebalance_weight: float = 0.5,
    ):
        super().__init__()
        # Peso inversamente proporcional à frequência
        weights = 1.0 / (class_freq ** rebalance_weight)
        weights = weights / weights.sum() * len(weights)
        self.register_buffer("weights", weights)

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        loss = F.binary_cross_entropy_with_logits(logits, targets, reduction='none')
        weighted_loss = loss * self.weights
        return weighted_loss.mean()
```

---

## Camada 5: Regularização Avançada

### 5.1 Exponential Moving Average (EMA)

```python
class EMAModel:
    """
    Mantém média móvel exponencial dos pesos.

    Benefício: Modelo mais suave, melhor para avaliação.
    """

    def __init__(self, model: nn.Module, decay: float = 0.9999):
        self.model = model
        self.decay = decay
        self.shadow = {}
        self.backup = {}

        for name, param in model.named_parameters():
            if param.requires_grad:
                self.shadow[name] = param.data.clone()

    @torch.no_grad()
    def update(self):
        for name, param in self.model.named_parameters():
            if param.requires_grad:
                self.shadow[name] = (
                    self.decay * self.shadow[name] +
                    (1 - self.decay) * param.data
                )

    def apply_shadow(self):
        """Aplica pesos EMA para avaliação."""
        for name, param in self.model.named_parameters():
            if param.requires_grad:
                self.backup[name] = param.data.clone()
                param.data = self.shadow[name]

    def restore(self):
        """Restaura pesos originais após avaliação."""
        for name, param in self.model.named_parameters():
            if param.requires_grad:
                param.data = self.backup[name]
```

### 5.2 MixUp + CutMix Combinados

```python
class MixUpCutMix:
    """
    Combina MixUp e CutMix com probabilidade.

    MixUp: Interpola imagens e labels
    CutMix: Corta e cola patches entre imagens
    """

    def __init__(
        self,
        mixup_alpha: float = 0.2,
        cutmix_alpha: float = 1.0,
        mixup_prob: float = 0.5,
        cutmix_prob: float = 0.5,
    ):
        self.mixup_alpha = mixup_alpha
        self.cutmix_alpha = cutmix_alpha
        self.mixup_prob = mixup_prob
        self.cutmix_prob = cutmix_prob

    def __call__(
        self,
        images: torch.Tensor,
        targets: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, float]:
        """Retorna: (images_mixed, targets, targets_shuffled, lam)"""

        r = random.random()

        if r < self.cutmix_prob:
            return self._cutmix(images, targets)
        elif r < self.cutmix_prob + self.mixup_prob:
            return self._mixup(images, targets)
        else:
            return images, targets, targets, 1.0

    def _mixup(self, images, targets):
        lam = np.random.beta(self.mixup_alpha, self.mixup_alpha)
        indices = torch.randperm(images.size(0))

        mixed = lam * images + (1 - lam) * images[indices]
        return mixed, targets, targets[indices], lam

    def _cutmix(self, images, targets):
        lam = np.random.beta(self.cutmix_alpha, self.cutmix_alpha)
        indices = torch.randperm(images.size(0))

        # Calcular bounding box
        W, H = images.shape[-2:]
        cut_ratio = np.sqrt(1 - lam)
        cut_w = int(W * cut_ratio)
        cut_h = int(H * cut_ratio)

        cx = np.random.randint(W)
        cy = np.random.randint(H)

        x1 = np.clip(cx - cut_w // 2, 0, W)
        x2 = np.clip(cx + cut_w // 2, 0, W)
        y1 = np.clip(cy - cut_h // 2, 0, H)
        y2 = np.clip(cy + cut_h // 2, 0, H)

        images[:, :, x1:x2, y1:y2] = images[indices, :, x1:x2, y1:y2]

        # Ajustar lambda pelo tamanho real do corte
        lam = 1 - ((x2 - x1) * (y2 - y1)) / (W * H)

        return images, targets, targets[indices], lam
```

---

## Camada 6: Ensemble & Calibração

### 6.1 Multi-Exit Calibration

```python
class MultiExitCalibrator:
    """
    Calibra cada saída do ensemble separadamente.
    """

    def __init__(self, num_classes: int):
        self.temperatures = torch.ones(num_classes)

    def fit(
        self,
        logits: torch.Tensor,
        targets: torch.Tensor,
    ):
        """Fit temperature per class."""
        for c in range(logits.shape[1]):
            class_logits = logits[:, c]
            class_targets = targets[:, c]

            best_temp = 1.0
            best_ece = float('inf')

            for temp in np.linspace(0.5, 3.0, 50):
                probs = torch.sigmoid(class_logits / temp)
                ece = self._compute_ece(probs, class_targets)
                if ece < best_ece:
                    best_ece = ece
                    best_temp = temp

            self.temperatures[c] = best_temp

    def calibrate(self, logits: torch.Tensor) -> torch.Tensor:
        return logits / self.temperatures.to(logits.device)
```

### 6.2 Specialist Fusion Strategies

```python
class SpecialistFusion:
    """
    Estratégias para fundir predições de especialistas.
    """

    @staticmethod
    def hard_routing(
        predictions: Dict[str, torch.Tensor],
        label_to_specialist: Dict[str, str],
    ) -> torch.Tensor:
        """Usa apenas o especialista designado para cada classe."""
        output = torch.zeros(14)
        for label, specialist in label_to_specialist.items():
            idx = ALL_LABELS.index(label)
            output[idx] = predictions[specialist][idx]
        return output

    @staticmethod
    def soft_routing(
        predictions: Dict[str, torch.Tensor],
        confidences: Dict[str, torch.Tensor],
    ) -> torch.Tensor:
        """Pondera por confiança do especialista."""
        weighted_sum = torch.zeros(14)
        weight_sum = torch.zeros(14)

        for specialist, pred in predictions.items():
            conf = confidences[specialist]
            weighted_sum += pred * conf
            weight_sum += conf

        return weighted_sum / (weight_sum + 1e-8)

    @staticmethod
    def learned_routing(
        predictions: Dict[str, torch.Tensor],
        gating_network: nn.Module,
        image_features: torch.Tensor,
    ) -> torch.Tensor:
        """Usa rede de gating aprendida."""
        gates = gating_network(image_features)  # (batch, num_specialists)

        # Stack predictions: (batch, num_specialists, num_classes)
        stacked = torch.stack(list(predictions.values()), dim=1)

        # Weighted combination
        gates = gates.unsqueeze(-1)  # (batch, num_specialists, 1)
        return (stacked * gates).sum(dim=1)
```

---

## Checklist de Implementação

### Hardware & Compilação
- [ ] torch.compile habilitado
- [ ] Channels Last ativado
- [ ] AMP com ordem correta
- [ ] Profiling com torch.profiler

### Data Pipeline
- [ ] Progressive resizing configurado
- [ ] Augmentation por especialista
- [ ] Prefetching assíncrono
- [ ] num_workers otimizado

### Otimização
- [ ] SAM ou LION avaliado
- [ ] Gradient accumulation correto
- [ ] Learning rate scheduler com warmup
- [ ] Gradient clipping ativo

### Loss & Regularização
- [ ] Focal ou Asymmetric Loss
- [ ] Class weights calculados
- [ ] Label smoothing habilitado
- [ ] MixUp/CutMix configurados
- [ ] EMA para avaliação

### Calibração
- [ ] Temperature Scaling aplicado
- [ ] ECE monitorado
- [ ] Calibração por classe se necessário

---

*Versão: 1.0*
*Última atualização: 2026-02-03*
