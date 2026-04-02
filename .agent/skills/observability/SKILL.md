---
name: observability
description: Skill covering OpenTelemetry instrumentation, Prometheus metrics, and
  structured logging in Vitruviano.
---

# Observability Skill

## Overview

This skill provides comprehensive guidelines for implementing production-grade observability in the Vitruviano project, covering OpenTelemetry tracing, Prometheus metrics, structured logging, and alerting configurations.

---

## Table of Contents

1. [Observability Pillars](#1-observability-pillars)
2. [OpenTelemetry Integration](#2-opentelemetry-integration)
3. [Prometheus Metrics](#3-prometheus-metrics)
4. [Structured Logging](#4-structured-logging)
5. [FastAPI Instrumentation](#5-fastapi-instrumentation)
6. [Distributed Tracing](#6-distributed-tracing)
7. [Alerting Configuration](#7-alerting-configuration)
8. [Dashboards](#8-dashboards)
9. [Quick Reference](#9-quick-reference)

---

## 1. Observability Pillars

### 1.1 Three Pillars Overview

| Pillar | Purpose | Tool |
|--------|---------|------|
| **Metrics** | Aggregated numerical data | Prometheus |
| **Traces** | Request flow across services | OpenTelemetry/Jaeger |
| **Logs** | Event records with context | Structured JSON logging |

### 1.2 Vitruviano Observability Stack

```
┌──────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                    │
│  │ FastAPI  │  │ Inference│  │ Training │                    │
│  │   API    │  │  Engine  │  │  Script  │                    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                    │
│       │             │             │                           │
│       ▼             ▼             ▼                           │
│  ┌─────────────────────────────────────────┐                 │
│  │         OpenTelemetry SDK               │                 │
│  │   (Traces + Metrics + Logs)             │                 │
│  └────────────────┬────────────────────────┘                 │
└───────────────────│──────────────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
   ┌────────┐  ┌────────┐  ┌────────┐
   │ Jaeger │  │Prometheus│ │  Loki  │
   │(Traces)│  │(Metrics)│  │ (Logs) │
   └────────┘  └────────┘  └────────┘
        │           │           │
        └───────────┴───────────┘
                    │
                    ▼
              ┌──────────┐
              │  Grafana │
              │Dashboard │
              └──────────┘
```

---

## 2. OpenTelemetry Integration

### 2.1 Installation

```bash
pip install opentelemetry-api \
            opentelemetry-sdk \
            opentelemetry-exporter-otlp \
            opentelemetry-instrumentation-fastapi \
            opentelemetry-instrumentation-requests
```

### 2.2 SDK Initialization

```python
# src/observability/otel.py
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION

def configure_opentelemetry(
    service_name: str = "vitruviano-api",
    service_version: str = "1.0.0",
    otlp_endpoint: str = "http://localhost:4317",
) -> None:
    """Configure OpenTelemetry SDK with OTLP exporters."""
    # Resource attributes
    resource = Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "deployment.environment": os.getenv("ENV", "development"),
    })

    # Tracing
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
    )
    trace.set_tracer_provider(tracer_provider)

    # Metrics
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=otlp_endpoint),
        export_interval_millis=60000,  # 1 minute
    )
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[metric_reader],
    )
    metrics.set_meter_provider(meter_provider)


# Get tracer and meter
tracer = trace.get_tracer("vitruviano")
meter = metrics.get_meter("vitruviano")
```

### 2.3 Manual Span Creation

```python
from opentelemetry import trace

tracer = trace.get_tracer("vitruviano.inference")

def predict(image_bytes: bytes) -> PredictionResponse:
    """Run prediction with tracing."""
    with tracer.start_as_current_span("predict") as span:
        # Add attributes
        span.set_attribute("input.size_bytes", len(image_bytes))

        # Preprocessing
        with tracer.start_as_current_span("preprocess"):
            tensor = preprocess(image_bytes)
            span.set_attribute("tensor.shape", str(tensor.shape))

        # Inference
        with tracer.start_as_current_span("model_forward"):
            logits = model(tensor)

        # Postprocess
        with tracer.start_as_current_span("postprocess"):
            result = postprocess(logits)
            span.set_attribute("predictions.count", len(result.predictions))

        # Record custom event
        span.add_event("prediction_complete", {
            "top_finding": result.predictions[0].className,
            "top_score": result.predictions[0].score,
        })

        return result
```

### 2.4 Context Propagation

```python
from opentelemetry import context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

propagator = TraceContextTextMapPropagator()

def make_external_request(url: str, data: dict) -> dict:
    """Make HTTP request with trace context propagation."""
    headers = {}
    propagator.inject(headers)  # Inject trace context

    response = requests.post(url, json=data, headers=headers)
    return response.json()


# Extract context from incoming request
def extract_context(headers: dict):
    ctx = propagator.extract(carrier=headers)
    token = context.attach(ctx)
    try:
        # Process request with extracted context
        ...
    finally:
        context.detach(token)
```

---

## 3. Prometheus Metrics

### 3.1 Metric Types

| Type | Description | Example |
|------|-------------|---------|
| Counter | Monotonically increasing | Total requests |
| Gauge | Current value (up/down) | Active connections |
| Histogram | Distribution of values | Request latency |
| Summary | Client-side percentiles | Response time |

### 3.2 Custom Metrics

```python
from prometheus_client import Counter, Histogram, Gauge, Info

# Counters
REQUESTS_TOTAL = Counter(
    "vitruviano_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

INFERENCE_TOTAL = Counter(
    "vitruviano_inference_total",
    "Total inference requests",
    ["status"],  # success, error
)

# Histograms
INFERENCE_LATENCY = Histogram(
    "vitruviano_inference_latency_seconds",
    "Inference latency in seconds",
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

PREPROCESSING_LATENCY = Histogram(
    "vitruviano_preprocessing_latency_seconds",
    "Image preprocessing latency",
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25],
)

# Gauges
MODEL_TEMPERATURE = Gauge(
    "vitruviano_model_temperature",
    "Current calibration temperature",
)

CACHE_SIZE = Gauge(
    "vitruviano_cache_size",
    "Current response cache size",
)

GPU_MEMORY_USED = Gauge(
    "vitruviano_gpu_memory_bytes",
    "GPU memory used in bytes",
    ["device"],
)

# Info
MODEL_INFO = Info(
    "vitruviano_model",
    "Model metadata",
)
```

### 3.3 Recording Metrics

```python
import time

def predict(image_bytes: bytes) -> PredictionResponse:
    start_time = time.time()

    try:
        result = engine.predict(image_bytes)

        # Record success
        INFERENCE_TOTAL.labels(status="success").inc()
        INFERENCE_LATENCY.observe(time.time() - start_time)

        return result

    except Exception as e:
        INFERENCE_TOTAL.labels(status="error").inc()
        raise


# Update gauges
def update_metrics():
    MODEL_TEMPERATURE.set(engine.temperature)
    CACHE_SIZE.set(response_cache.size())
    GPU_MEMORY_USED.labels(device="0").set(
        torch.cuda.memory_allocated(0)
    )

# Set info
MODEL_INFO.info({
    "version": "2.0.0",
    "architecture": "densenet121",
    "num_classes": "14",
})
```

### 3.4 FastAPI Integration

```python
from prometheus_fastapi_instrumentator import Instrumentator

# Basic instrumentation
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# Custom instrumentation
instrumentator = Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
    excluded_handlers=["/health", "/metrics"],
)

@instrumentator.counter(
    metric_name="inference_requests_total",
    doc="Total inference requests",
    labels={"handler": lambda r: r.url.path},
)
def count_inference(response):
    pass

instrumentator.instrument(app).expose(app)
```

---

## 4. Structured Logging

### 4.1 JSON Log Format

```python
# src/observability/logging.py
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "props"):
            log_entry.update(record.props)

        # Add trace context
        span = trace.get_current_span()
        if span.is_recording():
            ctx = span.get_span_context()
            log_entry["trace_id"] = format(ctx.trace_id, "032x")
            log_entry["span_id"] = format(ctx.span_id, "016x")

        return json.dumps(log_entry)


def configure_logging(level: str = "INFO") -> None:
    """Configure structured JSON logging."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    logging.root.handlers = [handler]
    logging.root.setLevel(getattr(logging, level.upper()))

    # Reduce noise from libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
```

### 4.2 Contextual Logging

```python
from contextvars import ContextVar
import logging

# Request context
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")


class ContextFilter(logging.Filter):
    """Add context variables to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.user_id = user_id_var.get()
        return True


# FastAPI middleware
@app.middleware("http")
async def add_request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request_id_var.set(request_id)

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
```

### 4.3 Domain-Specific Logging

```python
import logging

# Create domain loggers
inference_logger = logging.getLogger("vitruviano.inference")
security_logger = logging.getLogger("vitruviano.security")
data_logger = logging.getLogger("vitruviano.data")


def log_inference(result: PredictionResponse, duration_ms: float) -> None:
    """Log inference result with structured data."""
    inference_logger.info(
        "Inference completed",
        extra={
            "props": {
                "duration_ms": round(duration_ms, 2),
                "predictions_count": len(result.predictions),
                "top_finding": result.predictions[0].className,
                "top_score": result.predictions[0].score,
                "ece": result.metadata.get("ece"),
            }
        },
    )


def log_security_event(event_type: str, details: dict) -> None:
    """Log security-related events."""
    security_logger.warning(
        f"Security event: {event_type}",
        extra={"props": {"event_type": event_type, **details}},
    )
```

### 4.4 Log Levels Guide

| Level | When to Use |
|-------|-------------|
| DEBUG | Detailed diagnostic info (disabled in prod) |
| INFO | Normal operation events |
| WARNING | Unexpected but recoverable situations |
| ERROR | Errors that affect operation |
| CRITICAL | System-level failures |

---

## 5. FastAPI Instrumentation

### 5.1 Telemetry Middleware

```python
# src/serving/telemetry.py
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("vitruviano.http")


class TelemetryMiddleware(BaseHTTPMiddleware):
    """Middleware for HTTP request telemetry."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        request_id = request.headers.get("X-Request-ID", "-")

        # Log request
        logger.info(
            "Request started",
            extra={
                "props": {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "client_ip": request.client.host if request.client else "-",
                }
            },
        )

        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000

            # Log response
            logger.info(
                "Request completed",
                extra={
                    "props": {
                        "request_id": request_id,
                        "status_code": response.status_code,
                        "duration_ms": round(duration_ms, 2),
                    }
                },
            )

            # Add timing header
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "Request failed",
                extra={
                    "props": {
                        "request_id": request_id,
                        "error": str(e),
                        "duration_ms": round(duration_ms, 2),
                    }
                },
            )
            raise


# In api.py
app.add_middleware(TelemetryMiddleware)
```

### 5.2 Health Check Endpoints

```python
from datetime import datetime, timezone

@app.get("/health")
def health_check() -> dict:
    """Liveness probe."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready")
def readiness_check() -> dict:
    """Readiness probe with component checks."""
    checks = {}

    # Check model
    try:
        engine = engine_state.get("engine")
        checks["model"] = "ready" if engine else "not_loaded"
    except Exception as e:
        checks["model"] = f"error: {e}"

    # Check cache
    try:
        cache_stats = response_cache.stats()
        checks["cache"] = "ready"
        checks["cache_size"] = cache_stats["size"]
    except Exception as e:
        checks["cache"] = f"error: {e}"

    # Aggregate status
    all_ready = all(v == "ready" or isinstance(v, int) for v in checks.values())

    return {
        "status": "ready" if all_ready else "degraded",
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
```

---

## 6. Distributed Tracing

### 6.1 Trace Context Headers

| Header | Purpose |
|--------|---------|
| `traceparent` | W3C Trace Context (trace-id, span-id) |
| `tracestate` | Vendor-specific trace data |
| `X-Request-ID` | Application-level request ID |

### 6.2 Cross-Service Tracing

```python
# Service A: API Gateway
from opentelemetry.propagate import inject

def call_inference_service(image_bytes: bytes) -> dict:
    headers = {}
    inject(headers)  # Inject trace context

    response = requests.post(
        "http://inference-service/predict",
        files={"file": image_bytes},
        headers=headers,
    )
    return response.json()


# Service B: Inference Service
from opentelemetry.propagate import extract

@app.post("/predict")
async def predict(request: Request, file: UploadFile):
    # Extract trace context from incoming request
    ctx = extract(dict(request.headers))
    with trace.get_tracer("inference").start_span(
        "predict",
        context=ctx,
    ) as span:
        # Process...
        pass
```

### 6.3 Jaeger Configuration

```yaml
# docker-compose.yml
services:
  jaeger:
    image: jaegertracing/all-in-one:1.52
    ports:
      - "16686:16686"  # UI
      - "4317:4317"    # OTLP gRPC
      - "4318:4318"    # OTLP HTTP
    environment:
      - COLLECTOR_OTLP_ENABLED=true
```

---

## 7. Alerting Configuration

### 7.1 Prometheus Alert Rules

```yaml
# prometheus/alerts.yml
groups:
  - name: vitruviano-alerts
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: |
          sum(rate(vitruviano_requests_total{status=~"5.."}[5m]))
          / sum(rate(vitruviano_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"

      # Slow inference
      - alert: SlowInference
        expr: |
          histogram_quantile(0.95,
            rate(vitruviano_inference_latency_seconds_bucket[5m])
          ) > 1.0
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "P95 inference latency > 1s"
          description: "P95 latency is {{ $value | humanizeDuration }}"

      # High GPU memory
      - alert: HighGPUMemory
        expr: vitruviano_gpu_memory_bytes / 1e9 > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "GPU memory usage > 10GB"

      # Service down
      - alert: ServiceDown
        expr: up{job="vitruviano-api"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Vitruviano API is down"
```

### 7.2 Alert Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| Error rate (5xx) | > 5% | > 10% |
| P95 latency | > 1s | > 5s |
| GPU memory | > 10GB | > 14GB |
| Cache hit rate | < 50% | < 20% |
| ECE drift | > 0.08 | > 0.12 |

---

## 8. Dashboards

### 8.1 Key Metrics to Display

#### Request Metrics
- Requests per second (by endpoint)
- Error rate (by status code)
- Latency percentiles (P50, P95, P99)

#### Inference Metrics
- Inference latency distribution
- Predictions per second
- Top findings distribution
- Calibration metrics (ECE, MCE, temperature)

#### System Metrics
- GPU memory utilization
- CPU usage
- Cache hit rate
- Active connections

### 8.2 Grafana Dashboard JSON

```json
{
  "title": "Vitruviano API",
  "panels": [
    {
      "title": "Request Rate",
      "type": "graph",
      "targets": [
        {
          "expr": "sum(rate(vitruviano_requests_total[5m])) by (status)",
          "legendFormat": "{{status}}"
        }
      ]
    },
    {
      "title": "Inference Latency",
      "type": "heatmap",
      "targets": [
        {
          "expr": "sum(rate(vitruviano_inference_latency_seconds_bucket[5m])) by (le)"
        }
      ]
    },
    {
      "title": "GPU Memory",
      "type": "gauge",
      "targets": [
        {
          "expr": "vitruviano_gpu_memory_bytes / 1e9"
        }
      ]
    }
  ]
}
```

---

## 9. Quick Reference

### 9.1 Quick Reference Card

```
╔══════════════════════════════════════════════════════════════╗
║               OBSERVABILITY QUICK REFERENCE                  ║
╠══════════════════════════════════════════════════════════════╣
║ OPENTELEMETRY                                                ║
║ ├─ tracer.start_as_current_span("name")  → Create span      ║
║ ├─ span.set_attribute("key", value)      → Add metadata     ║
║ ├─ span.add_event("name", attrs)         → Log event        ║
║ └─ inject(headers) / extract(headers)    → Propagate ctx    ║
╠══════════════════════════════════════════════════════════════╣
║ PROMETHEUS                                                   ║
║ ├─ Counter:   .inc(), .labels(a=1).inc()                    ║
║ ├─ Gauge:     .set(val), .inc(), .dec()                     ║
║ ├─ Histogram: .observe(val)                                 ║
║ └─ Info:      .info({...})                                  ║
╠══════════════════════════════════════════════════════════════╣
║ LOGGING                                                      ║
║ ├─ DEBUG:     Detailed diagnostics                          ║
║ ├─ INFO:      Normal operations                             ║
║ ├─ WARNING:   Recoverable issues                            ║
║ ├─ ERROR:     Operation failures                            ║
║ └─ CRITICAL:  System failures                               ║
╠══════════════════════════════════════════════════════════════╣
║ ENDPOINTS                                                    ║
║ ├─ /health   → Liveness probe                               ║
║ ├─ /ready    → Readiness probe                              ║
║ └─ /metrics  → Prometheus scrape                            ║
╚══════════════════════════════════════════════════════════════╝
```

### 9.2 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP collector endpoint | `http://localhost:4317` |
| `OTEL_SERVICE_NAME` | Service name for traces | `vitruviano-api` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `LOG_FORMAT` | Log format (json/text) | `json` |

---

*Last Updated: 2026-01-19 | Version: 1.0.0*
