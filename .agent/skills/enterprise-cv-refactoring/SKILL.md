---
name: enterprise-cv-refactoring
description: Refatoração avançada em larga escala para sistemas de visão computacional enterprise
---

# Enterprise CV Refactoring Skill

Engenharia de refatoração para sistemas de visão computacional escaláveis (2025-2026).

---

## 1. Do Monolítico ao Modular

### Decomposição de "Wall of Text"

```python
# ❌ ANTES: Script linear denso
def process_images(paths, model, threshold, output_dir, format="png"):
    results = []
    for p in paths:
        img = cv2.imread(p)
        img = cv2.resize(img, (224, 224))
        pred = model(img)
        if pred > threshold:
            cv2.imwrite(f"{output_dir}/{p}.{format}", img)
            results.append({"path": p, "pred": pred})
    return results

# ✅ DEPOIS: Estrutura OO com responsabilidades isoladas
@dataclass
class ProcessingConfig:
    threshold: float = 0.5
    output_format: str = "png"
    target_size: tuple[int, int] = (224, 224)

class ImageProcessor:
    def __init__(self, model: nn.Module, config: ProcessingConfig):
        self.model = model
        self.config = config

    def preprocess(self, image: np.ndarray) -> np.ndarray:
        return cv2.resize(image, self.config.target_size)

    def predict(self, image: np.ndarray) -> float:
        return float(self.model(image))

    def process_batch(self, paths: list[Path]) -> list[PredictionResult]:
        return [self._process_single(p) for p in paths]
```

### Named Tuples vs Tuplas Posicionais

```python
# ❌ Frágil: ordem posicional
def detect(img) -> tuple:
    return boxes, scores, labels, masks  # Qual é qual?

bbox, score, label, mask = detect(img)  # Erro se mudar ordem

# ✅ Robusto: estrutura nomeada
from typing import NamedTuple

class DetectionResult(NamedTuple):
    boxes: np.ndarray      # (N, 4) xyxy
    scores: np.ndarray     # (N,) confidence
    labels: np.ndarray     # (N,) class ids
    masks: np.ndarray | None = None  # (N, H, W) optional

result = detect(img)
result.boxes  # Acesso por nome, imune a reordenação
```

### Encapsulamento Anti-Mutação

```python
# ❌ Bug silencioso: lista mutável como default
def add_augmentation(aug, augmentations=[]):  # PERIGO!
    augmentations.append(aug)
    return augmentations

# ✅ Correto: None como sentinel
def add_augmentation(
    aug: Augmentation,
    augmentations: list[Augmentation] | None = None,
) -> list[Augmentation]:
    if augmentations is None:
        augmentations = []
    return [*augmentations, aug]  # Nova lista, sem mutação
```

---

## 2. Performance Pythonic

### Vetorização sobre Loops

```python
# ❌ Loop Python: ~1000x mais lento
def normalize_slow(images: list[np.ndarray]) -> list[np.ndarray]:
    result = []
    for img in images:
        for i in range(img.shape[0]):
            for j in range(img.shape[1]):
                for c in range(img.shape[2]):
                    img[i, j, c] = (img[i, j, c] - 128) / 255
        result.append(img)
    return result

# ✅ Vetorizado: usa SIMD (SSE/AVX)
def normalize_fast(images: np.ndarray) -> np.ndarray:
    return (images.astype(np.float32) - 128.0) / 255.0
```

### Polars vs Pandas (10x mais rápido)

```python
import polars as pl

# Lazy evaluation + column pruning + predicate pushdown
df = (
    pl.scan_parquet("metadata/*.parquet")
    .filter(pl.col("label") == "tumor")
    .select(["image_path", "bbox", "confidence"])
    .collect()
)

# Multi-threaded nativo, backend Rust
```

**Benchmark:**
| Operação | Pandas | Polars |
|----------|--------|--------|
| groupby.agg | 45s | 4s |
| join 10M rows | 12s | 1.2s |
| filter + select | 8s | 0.3s |

### Horizontal Scaling com Spark

```python
from pyspark.sql.functions import pandas_udf
from pyspark.sql.types import ArrayType, FloatType

@pandas_udf(ArrayType(FloatType()))
def extract_features(images: pd.Series) -> pd.Series:
    # Executa em paralelo no cluster
    return images.apply(lambda x: model.encode(x).tolist())

# Distribuído via Apache Arrow
spark_df = spark.read.parquet("s3://bucket/images/")
features = spark_df.withColumn("embedding", extract_features("pixels"))
```

---

## 3. Padrões Enterprise para CV

### Compound Scaling (EfficientNet)

```python
# Escalonamento conjunto: profundidade × largura × resolução
def compound_scale(
    base_depth: int,
    base_width: int,
    base_resolution: int,
    phi: float,  # Compound coefficient
    alpha: float = 1.2,  # Depth
    beta: float = 1.1,   # Width
    gamma: float = 1.15, # Resolution
) -> tuple[int, int, int]:
    depth = int(base_depth * (alpha ** phi))
    width = int(base_width * (beta ** phi))
    resolution = int(base_resolution * (gamma ** phi))
    return depth, width, resolution

# EfficientNet-B7: phi=2.0 → 66M params, 600px
```

### Spatial Pyramid Pooling

```python
class SPPLayer(nn.Module):
    """Aceita imagens de qualquer tamanho."""

    def __init__(self, pool_sizes: list[int] = [1, 2, 4]):
        super().__init__()
        self.pool_sizes = pool_sizes

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, C, H, W = x.shape
        features = []

        for size in self.pool_sizes:
            # Adaptive pooling → tamanho fixo
            pooled = F.adaptive_max_pool2d(x, output_size=(size, size))
            features.append(pooled.view(B, -1))

        return torch.cat(features, dim=1)  # (B, C * Σ(size²))
```

### Pipeline Multimodal (YOLO-X + OCR + RAG)

```python
class DocumentAnalysisPipeline:
    def __init__(self):
        self.detector = YOLOXDetector("yolox-x")  # Layout detection
        self.ocr = PaddleOCR(use_angle_cls=True)
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        self.retriever = ChromaDB(collection="documents")

    def process(self, image: np.ndarray) -> DocumentResult:
        # 1. Detect layout regions
        regions = self.detector.detect(image)

        # 2. OCR each region
        texts = [self.ocr(crop_region(image, r)) for r in regions]

        # 3. Semantic chunking
        chunks = self._chunk_by_region(texts, regions)

        # 4. Embed and store for RAG
        embeddings = self.embedder.encode(chunks)
        self.retriever.add(chunks, embeddings)

        return DocumentResult(regions, texts, chunks)
```

---

## 4. Segurança e Governança ("Shift Left")

### CI/CD Security Pipeline

```yaml
# .github/workflows/security.yml
name: Security Checks

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Static Analysis (PEP 8)
        run: ruff check . --select=ALL

      - name: Security Scan (Bandit)
        run: bandit -r src/ -ll -ii

      - name: Dependency Audit
        run: pip-audit --strict

      - name: Secret Detection
        run: detect-secrets scan --all-files
```

### Guardrails de Entrada/Saída

```python
from pydantic import BaseModel, validator
import re

class ImageInput(BaseModel):
    """Validação de entrada com proteção contra injection."""

    path: str
    prompt: str | None = None

    @validator("path")
    def validate_path(cls, v):
        # Previne path traversal
        if ".." in v or v.startswith("/"):
            raise ValueError("Path traversal detected")
        return v

    @validator("prompt")
    def sanitize_prompt(cls, v):
        if v is None:
            return v
        # Detecta tentativas de prompt injection
        injection_patterns = [
            r"ignore.*previous",
            r"system\s*:",
            r"<\|.*\|>",
        ]
        for pattern in injection_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("Prompt injection detected")
        return v
```

### Drift Detection (PSI + KS)

```python
from scipy import stats
import numpy as np

def calculate_psi(
    expected: np.ndarray,
    actual: np.ndarray,
    buckets: int = 10,
) -> float:
    """Population Stability Index."""
    breakpoints = np.linspace(0, 1, buckets + 1)

    expected_percents = np.histogram(expected, breakpoints)[0] / len(expected)
    actual_percents = np.histogram(actual, breakpoints)[0] / len(actual)

    # Evita log(0)
    expected_percents = np.clip(expected_percents, 1e-6, 1)
    actual_percents = np.clip(actual_percents, 1e-6, 1)

    psi = np.sum(
        (actual_percents - expected_percents) *
        np.log(actual_percents / expected_percents)
    )
    return psi

def check_drift(train_dist: np.ndarray, prod_dist: np.ndarray) -> dict:
    psi = calculate_psi(train_dist, prod_dist)
    ks_stat, ks_pvalue = stats.ks_2samp(train_dist, prod_dist)

    return {
        "psi": psi,
        "psi_alert": psi > 0.2,  # Threshold padrão
        "ks_statistic": ks_stat,
        "ks_pvalue": ks_pvalue,
        "ks_alert": ks_pvalue < 0.05,
    }
```

---

## 5. Padrões PEP e Conformidade

### Type Hints Strict

```python
from typing import Protocol, TypeVar, Generic
from collections.abc import Callable

T = TypeVar("T", bound="BaseModel")

class Predictor(Protocol[T]):
    """Protocol para predictors tipados."""

    def predict(self, input: np.ndarray) -> T: ...
    def predict_batch(self, inputs: list[np.ndarray]) -> list[T]: ...

class CVPipeline(Generic[T]):
    def __init__(
        self,
        predictor: Predictor[T],
        preprocessor: Callable[[np.ndarray], np.ndarray],
    ) -> None:
        self.predictor = predictor
        self.preprocessor = preprocessor
```

### EU AI Act Compliance

```python
@dataclass
class AIRiskClassification:
    """Classificação de risco conforme EU AI Act."""

    UNACCEPTABLE = "unacceptable"  # Proibido
    HIGH_RISK = "high_risk"        # Requer certificação
    LIMITED_RISK = "limited_risk"  # Transparência
    MINIMAL_RISK = "minimal_risk"  # Sem restrições

class ExplainablePredictor(nn.Module):
    """Predictor com explicabilidade integrada."""

    def forward_with_explanation(
        self,
        x: torch.Tensor,
    ) -> tuple[torch.Tensor, dict]:
        # Predição + saliency map + attention weights
        output = self.model(x)
        explanation = {
            "saliency": self._compute_saliency(x),
            "attention": self._get_attention_weights(),
            "confidence": torch.softmax(output, dim=-1).max().item(),
            "human_override_enabled": True,
        }
        return output, explanation
```

---

## Checklist de Refatoração

- [ ] Decompor scripts monolíticos em classes OO
- [ ] Substituir tuplas por NamedTuple/Dataclass
- [ ] Eliminar defaults mutáveis
- [ ] Vetorizar loops críticos
- [ ] Migrar Pandas → Polars para datasets > 1M rows
- [ ] Implementar compound scaling em modelos
- [ ] Adicionar SPP para invariância de escala
- [ ] Integrar Bandit/Ruff no CI/CD
- [ ] Implementar guardrails de entrada
- [ ] Adicionar drift detection em produção
- [ ] Documentar classificação de risco (EU AI Act)
