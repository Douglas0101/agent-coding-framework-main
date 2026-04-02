---
name: data-augmentation
description: Técnicas avançadas de data augmentation para imagens médicas (RandAugment, MixUp, CutMix, Progressive Resizing)
---

# Data Augmentation Skill

Técnicas avançadas de data augmentation para melhorar generalização e robustez de modelos de classificação de imagens médicas.

---

## Visão Geral

```
┌────────────────────────────────────────────────────────────────────┐
│                    DATA AUGMENTATION PIPELINE                       │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌─────────┐    ┌─────────────┐    ┌──────────┐    ┌───────────┐ │
│  │  Image  │───▶│ Geometric   │───▶│ Photom.  │───▶│ Advanced  │ │
│  │  Input  │    │ (Flip/Rot)  │    │(Color)   │    │(Mix/Cut)  │ │
│  └─────────┘    └─────────────┘    └──────────┘    └───────────┘ │
│                                                          │         │
│                                                          ▼         │
│                                                   ┌───────────┐   │
│                                                   │  Tensor   │   │
│                                                   │  Output   │   │
│                                                   └───────────┘   │
╚════════════════════════════════════════════════════════════════════╝
```

---

## 1. RandAugment

### 1.1 O que é RandAugment?

RandAugment é uma técnica de augmentation **automática** que seleciona aleatoriamente `N` transformações de um pool e aplica cada uma com magnitude `M`.

**Vantagens:**
- Não requer busca de hiperparâmetros (apenas N e M)
- Mais simples que AutoAugment
- Funciona bem em imagens médicas

### 1.2 Implementação

```python
from torchvision import transforms
from torchvision.transforms import autoaugment

class RandAugmentTransform:
    """RandAugment wrapper com configurações médicas."""

    def __init__(
        self,
        num_ops: int = 2,
        magnitude: int = 9,
        num_magnitude_bins: int = 31,
    ):
        """
        Args:
            num_ops: Número de operações por imagem (N)
            magnitude: Magnitude das transformações (M, 0-30)
            num_magnitude_bins: Bins para discretização
        """
        self.rand_augment = autoaugment.RandAugment(
            num_ops=num_ops,
            magnitude=magnitude,
            num_magnitude_bins=num_magnitude_bins,
        )

    def __call__(self, img):
        return self.rand_augment(img)


def get_train_transforms_with_randaugment(
    input_size: int = 224,
    rand_n: int = 2,
    rand_m: int = 9,
) -> transforms.Compose:
    """Pipeline de augmentation com RandAugment."""
    return transforms.Compose([
        transforms.Resize(int(input_size * 1.1)),
        transforms.RandomCrop(input_size),
        transforms.RandomHorizontalFlip(p=0.5),
        RandAugmentTransform(num_ops=rand_n, magnitude=rand_m),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
        ),
    ])
```

### 1.3 Configuração Recomendada

| Dataset | N (ops) | M (magnitude) |
|---------|---------|---------------|
| NIH ChestX-ray14 | 2 | 9 |
| RSNA Pneumonia | 2 | 7 |
| CheXpert | 3 | 9 |
| Geral (início) | 2 | 5 |

---

## 2. MixUp

### 2.1 O que é MixUp?

MixUp cria amostras sintéticas **interpolando** duas imagens e suas labels:

```
x_new = λ·x_i + (1-λ)·x_j
y_new = λ·y_i + (1-λ)·y_j
```

Onde λ ~ Beta(α, α).

**Vantagens:**
- Forte regularização
- Suaviza decision boundaries
- Melhora calibração

### 2.2 Implementação

```python
import torch
import numpy as np

class MixUp:
    """MixUp data augmentation."""

    def __init__(self, alpha: float = 0.2, p: float = 0.5):
        """
        Args:
            alpha: Parâmetro Beta distribution (menor = mais próximo do original)
            p: Probabilidade de aplicar MixUp
        """
        self.alpha = alpha
        self.p = p

    def __call__(
        self,
        images: torch.Tensor,
        targets: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, float]:
        """
        Aplica MixUp em um batch.

        Args:
            images: Tensor (B, C, H, W)
            targets: Tensor (B, num_classes) para multi-label ou (B,) para single

        Returns:
            mixed_images: Imagens misturadas
            mixed_targets: Labels misturadas
            lam: Lambda usado
        """
        if np.random.random() > self.p:
            return images, targets, 1.0

        batch_size = images.size(0)

        # Lambda da distribuição Beta
        lam = np.random.beta(self.alpha, self.alpha)

        # Índices para shuffle
        indices = torch.randperm(batch_size, device=images.device)

        # Mix
        mixed_images = lam * images + (1 - lam) * images[indices]
        mixed_targets = lam * targets + (1 - lam) * targets[indices]

        return mixed_images, mixed_targets, lam


# Uso no training loop
mixup = MixUp(alpha=0.2, p=0.5)

for images, targets in train_loader:
    images, targets = images.to(device), targets.to(device)

    # Aplicar MixUp
    mixed_images, mixed_targets, lam = mixup(images, targets.float())

    # Forward
    outputs = model(mixed_images)

    # Loss com targets misturados
    loss = criterion(outputs, mixed_targets)
```

### 2.3 Configuração Recomendada

| Alpha | Efeito | Uso |
|-------|--------|-----|
| 0.1 | Suave, quase original | Datasets pequenos |
| **0.2** | **Balanceado** | **Recomendado** |
| 0.4 | Agressivo | Datasets grandes |
| 1.0 | Uniforme (igual peso) | Experimental |

---

## 3. CutMix

### 3.1 O que é CutMix?

CutMix **recorta** uma região de uma imagem e **cola** em outra, ajustando as labels proporcionalmente à área:

```
x_new = M ⊙ x_i + (1-M) ⊙ x_j
y_new = λ·y_i + (1-λ)·y_j
```

Onde M é uma máscara binária e λ = 1 - (área_cortada / área_total).

**Vantagens:**
- Força o modelo a usar informação *local*
- Evita overfitting em features específicas
- Complementar ao MixUp

### 3.2 Implementação

```python
import torch
import numpy as np

class CutMix:
    """CutMix data augmentation."""

    def __init__(self, alpha: float = 1.0, p: float = 0.5):
        """
        Args:
            alpha: Parâmetro Beta para tamanho do corte
            p: Probabilidade de aplicar CutMix
        """
        self.alpha = alpha
        self.p = p

    def _rand_bbox(
        self,
        size: tuple,
        lam: float,
    ) -> tuple[int, int, int, int]:
        """Gera bounding box aleatório."""
        W, H = size[2], size[3]
        cut_rat = np.sqrt(1.0 - lam)
        cut_w = int(W * cut_rat)
        cut_h = int(H * cut_rat)

        # Centro aleatório
        cx = np.random.randint(W)
        cy = np.random.randint(H)

        # Bounds
        bbx1 = np.clip(cx - cut_w // 2, 0, W)
        bby1 = np.clip(cy - cut_h // 2, 0, H)
        bbx2 = np.clip(cx + cut_w // 2, 0, W)
        bby2 = np.clip(cy + cut_h // 2, 0, H)

        return bbx1, bby1, bbx2, bby2

    def __call__(
        self,
        images: torch.Tensor,
        targets: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, float]:
        """Aplica CutMix em um batch."""
        if np.random.random() > self.p:
            return images, targets, 1.0

        batch_size = images.size(0)

        # Lambda
        lam = np.random.beta(self.alpha, self.alpha)

        # Índices shuffle
        indices = torch.randperm(batch_size, device=images.device)

        # Gerar bbox
        bbx1, bby1, bbx2, bby2 = self._rand_bbox(images.size(), lam)

        # Aplicar corte
        mixed_images = images.clone()
        mixed_images[:, :, bbx1:bbx2, bby1:bby2] = images[indices, :, bbx1:bbx2, bby1:bby2]

        # Ajustar lambda pela área real cortada
        lam = 1 - ((bbx2 - bbx1) * (bby2 - bby1) / (images.size()[-1] * images.size()[-2]))

        # Mix targets
        mixed_targets = lam * targets + (1 - lam) * targets[indices]

        return mixed_images, mixed_targets, lam


# Uso combinado com MixUp
class MixUpCutMix:
    """Combina MixUp e CutMix."""

    def __init__(
        self,
        mixup_alpha: float = 0.2,
        cutmix_alpha: float = 1.0,
        mixup_prob: float = 0.5,
        cutmix_prob: float = 0.5,
    ):
        self.mixup = MixUp(mixup_alpha, mixup_prob)
        self.cutmix = CutMix(cutmix_alpha, cutmix_prob)
        self.cutmix_prob = cutmix_prob / (mixup_prob + cutmix_prob)

    def __call__(
        self,
        images: torch.Tensor,
        targets: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, float]:
        """Aplica MixUp ou CutMix aleatoriamente."""
        if np.random.random() < self.cutmix_prob:
            return self.cutmix(images, targets)
        return self.mixup(images, targets)
```

---

## 4. Progressive Resizing

### 4.1 O que é Progressive Resizing?

Treina o modelo começando com **imagens menores** e gradualmente **aumentando a resolução**:

```
Época 1-10:  224x224
Época 11-30: 320x320
Época 31-50: 384x384
```

**Vantagens:**
- Mais rápido inicialmente
- Regularização natural (data augmentation implícito)
- Permite convergir para maior resolução

### 4.2 Implementação

```python
from torch.utils.data import DataLoader
from typing import Callable

class ProgressiveResizing:
    """Handler para progressive resizing."""

    def __init__(
        self,
        sizes: list[int],
        epoch_milestones: list[int],
        transform_factory: Callable[[int], transforms.Compose],
    ):
        """
        Args:
            sizes: Lista de tamanhos [224, 320, 384]
            epoch_milestones: Épocas para mudar [0, 15, 35]
            transform_factory: Função que cria transform dado o size
        """
        assert len(sizes) == len(epoch_milestones)
        self.sizes = sizes
        self.milestones = epoch_milestones
        self.transform_factory = transform_factory
        self.current_size = sizes[0]

    def get_size_for_epoch(self, epoch: int) -> int:
        """Retorna o tamanho para a época atual."""
        for i, milestone in enumerate(self.milestones[::-1]):
            if epoch >= milestone:
                return self.sizes[len(self.sizes) - 1 - i]
        return self.sizes[0]

    def should_update(self, epoch: int) -> bool:
        """Verifica se precisa atualizar o tamanho."""
        new_size = self.get_size_for_epoch(epoch)
        if new_size != self.current_size:
            self.current_size = new_size
            return True
        return False

    def get_transform(self) -> transforms.Compose:
        """Retorna transform para o tamanho atual."""
        return self.transform_factory(self.current_size)


# Uso no training loop
def make_transform(size: int) -> transforms.Compose:
    return transforms.Compose([
        transforms.Resize(int(size * 1.1)),
        transforms.RandomCrop(size),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

progressive = ProgressiveResizing(
    sizes=[224, 320, 384],
    epoch_milestones=[0, 15, 35],
    transform_factory=make_transform,
)

for epoch in range(50):
    if progressive.should_update(epoch):
        print(f"Epoch {epoch}: Resizing to {progressive.current_size}")
        train_dataset.transform = progressive.get_transform()
        train_loader = DataLoader(train_dataset, batch_size=adjust_batch(progressive.current_size))

    train_one_epoch(model, train_loader)
```

### 4.3 Ajuste de Batch Size

| Resolução | Batch Size (8GB VRAM) | Batch Size (12GB) |
|-----------|----------------------|-------------------|
| 224x224 | 64 | 96 |
| 320x320 | 32 | 48 |
| 384x384 | 24 | 32 |
| 512x512 | 12 | 16 |

---

## 5. Augmentation para Imagens Médicas

### 5.1 Considerações Especiais

> ⚠️ **Cuidado**: Algumas augmentations podem criar artefatos não-realistas em imagens médicas.

| Augmentation | Seguro para CXR? | Observação |
|--------------|-----------------|------------|
| Horizontal Flip | ✅ Sim | Anatomia simétrica |
| Vertical Flip | ❌ Não | Inverte anatomia |
| Rotation ±15° | ✅ Sim | Leve rotação OK |
| Rotation >30° | ⚠️ Cuidado | Pode distorcer |
| Brightness | ✅ Sim | Simula exposure |
| Contrast | ✅ Sim | Comum em equipamentos |
| Cutout | ⚠️ Cuidado | Pode ocultar lesões |
| Elastic | ❌ Não | Distorce anatomia |

### 5.2 Pipeline Recomendado para CXR

```python
def get_cxr_train_transforms(input_size: int = 224) -> transforms.Compose:
    """Augmentation seguro para radiografias de tórax."""
    return transforms.Compose([
        # Geométrico (leve)
        transforms.Resize(int(input_size * 1.1)),
        transforms.RandomCrop(input_size),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(degrees=10),
        transforms.RandomAffine(
            degrees=0,
            translate=(0.05, 0.05),
            scale=(0.95, 1.05),
        ),

        # Fotométrico
        transforms.ColorJitter(
            brightness=0.1,
            contrast=0.1,
        ),

        # Para tensor
        transforms.ToTensor(),

        # Normalização ImageNet
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
        ),
    ])
```

---

## 6. Integração Completa

### 6.1 Factory de Augmentation

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class AugmentationConfig:
    """Configuração de augmentation."""

    input_size: int = 224

    # RandAugment
    use_randaugment: bool = True
    rand_n: int = 2
    rand_m: int = 9

    # MixUp/CutMix
    use_mixup: bool = True
    mixup_alpha: float = 0.2
    use_cutmix: bool = True
    cutmix_alpha: float = 1.0

    # Progressive Resizing
    use_progressive: bool = False
    progressive_sizes: list[int] = None
    progressive_milestones: list[int] = None

    # Modo
    mode: Literal["train", "val", "test"] = "train"


def build_transforms(config: AugmentationConfig) -> transforms.Compose:
    """Constrói pipeline de transforms baseado na config."""

    if config.mode in ("val", "test"):
        return transforms.Compose([
            transforms.Resize(int(config.input_size * 1.1)),
            transforms.CenterCrop(config.input_size),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])

    # Train mode
    transform_list = [
        transforms.Resize(int(config.input_size * 1.1)),
        transforms.RandomCrop(config.input_size),
        transforms.RandomHorizontalFlip(p=0.5),
    ]

    if config.use_randaugment:
        transform_list.append(
            RandAugmentTransform(config.rand_n, config.rand_m)
        )

    transform_list.extend([
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    return transforms.Compose(transform_list)


def build_mixup_cutmix(config: AugmentationConfig) -> MixUpCutMix | None:
    """Constrói augmentation de batch (MixUp/CutMix)."""
    if config.mode != "train":
        return None

    if not config.use_mixup and not config.use_cutmix:
        return None

    return MixUpCutMix(
        mixup_alpha=config.mixup_alpha if config.use_mixup else 0,
        cutmix_alpha=config.cutmix_alpha if config.use_cutmix else 0,
        mixup_prob=0.5 if config.use_mixup else 0,
        cutmix_prob=0.5 if config.use_cutmix else 0,
    )
```

### 6.2 Uso no Script de Treino

```python
# scripts/train.py

parser.add_argument("--use-randaugment", action="store_true")
parser.add_argument("--rand-n", type=int, default=2)
parser.add_argument("--rand-m", type=int, default=9)
parser.add_argument("--use-mixup", action="store_true")
parser.add_argument("--mixup-alpha", type=float, default=0.2)
parser.add_argument("--use-cutmix", action="store_true")
parser.add_argument("--cutmix-alpha", type=float, default=1.0)

# Build config
aug_config = AugmentationConfig(
    input_size=args.input_size,
    use_randaugment=args.use_randaugment,
    rand_n=args.rand_n,
    rand_m=args.rand_m,
    use_mixup=args.use_mixup,
    mixup_alpha=args.mixup_alpha,
    use_cutmix=args.use_cutmix,
    cutmix_alpha=args.cutmix_alpha,
    mode="train",
)

train_transform = build_transforms(aug_config)
mixup_cutmix = build_mixup_cutmix(aug_config)

# Training loop
for images, targets in train_loader:
    if mixup_cutmix:
        images, targets, _ = mixup_cutmix(images, targets.float())

    outputs = model(images)
    loss = criterion(outputs, targets)
```

---

## Checklist de Implementação

- [ ] Adicionar `RandAugmentTransform` em `src/data/transforms.py`
- [ ] Implementar `MixUp` e `CutMix` em `src/data/augmentation.py`
- [ ] Criar `ProgressiveResizing` handler
- [ ] Adicionar argumentos ao `scripts/train.py`
- [ ] Atualizar factory de transforms
- [ ] Criar testes para cada augmentation
- [ ] Documentar em `docs/training.md`

## Referências

- RandAugment: https://arxiv.org/abs/1909.13719
- MixUp: https://arxiv.org/abs/1710.09412
- CutMix: https://arxiv.org/abs/1905.04899
- Progressive Resizing: FastAI (Jeremy Howard)
