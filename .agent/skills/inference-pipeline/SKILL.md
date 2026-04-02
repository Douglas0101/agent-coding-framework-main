---
name: inference-pipeline
description: Skill for building production-grade ML inference pipelines with FastAPI,
  caching, calibration, and optimization in Vitruviano.
---

# Inference Pipeline Skill

## Overview

This skill provides comprehensive guidelines for building enterprise-grade machine learning inference pipelines in the Vitruviano project, covering FastAPI serving, model optimization, response caching, and calibration integration.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [FastAPI Serving Layer](#2-fastapi-serving-layer)
3. [Inference Engine Pattern](#3-inference-engine-pattern)
4. [Model Optimization](#4-model-optimization)
5. [Response Caching](#5-response-caching)
6. [Calibration Integration](#6-calibration-integration)
7. [Health and Readiness](#7-health-and-readiness)
8. [Observability](#8-observability)
9. [Batch Inference](#9-batch-inference)
10. [Regression Snapshots & Drift Analysis](#10-regression-snapshots--drift-analysis)
11. [Quick Reference](#11-quick-reference)

---

## 1. Architecture Overview

### 1.1 High-Level Architecture

```
╔═══════════════════════════════════════════════════════════════╗
║                    INFERENCE PIPELINE                         ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐  ║
║  │   Client    │───▶│   FastAPI    │───▶│  InferenceEngine │  ║
║  │   Request   │    │   API Layer  │    │   (PyTorch)     │  ║
║  └─────────────┘    └──────────────┘    └─────────────────┘  ║
║         │                  │                     │            ║
║         │                  ▼                     ▼            ║
║         │          ┌──────────────┐    ┌─────────────────┐   ║
║         │          │   Response   │    │   Calibration   │   ║
║         │          │    Cache     │    │   (Temp Scale)  │   ║
║         │          └──────────────┘    └─────────────────┘   ║
║         │                  │                     │            ║
║         │                  ▼                     ▼            ║
║         │          ┌──────────────┐    ┌─────────────────┐   ║
║         └─────────▶│   Telemetry  │◀───│   Prometheus    │   ║
║                    │   Middleware │    │   Metrics       │   ║
║                    └──────────────┘    └─────────────────┘   ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

### 1.2 Module Structure

```
src/serving/
├── __init__.py
├── api.py              # FastAPI application
├── inference.py        # InferenceEngine class
├── schemas.py          # Pydantic models
├── telemetry.py        # Logging and tracing
└── cache.py            # Response caching (optional)
```

---

## 2. FastAPI Serving Layer

### 2.1 Application Setup

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

# Global state for singleton pattern
engine_state: dict = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context for startup/shutdown."""
    # Startup: Load model
    logger.info("Initializing Inference Service...")
    engine_state["engine"] = InferenceEngine(
        model_path=os.getenv("MODEL_PATH"),
        calibration_path=os.getenv("CALIBRATION_PATH"),
        device=os.getenv("DEVICE", "cpu"),
    )
    logger.info("Service Ready.")

    yield

    # Shutdown: Cleanup
    logger.info("Shutting down service...")
    engine_state.clear()

app = FastAPI(
    title="Vitruviano Serving Layer",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)
```

### 2.2 API Key Authentication

```python
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(
    header_val: str = Security(api_key_header),
) -> str | None:
    """Validate API Key from header."""
    expected_key = os.getenv("API_KEY")

    if not expected_key:
        logger.warning("API_KEY not set! Unprotected endpoint!")
        return None

    if not header_val:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if header_val != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return header_val
```

### 2.3 Prediction Endpoint

```python
from fastapi import UploadFile, File, Depends

# Module-level constant for B008 compliance
FILE_PARAM = File(...)
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))

@app.post("/predict", response_model=PredictionResponse)
async def predict_image(
    file: UploadFile = FILE_PARAM,
    _auth: str = Depends(get_api_key),
) -> PredictionResponse:
    """Run inference on uploaded image."""
    if not engine_state.get("engine"):
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        content = await _validate_image(file)
        engine = engine_state["engine"]
        return engine.predict(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("Inference error: %s", e)
        raise HTTPException(
            status_code=500, detail="Internal processing error"
        ) from e
    finally:
        await file.close()
```

### 2.4 Input Validation

```python
async def _validate_image(file: UploadFile) -> bytes:
    """Validate image file and read content."""
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Must be an image.",
        )

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large.")
    if not content:
        raise HTTPException(status_code=400, detail="Empty file.")

    return content
```

---

## 3. Inference Engine Pattern

### 3.1 Engine Class Structure

```python
class InferenceEngine:
    """Production inference engine with calibration."""

    CLASSES = [
        "Atelectasis", "Cardiomegaly", "Effusion", "Infiltration",
        "Mass", "Nodule", "Pneumonia", "Pneumothorax",
        "Consolidation", "Edema", "Emphysema", "Fibrosis",
        "Pleural_Thickening", "Hernia",
    ]

    def __init__(
        self,
        model_path: str,
        calibration_path: str,
        device: str = "cpu",
    ):
        self.device = torch.device(device)
        self.temperature = 1.0
        self.thresholds = torch.tensor([0.5] * 14).to(self.device)
        self.ece = 0.0
        self.mce = 0.0

        # Preprocessing (must match training)
        self.transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ])

        # Load artifacts
        self.model = self._load_model(model_path)
        self._load_calibration(calibration_path)
```

### 3.2 Safe Model Loading

```python
def _load_model(self, path: str) -> nn.Module:
    """Load model with safety checks."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Model not found: {path}")

    logger.info("Loading model from %s...", path)
    model = ChestXrayClassifier(num_classes=14, pretrained=False)
    model.to(self.device)

    # Secure loading (weights only)
    trust_ckpt = os.getenv("TRUST_CHECKPOINT", "false").lower() == "true"
    state_dict = load_checkpoint_safely(
        path,
        map_location=self.device,
        trust_checkpoint=trust_ckpt,
    )

    # Handle nested state dicts
    for key in ["model_state", "state_dict", "model"]:
        if key in state_dict:
            state_dict = state_dict[key]
            break

    model.load_state_dict(state_dict)
    model.eval()

    # Apply torch.compile for inference acceleration
    if self.device.type == "cuda" and hasattr(torch, "compile"):
        try:
            model = torch.compile(model, mode="reduce-overhead")
            logger.info("Model compiled with torch.compile")
        except Exception as e:
            logger.warning("torch.compile failed: %s", e)

    return model
```

### 3.3 Inference Method

```python
@torch.no_grad()
def predict(self, image_bytes: bytes) -> PredictionResponse:
    """Run end-to-end inference on image bytes."""
    start_time = time.time()

    # 1. Preprocessing
    image = self._load_and_validate_image(image_bytes)
    tensor = self.transform(image).unsqueeze(0).to(self.device)

    # 2. Inference
    logits = self.model(tensor)

    # 3. Calibration (Temperature Scaling)
    scaled_logits = logits / self.temperature
    probs = torch.sigmoid(scaled_logits)

    # 4. Dynamic Thresholding
    is_detected = probs >= self.thresholds

    # 5. Format Output
    results = self._format_predictions(probs, is_detected)
    duration_ms = (time.time() - start_time) * 1000

    return PredictionResponse(
        predictions=results,
        metadata={
            "processing_time_ms": round(duration_ms, 2),
            "temperature": self.temperature,
            "ece": self.ece,
            "mce": self.mce,
        },
    )
```

---

## 4. Model Optimization

### 4.1 torch.compile (PyTorch 2.0+)

```python
# Compilation modes
# - "default": Good balance of speed and compile time
# - "reduce-overhead": Best for inference (lower latency)
# - "max-autotune": Best throughput (longer compile, no caching)

if hasattr(torch, "compile"):
    model = torch.compile(
        model,
        mode="reduce-overhead",  # Best for serving
        fullgraph=True,          # Compile entire graph
    )
```

### 4.2 ONNX Export

```python
import torch.onnx

def export_to_onnx(
    model: nn.Module,
    output_path: str,
    input_shape: tuple = (1, 3, 224, 224),
) -> None:
    """Export model to ONNX format."""
    model.eval()
    dummy_input = torch.randn(*input_shape)

    torch.onnx.export(
        model,
        dummy_input,
        output_path,
        export_params=True,
        opset_version=17,
        do_constant_folding=True,
        input_names=["image"],
        output_names=["logits"],
        dynamic_axes={
            "image": {0: "batch_size"},
            "logits": {0: "batch_size"},
        },
    )

# Usage
export_to_onnx(model, "model.onnx")
```

### 4.3 ONNX Runtime Inference

```python
import onnxruntime as ort

class ONNXInferenceEngine:
    """ONNX Runtime-based inference engine."""

    def __init__(self, model_path: str, device: str = "cpu"):
        providers = ["CPUExecutionProvider"]
        if device == "cuda":
            providers.insert(0, "CUDAExecutionProvider")

        self.session = ort.InferenceSession(
            model_path,
            providers=providers,
        )
        self.input_name = self.session.get_inputs()[0].name

    def predict(self, tensor: np.ndarray) -> np.ndarray:
        """Run inference with ONNX Runtime."""
        outputs = self.session.run(
            None,
            {self.input_name: tensor.astype(np.float32)},
        )
        return outputs[0]
```

### 4.4 TensorRT Optimization (NVIDIA)

```python
import tensorrt as trt
import torch_tensorrt

def optimize_for_tensorrt(
    model: nn.Module,
    input_shape: tuple = (1, 3, 224, 224),
) -> nn.Module:
    """Optimize model with TensorRT."""
    model.eval()

    inputs = [
        torch_tensorrt.Input(
            shape=input_shape,
            dtype=torch.float32,
        ),
    ]

    optimized_model = torch_tensorrt.compile(
        model,
        inputs=inputs,
        enabled_precisions={torch.float32, torch.float16},
        workspace_size=1 << 28,  # 256MB
    )

    return optimized_model
```

---

## 5. Response Caching

### 5.1 LRU Cache with TTL

```python
from collections import OrderedDict
import hashlib
import time

class ResponseCache:
    """LRU cache with TTL for inference responses."""

    def __init__(self, max_size: int = 1000, ttl_seconds: float = 60.0):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, tuple[float, dict]] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def _make_key(self, content: bytes) -> str:
        """Create cache key from content hash."""
        return hashlib.sha256(content).hexdigest()[:32]

    def get(self, content: bytes) -> dict | None:
        """Get cached response if exists and not expired."""
        key = self._make_key(content)
        if key not in self._cache:
            self._misses += 1
            return None

        timestamp, response = self._cache[key]
        if time.time() - timestamp > self.ttl_seconds:
            del self._cache[key]
            self._misses += 1
            return None

        self._cache.move_to_end(key)  # LRU update
        self._hits += 1
        return response

    def set(self, content: bytes, response: dict) -> None:
        """Store response in cache."""
        key = self._make_key(content)

        # Evict oldest if at capacity
        while len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)

        self._cache[key] = (time.time(), response)

    def stats(self) -> dict:
        """Get cache statistics."""
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0.0,
            "size": len(self._cache),
        }
```

### 5.2 Cache Integration

```python
# Global cache (configurable via env vars)
CACHE_ENABLED = os.getenv("RESPONSE_CACHE_ENABLED", "true").lower() == "true"
response_cache = ResponseCache(
    max_size=int(os.getenv("RESPONSE_CACHE_SIZE", "1000")),
    ttl_seconds=float(os.getenv("RESPONSE_CACHE_TTL", "60.0")),
)

@app.post("/predict")
async def predict_image(file: UploadFile = FILE_PARAM):
    content = await _validate_image(file)

    # Check cache first
    if CACHE_ENABLED:
        cached = response_cache.get(content)
        if cached:
            logger.debug("Cache hit")
            return cached

    # Run inference
    result = engine.predict(content)

    # Store in cache
    if CACHE_ENABLED:
        response_cache.set(content, result.model_dump())

    return result
```

---

## 6. Calibration Integration

### 6.1 Temperature Scaling

```python
def _load_calibration(self, path: str) -> None:
    """Load calibration parameters from JSON."""
    if not os.path.exists(path):
        logger.warning("Calibration not found, using defaults")
        return

    with open(path) as f:
        data = json.load(f)

    # Temperature
    if "temperature" in data:
        self.temperature = data["temperature"]
        logger.info("Temperature: %.4f", self.temperature)

    # Thresholds (Youden Index)
    if "thresholds" in data and "youden" in data["thresholds"]:
        youden_thr = data["thresholds"]["youden"]
        ordered_thr = [youden_thr.get(cls, 0.5) for cls in self.CLASSES]
        self.thresholds = torch.tensor(ordered_thr).to(self.device)
        logger.info("Applied dynamic thresholds")

    # Metrics
    if "ece" in data:
        self.ece = float(data["ece"].get("ts", 0.0))
    if "mce" in data:
        self.mce = float(data["mce"].get("ts", 0.0))
```

### 6.2 Calibration Endpoint

```python
@app.get("/calibration")
def get_calibration() -> dict:
    """Get current calibration metrics."""
    if "engine" not in engine_state:
        raise HTTPException(status_code=503, detail="Service not ready")

    engine = engine_state["engine"]
    return {
        "temperature": engine.temperature,
        "ece": engine.ece,
        "mce": engine.mce,
        "quality": _get_calibration_quality(engine.ece),
    }

def _get_calibration_quality(ece: float) -> str:
    """Classify calibration quality."""
    if ece < 0.02:
        return "Excellent"
    if ece < 0.05:
        return "Very Good"
    if ece < 0.10:
        return "Good"
    if ece < 0.15:
        return "Moderate"
    return "Poor"
```

---

## 7. Health and Readiness

### 7.1 Liveness Probe

```python
@app.get("/health")
def health_check() -> dict:
    """Liveness probe for Kubernetes."""
    if "engine" in engine_state:
        return {"status": "healthy", "components": {"engine": "loaded"}}
    return {"status": "unhealthy", "reason": "engine not loaded"}
```

### 7.2 Readiness Probe

```python
@app.get("/ready")
def readiness_check() -> dict:
    """Readiness probe for Kubernetes."""
    engine = engine_state.get("engine")
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not loaded")

    # Verify model is functional
    try:
        dummy_input = torch.zeros(1, 3, 224, 224).to(engine.device)
        with torch.no_grad():
            _ = engine.model(dummy_input)
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
```

### 7.3 Model Warmup

```python
def warmup_model(engine: InferenceEngine, n_iterations: int = 3) -> None:
    """Warmup model for optimal performance."""
    logger.info("Warming up model...")
    dummy_image = Image.new("RGB", (224, 224), color="gray")
    dummy_bytes = io.BytesIO()
    dummy_image.save(dummy_bytes, format="PNG")
    dummy_bytes = dummy_bytes.getvalue()

    for i in range(n_iterations):
        _ = engine.predict(dummy_bytes)
        logger.debug("Warmup iteration %d/%d", i + 1, n_iterations)

    logger.info("Model warmup complete")
```

---

## 8. Observability

### 8.1 Prometheus Metrics

```python
from prometheus_fastapi_instrumentator import Instrumentator

# Auto-instrument all endpoints
Instrumentator().instrument(app).expose(app)

# Custom metrics
from prometheus_client import Counter, Histogram

INFERENCE_LATENCY = Histogram(
    "inference_latency_seconds",
    "Inference latency in seconds",
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)

INFERENCE_COUNT = Counter(
    "inference_total",
    "Total inference requests",
    ["status"],  # success/error
)

@app.post("/predict")
async def predict_image(file: UploadFile = FILE_PARAM):
    with INFERENCE_LATENCY.time():
        try:
            result = engine.predict(await file.read())
            INFERENCE_COUNT.labels(status="success").inc()
            return result
        except Exception:
            INFERENCE_COUNT.labels(status="error").inc()
            raise
```

### 8.2 Structured Logging

```python
import json
import logging

class JSONFormatter(logging.Formatter):
    """JSON structured log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        # Add extra properties
        if hasattr(record, "props"):
            log_entry.update(record.props)

        return json.dumps(log_entry)

def configure_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logging.root.addHandler(handler)
    logging.root.setLevel(logging.INFO)
```

---

## 9. Batch Inference

### 9.1 Batch Endpoint

```python
from pydantic import BaseModel

class BatchPredictionRequest(BaseModel):
    image_ids: list[str]

@app.post("/predict/batch")
async def predict_batch(
    request: BatchPredictionRequest,
    _auth: str = Depends(get_api_key),
) -> dict:
    """Run batch inference on multiple images."""
    if len(request.image_ids) > 32:
        raise HTTPException(400, "Maximum batch size is 32")

    results = []
    for image_id in request.image_ids:
        image_bytes = await _load_image(image_id)
        result = engine.predict(image_bytes)
        results.append({
            "image_id": image_id,
            "predictions": result.predictions,
        })

    return {"results": results}
```

### 9.2 Vectorized Batch Processing

```python
@torch.no_grad()
def predict_batch(
    self,
    images: list[bytes],
) -> list[PredictionResponse]:
    """Run batch inference."""
    tensors = []
    for img_bytes in images:
        image = self._load_and_validate_image(img_bytes)
        tensors.append(self.transform(image))

    # Stack into batch
    batch = torch.stack(tensors).to(self.device)

    # Single forward pass
    logits = self.model(batch)
    scaled_logits = logits / self.temperature
    probs = torch.sigmoid(scaled_logits)

    # Format results
    return [
        self._format_prediction(probs[i])
        for i in range(len(images))
    ]
```

---

## 10. Regression Snapshots & Drift Analysis

### 10.1 Drift Validation Flow

Before deploying a new model version, it's critical to ensure it doesn't suffer from "silent calibration regressions" or dramatic probability shifts compared to the current production model.

The regression snapshots layer provides tools to automate this:

```bash
# 1. Take a snapshot of the current (Base) model
python scripts/regression_take_snapshot.py \
  --golden-set <golden_set_name> \
  --model-version <current_version> \
  --model-path <path_to_base_model> \
  --calibration-path <path_to_base_calib>

# 2. Take a snapshot of the new (Target) model
python scripts/regression_take_snapshot.py \
  --golden-set <golden_set_name> \
  --model-version <new_version> \
  --model-path <path_to_new_model> \
  --calibration-path <path_to_new_calib>

# 3. Compare for statistical and calibration drift
python scripts/regression_compare_snapshots.py \
  --golden-set <golden_set_name> \
  --base <current_version> --target <new_version>
```

### 10.2 Continuous Monitoring

- **Golden Sets**: Regularly update your `GoldenSet` definitions using `regression_create_golden_set.py` to ensure they reflect current clinical edge cases.
- **Metrics**: The `DriftReport` generated calculates Delta ECE/MCE and Class MAE. High MAE without corresponding AUC improvements often signals instability.

---

## 11. Quick Reference

### 11.1 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MODEL_PATH` | Path to model checkpoint | Required |
| `CALIBRATION_PATH` | Path to calibration JSON | Required |
| `DEVICE` | Compute device (cpu/cuda) | `cpu` |
| `API_KEY` | API key for authentication | None |
| `MAX_UPLOAD_BYTES` | Maximum upload size | 10MB |
| `RESPONSE_CACHE_ENABLED` | Enable response caching | `true` |
| `RESPONSE_CACHE_SIZE` | Cache max entries | 1000 |
| `RESPONSE_CACHE_TTL` | Cache TTL in seconds | 60 |

### 10.2 Quick Reference Card

```
╔══════════════════════════════════════════════════════════════╗
║             INFERENCE PIPELINE QUICK REFERENCE               ║
╠══════════════════════════════════════════════════════════════╣
║ ENDPOINTS                                                    ║
║ ├─ POST /predict          → Single image inference           ║
║ ├─ POST /predict/batch    → Batch inference                  ║
║ ├─ GET  /health           → Liveness probe                   ║
║ ├─ GET  /ready            → Readiness probe                  ║
║ ├─ GET  /calibration      → Calibration metrics              ║
║ └─ GET  /metrics          → Prometheus metrics               ║
╠══════════════════════════════════════════════════════════════╣
║ OPTIMIZATION                                                 ║
║ ├─ torch.compile          → PyTorch 2.x acceleration         ║
║ ├─ ONNX Runtime           → Cross-platform inference         ║
║ ├─ TensorRT               → NVIDIA GPU optimization          ║
║ └─ Response Cache         → LRU with TTL                     ║
╠══════════════════════════════════════════════════════════════╣
║ CALIBRATION                                                  ║
║ ├─ Temperature Scaling    → logits / T before sigmoid        ║
║ ├─ Dynamic Thresholds     → Youden Index per class           ║
║ ├─ ECE Target             → < 0.05                           ║
║ └─ MCE Target             → < 0.15                           ║
╚══════════════════════════════════════════════════════════════╝
```

---

*Last Updated: 2026-01-19 | Version: 1.0.0*
