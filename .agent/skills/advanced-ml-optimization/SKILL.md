---
name: advanced-ml-optimization
description: Técnicas avançadas de otimização para LLMs, PEFT, AutoML e reconhecimento nanométrico
---

# Advanced ML Optimization Skill

Técnicas de ponta para treinamento de modelos de larga escala, AutoML avançado, e processamento de alta resolução.

---

## 1. PEFT de Próxima Geração

### DoRA (Weight-Decomposed Low-Rank Adaptation)

Supera LoRA tradicional ao decompor pesos em **magnitude** e **direção**:

```python
from peft import DoraConfig, get_peft_model

config = DoraConfig(
    r=16,                    # rank
    lora_alpha=32,           # scaling
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.05,
    use_dora=True,           # Decomposição magnitude/direção
)
model = get_peft_model(base_model, config)
```

**Vantagens:**
- Aprende padrões similar ao Full Fine-Tuning
- ~10% menos memória que LoRA padrão
- Melhor generalização em tarefas downstream

### rsLoRA (Rank-Stabilized LoRA)

Utiliza fator de escala `1/√r` para estabilizar gradientes em alto rank:

```python
config = LoraConfig(
    r=256,                   # Alto rank
    lora_alpha=256,
    use_rslora=True,         # Fator de escala estabilizador
)
```

**Benefício:** Evita colapso de gradiente em r > 64.

### QLoRA (Quantized LoRA)

Treina modelos de 70B params em GPUs consumer:

```python
from transformers import BitsAndBytesConfig

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",      # NormalFloat 4-bit
    bnb_4bit_use_double_quant=True, # Quantização dupla
    bnb_4bit_compute_dtype=torch.bfloat16,
)

model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-70b",
    quantization_config=bnb_config,
    device_map="auto",
)
```

**Memória:** 70B → ~35GB (cabe em 2x RTX 3090).

---

## 2. Compilação e Aceleração de Hardware

### JAX + XLA Compilation

```python
import jax
import jax.numpy as jnp

@jax.jit  # XLA compilation
def train_step(params, batch):
    def loss_fn(p):
        logits = model.apply(p, batch['input'])
        return cross_entropy(logits, batch['target'])

    loss, grads = jax.value_and_grad(loss_fn)(params)
    return loss, grads

# Operações fundidas = menos transferências de memória
```

**Vantagens:**
- Fusão automática de operações
- Vetorização para TPUs/GPUs
- 2-5x mais rápido que PyTorch eager

### torch.compile() Modos

```python
# Modo max-autotune: busca exaustiva de kernels ótimos
model = torch.compile(model, mode="max-autotune")

# Modo reduce-overhead: minimiza latência de dispatch
model = torch.compile(model, mode="reduce-overhead", fullgraph=True)
```

---

## 3. Otimização de Segunda Ordem

### SGLD (Stochastic Gradient Langevin Dynamics)

Escapa de saddle points via ruído Browniano:

```python
class SGLDOptimizer:
    def __init__(self, params, lr=1e-4, noise_scale=0.01):
        self.params = list(params)
        self.lr = lr
        self.noise_scale = noise_scale

    def step(self, grads):
        for p, g in zip(self.params, grads):
            noise = torch.randn_like(p) * self.noise_scale
            p.data -= self.lr * g + np.sqrt(2 * self.lr) * noise
```

**Uso:** Paisagens não-convexas com muitos mínimos locais.

### SAM (Sharpness-Aware Minimization)

Busca mínimos "planos" para melhor generalização:

```python
from sam import SAM

base_optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
optimizer = SAM(model.parameters(), base_optimizer, rho=0.05)

# Training step
loss = criterion(model(x), y)
loss.backward()
optimizer.first_step(zero_grad=True)

criterion(model(x), y).backward()
optimizer.second_step(zero_grad=True)
```

---

## 4. AutoML Avançado

### Platt Scaling (Calibração)

```python
from sklearn.calibration import CalibratedClassifierCV

# Wrapper para PyTorch
calibrator = CalibratedClassifierCV(
    base_estimator=None,
    method='sigmoid',  # Platt Scaling
    cv='prefit',
)

# Treina em validation logits
calibrator.fit(val_logits.numpy(), val_labels.numpy())
calibrated_probs = calibrator.predict_proba(test_logits.numpy())
```

**Garantia:** Confiança 70% → 70% de acerto real.

### Temperature Scaling (Implementado no Projeto)

```python
from src.utils.calibration import TemperatureScaling

ts = TemperatureScaling()
ts.fit(val_loader, model, device)

# Aplicar escala
calibrated_logits = logits / ts.temperature
```

### Learned Optimizers

Redes neurais que calculam regras de atualização:

```python
# Conceito: otimizador como meta-modelo
class LearnedOptimizer(nn.Module):
    def __init__(self):
        self.lstm = nn.LSTM(input_size=2, hidden_size=20)
        self.output = nn.Linear(20, 1)

    def forward(self, grad, prev_grad):
        # Entrada: gradiente atual e anterior
        x = torch.stack([grad, prev_grad], dim=-1)
        h, _ = self.lstm(x)
        return self.output(h)  # Fator de atualização
```

### Hyperband + NAS

```python
from ray import tune
from ray.tune.schedulers import HyperBandScheduler

scheduler = HyperBandScheduler(
    max_t=100,           # Max epochs
    reduction_factor=3,  # Descarta 2/3 a cada round
    stop_last_trials=True,
)

tune.run(
    train_fn,
    config={
        "lr": tune.loguniform(1e-5, 1e-2),
        "layers": tune.choice([2, 4, 6, 8]),
        "hidden": tune.choice([128, 256, 512]),
    },
    scheduler=scheduler,
    num_samples=50,
)
```

---

## 5. Processamento de Alta Resolução

### Latent Diffusion (Super-Resolução)

```python
from diffusers import StableDiffusionUpscalePipeline

pipe = StableDiffusionUpscalePipeline.from_pretrained(
    "stabilityai/stable-diffusion-x4-upscaler"
)

# 256px → 1024px
upscaled = pipe(prompt="enhance", image=low_res_img).images[0]
```

### Vision Transformers (ViT)

```python
from transformers import ViTForImageClassification

model = ViTForImageClassification.from_pretrained(
    "google/vit-base-patch16-224",  # Patches 16x16
    num_labels=14,
)

# Patches capturam dependências globais
# Ideal para: imagens médicas, nanométricas
```

**Vantagens:**
- Relações de longo alcance entre patches
- Atenção multi-cabeça sobre posições distantes
- Melhor que CNNs em imagens com padrões dispersos

### Deep Galerkin Method (PDEs)

Aproximações mesh-free para simulações físicas:

```python
class DGMNet(nn.Module):
    """Deep Galerkin Method para PDEs."""

    def __init__(self, layers=[50, 50, 50]):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(3, layers[0]),  # (x, y, t)
            *[nn.Sequential(nn.Linear(l, l), nn.Tanh())
              for l in layers],
            nn.Linear(layers[-1], 1),
        )

    def forward(self, x, y, t):
        return self.network(torch.cat([x, y, t], dim=-1))

# Loss: residual da PDE + condições de contorno
def physics_loss(u, x, y, t):
    u_t = torch.autograd.grad(u, t, create_graph=True)[0]
    u_xx = ...  # Segunda derivada
    return (u_t - alpha * u_xx).pow(2).mean()
```

---

## 6. Graph Neural Networks (Molecular)

### GraphRAG para Dados Moleculares

```python
from torch_geometric.nn import GCNConv, global_mean_pool

class MolecularGNN(nn.Module):
    def __init__(self, in_features, hidden, out_features):
        super().__init__()
        self.conv1 = GCNConv(in_features, hidden)
        self.conv2 = GCNConv(hidden, hidden)
        self.fc = nn.Linear(hidden, out_features)

    def forward(self, x, edge_index, batch):
        x = F.relu(self.conv1(x, edge_index))
        x = F.relu(self.conv2(x, edge_index))
        x = global_mean_pool(x, batch)  # Agregação molecular
        return self.fc(x)

# Uso: QM9 dataset, propriedades termodinâmicas
```

---

## 7. Edge Detection de Alta Precisão

### Modified Roberts Cross (Nanométrico)

```python
import cv2
import numpy as np

def roberts_enhanced(image: np.ndarray, threshold: float = 0.1) -> np.ndarray:
    """Roberts Cross modificado para precisão nanométrica."""
    # Kernels Roberts padrão
    kx = np.array([[1, 0], [0, -1]], dtype=np.float32)
    ky = np.array([[0, 1], [-1, 0]], dtype=np.float32)

    # Aplicar com subpixel precision
    gx = cv2.filter2D(image.astype(np.float64), -1, kx)
    gy = cv2.filter2D(image.astype(np.float64), -1, ky)

    # Magnitude com precisão float64
    magnitude = np.sqrt(gx**2 + gy**2)

    # Non-maximum suppression
    direction = np.arctan2(gy, gx)
    nms = non_max_suppression(magnitude, direction)

    return (nms > threshold).astype(np.uint8) * 255
```

---

## 8. Loss Functions para Class Imbalance

### Focal Loss

Reduz peso de exemplos fáceis, focando nos difíceis:

```python
import torch
import torch.nn as nn
import torch.nn.functional as F

class FocalLoss(nn.Module):
    """Focal Loss para classificação multi-label."""

    def __init__(
        self,
        alpha: float = 0.25,
        gamma: float = 2.0,
        reduction: str = "mean",
    ):
        """
        Args:
            alpha: Peso para classe positiva (0.25 = mais peso para positivos raros)
            gamma: Fator de foco (2.0 = foco forte em exemplos difíceis)
            reduction: 'mean', 'sum', or 'none'
        """
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.reduction = reduction

    def forward(
        self,
        inputs: torch.Tensor,
        targets: torch.Tensor,
    ) -> torch.Tensor:
        """
        Args:
            inputs: Logits (B, C)
            targets: Labels (B, C) para multi-label ou (B,) para single
        """
        p = torch.sigmoid(inputs)
        ce_loss = F.binary_cross_entropy_with_logits(
            inputs, targets, reduction="none"
        )

        # Focal term
        p_t = p * targets + (1 - p) * (1 - targets)
        focal_weight = (1 - p_t) ** self.gamma

        # Alpha weighting
        alpha_t = self.alpha * targets + (1 - self.alpha) * (1 - targets)

        loss = alpha_t * focal_weight * ce_loss

        if self.reduction == "mean":
            return loss.mean()
        elif self.reduction == "sum":
            return loss.sum()
        return loss
```

**Configuração Recomendada:**
- `gamma=2.0`: Padrão para a maioria dos casos
- `gamma=3.0-4.0`: Para imbalance extremo
- `alpha=0.25`: Padrão
- `alpha=0.75`: Se positivos muito raros

### Asymmetric Loss

Trata positivos e negativos de forma assimétrica, ideal para multi-label:

```python
class AsymmetricLoss(nn.Module):
    """Asymmetric Loss para multi-label classification."""

    def __init__(
        self,
        gamma_neg: float = 4.0,
        gamma_pos: float = 0.0,
        clip: float = 0.05,
        reduction: str = "mean",
    ):
        """
        Args:
            gamma_neg: Hard negative mining (maior = mais foco em FP)
            gamma_pos: Focal term para positivos (0 = sem foco)
            clip: Threshold mínimo para probabilidade (evita log(0))
            reduction: 'mean', 'sum', or 'none'
        """
        super().__init__()
        self.gamma_neg = gamma_neg
        self.gamma_pos = gamma_pos
        self.clip = clip
        self.reduction = reduction

    def forward(
        self,
        inputs: torch.Tensor,
        targets: torch.Tensor,
    ) -> torch.Tensor:
        """Aplica asymmetric loss."""
        # Sigmoid
        p = torch.sigmoid(inputs)

        # Clip para estabilidade numérica
        p_clip = (p + self.clip).clamp(max=1)

        # Termos positivos e negativos
        xs_pos = p
        xs_neg = 1 - p_clip

        # BCE básico
        los_pos = targets * torch.log(xs_pos.clamp(min=1e-8))
        los_neg = (1 - targets) * torch.log(xs_neg.clamp(min=1e-8))

        # Asymmetric focusing
        if self.gamma_neg > 0:
            neg_weight = (p_clip) ** self.gamma_neg
            los_neg = los_neg * neg_weight

        if self.gamma_pos > 0:
            pos_weight = (1 - p) ** self.gamma_pos
            los_pos = los_pos * pos_weight

        loss = -(los_pos + los_neg)

        if self.reduction == "mean":
            return loss.mean()
        elif self.reduction == "sum":
            return loss.sum()
        return loss


# Exemplo de uso
criterion = AsymmetricLoss(
    gamma_neg=4,   # Suprimir falsos positivos
    gamma_pos=0,   # Não modificar positivos
    clip=0.05,
)
```

**Configuração por Cenário:**

| Cenário | gamma_pos | gamma_neg | Efeito |
|---------|-----------|-----------|--------|
| Muitos FP | 0 | 4-6 | Suprimir negativos fáceis |
| Muitos FN | 1-2 | 2 | Balanceado |
| Extremo imbalance | 0 | 6-8 | Hard negative mining |

### Class-Balanced Loss

Repondera perdas por frequência de classe:

```python
class ClassBalancedLoss(nn.Module):
    """Loss ponderada por frequência de classe."""

    def __init__(
        self,
        samples_per_class: list[int],
        beta: float = 0.9999,
        loss_type: str = "focal",
    ):
        """
        Args:
            samples_per_class: Número de amostras por classe
            beta: Fator de suavização (0.9999 comum)
            loss_type: 'bce', 'focal', ou 'asymmetric'
        """
        super().__init__()

        # Calcular pesos efetivos
        effective_num = 1.0 - torch.pow(beta, torch.tensor(samples_per_class, dtype=torch.float))
        weights = (1.0 - beta) / effective_num
        weights = weights / weights.sum() * len(samples_per_class)

        self.register_buffer("weights", weights)
        self.loss_type = loss_type

        if loss_type == "focal":
            self.base_loss = FocalLoss(reduction="none")
        elif loss_type == "asymmetric":
            self.base_loss = AsymmetricLoss(reduction="none")
        else:
            self.base_loss = None

    def forward(
        self,
        inputs: torch.Tensor,
        targets: torch.Tensor,
    ) -> torch.Tensor:
        """Aplica class-balanced loss."""
        if self.base_loss:
            loss = self.base_loss(inputs, targets)
        else:
            loss = F.binary_cross_entropy_with_logits(
                inputs, targets, reduction="none"
            )

        # Ponderar por classe
        weighted_loss = loss * self.weights.unsqueeze(0)

        return weighted_loss.mean()


# Exemplo com frequências do NIH CXR
samples_per_class = [
    11559,  # Atelectasis
    2776,   # Cardiomegaly
    4667,   # Consolidation
    2303,   # Edema
    13317,  # Effusion
    2516,   # Emphysema
    1686,   # Fibrosis
    227,    # Hernia
    19894,  # Infiltration
    5782,   # Mass
    6331,   # Nodule
    3385,   # Pleural Thickening
    1431,   # Pneumonia
    5302,   # Pneumothorax
]

criterion = ClassBalancedLoss(
    samples_per_class=samples_per_class,
    beta=0.9999,
    loss_type="asymmetric",
)
```

### Label Smoothing

Combinável com qualquer loss para melhorar calibração:

```python
class LabelSmoothingBCE(nn.Module):
    """BCE com label smoothing."""

    def __init__(self, smoothing: float = 0.1):
        super().__init__()
        self.smoothing = smoothing

    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        # Suavizar labels: 0 -> eps, 1 -> 1-eps
        smooth_targets = targets * (1 - self.smoothing) + 0.5 * self.smoothing
        return F.binary_cross_entropy_with_logits(inputs, smooth_targets)
```

---

## Checklist de Implementação

- [ ] Integrar DoRA/rsLoRA no pipeline de fine-tuning
- [ ] Adicionar QLoRA para modelos > 7B params
- [ ] Implementar Temperature Scaling automático
- [ ] Adicionar Hyperband scheduler para hypertuning
- [ ] Suporte a ViT para classificação de patches
- [ ] GraphRAG para dados estruturados (se aplicável)

## Referências

- DoRA: https://arxiv.org/abs/2402.09353
- QLoRA: https://arxiv.org/abs/2305.14314
- SAM: https://arxiv.org/abs/2010.01412
- Deep Galerkin: https://arxiv.org/abs/1708.07469
