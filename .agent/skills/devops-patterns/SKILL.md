---
name: devops-patterns
description: Skill for implementing Docker, CI/CD, and deployment best practices in
  Vitruviano.
---

# DevOps Patterns Skill

## Overview

This skill provides comprehensive guidelines for implementing production-grade DevOps practices in the Vitruviano project, covering Docker containerization, GitHub Actions CI/CD, dependency management, and deployment strategies.

---

## Table of Contents

1. [Docker Best Practices](#1-docker-best-practices)
2. [Multi-Stage Builds for ML](#2-multi-stage-builds-for-ml)
3. [GitHub Actions Workflows](#3-github-actions-workflows)
4. [Pre-commit Automation](#4-pre-commit-automation)
5. [Dependency Management](#5-dependency-management)
6. [Artifact Versioning](#6-artifact-versioning)
7. [Environment Configuration](#7-environment-configuration)
8. [Deployment Strategies](#8-deployment-strategies)
9. [Quick Reference](#9-quick-reference)

---

## 1. Docker Best Practices

### 1.1 Base Image Selection

| Use Case | Recommended Base | Size |
|----------|------------------|------|
| Production API | `python:3.11-slim` | ~150MB |
| ML Training | `pytorch/pytorch:2.1.2-cuda12.1-cudnn8-runtime` | ~5GB |
| Development | `python:3.11` | ~900MB |
| Minimal CLI | `python:3.11-alpine` | ~50MB |

### 1.2 Production Dockerfile

```dockerfile
# syntax=docker/dockerfile:1.6
FROM python:3.11-slim AS base

# Security: Run as non-root
RUN groupadd -r vitruviano && useradd -r -g vitruviano vitruviano

# Environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# ─────────────────────────────────────────────
# Stage 1: Dependencies
# ─────────────────────────────────────────────
FROM base AS deps

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ─────────────────────────────────────────────
# Stage 2: Production
# ─────────────────────────────────────────────
FROM base AS production

# Copy only installed packages
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=vitruviano:vitruviano src/ ./src/
COPY --chown=vitruviano:vitruviano models/ ./models/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Switch to non-root user
USER vitruviano

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "src.serving.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 1.3 .dockerignore

```dockerignore
# Git
.git/
.gitignore

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
venv/
.eggs/
*.egg-info/

# Testing
tests/
.pytest_cache/
.coverage
htmlcov/

# IDE
.idea/
.vscode/
*.swp

# Data (mount at runtime)
data/
outputs/
*.pth
*.onnx

# Documentation
docs/
*.md

# Development
.pre-commit-config.yaml
Makefile
docker-compose.dev.yml
```

### 1.4 Layer Optimization

```dockerfile
# ❌ Bad: Multiple RUN commands create many layers
RUN apt-get update
RUN apt-get install -y curl
RUN apt-get install -y git
RUN rm -rf /var/lib/apt/lists/*

# ✅ Good: Single RUN with cleanup
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*
```

---

## 2. Multi-Stage Builds for ML

### 2.1 GPU Training Image

```dockerfile
# syntax=docker/dockerfile:1.6

# ─────────────────────────────────────────────
# Stage 1: Base with CUDA
# ─────────────────────────────────────────────
FROM pytorch/pytorch:2.1.2-cuda12.1-cudnn8-runtime AS base

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /workspace

# ─────────────────────────────────────────────
# Stage 2: Dependencies
# ─────────────────────────────────────────────
FROM base AS deps

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ─────────────────────────────────────────────
# Stage 3: Development (includes dev tools)
# ─────────────────────────────────────────────
FROM deps AS development

COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY . .

CMD ["bash"]

# ─────────────────────────────────────────────
# Stage 4: Production Training
# ─────────────────────────────────────────────
FROM deps AS training

# Copy only training code
COPY src/ ./src/
COPY scripts/train.py ./scripts/
COPY configs/ ./configs/

# Mount points
VOLUME ["/data", "/outputs"]

ENTRYPOINT ["python", "scripts/train.py"]
CMD ["--config", "configs/default.yaml"]
```

### 2.2 ONNX Export Image

```dockerfile
FROM python:3.11-slim AS onnx-builder

RUN pip install --no-cache-dir \
    torch==2.1.2 --index-url https://download.pytorch.org/whl/cpu \
    onnx==1.15.0 \
    onnxruntime==1.16.3

WORKDIR /export

COPY src/models/ ./src/models/
COPY scripts/export_onnx.py ./

ENTRYPOINT ["python", "scripts/export_onnx.py"]
```

### 2.3 Docker Compose for Development

```yaml
# docker-compose.yml
version: "3.9"

services:
  api:
    build:
      context: .
      target: production
    ports:
      - "8000:8000"
    environment:
      - MODEL_PATH=/models/best_model.pth
      - CALIBRATION_PATH=/models/calibration.json
      - API_KEY=${API_KEY}
      - LOG_LEVEL=INFO
    volumes:
      - ./models:/models:ro
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  prometheus:
    image: prom/prometheus:v2.48.0
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro

  jaeger:
    image: jaegertracing/all-in-one:1.52
    ports:
      - "16686:16686"
      - "4317:4317"
    environment:
      - COLLECTOR_OTLP_ENABLED=true
```

---

## 3. GitHub Actions Workflows

### 3.1 Main CI Workflow

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

env:
  PYTHON_VERSION: "3.11"

jobs:
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Cache pip
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}
          restore-keys: ${{ runner.os }}-pip-

      - name: Install dependencies
        run: pip install ruff mypy bandit

      - name: Ruff lint
        run: ruff check src/

      - name: Ruff format check
        run: ruff format --check src/

      - name: Mypy
        run: mypy src/ --ignore-missing-imports

      - name: Bandit security check
        run: bandit -r src/ -c pyproject.toml

  test:
    name: Test
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Cache pip
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run tests
        run: pytest tests/ -v --cov=src --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: coverage.xml
          token: ${{ secrets.CODECOV_TOKEN }}

  build:
    name: Build Docker
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: false
          tags: vitruviano:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### 3.2 Release Workflow

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - "v*"

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      packages: write

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract version
        id: version
        run: echo "version=${GITHUB_REF#refs/tags/v}" >> $GITHUB_OUTPUT

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:${{ steps.version.outputs.version }}
            ghcr.io/${{ github.repository }}:latest
          cache-from: type=gha

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v1
        with:
          generate_release_notes: true
```

### 3.3 Scheduled Security Scan

```yaml
# .github/workflows/security.yml
name: Security Scan

on:
  schedule:
    - cron: "0 0 * * 1"  # Weekly on Monday
  workflow_dispatch:

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: "fs"
          scan-ref: "."
          format: "sarif"
          output: "trivy-results.sarif"

      - name: Upload to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: "trivy-results.sarif"

      - name: Dependency audit
        run: |
          pip install pip-audit
          pip-audit -r requirements.txt
```

---

## 4. Pre-commit Automation

### 4.1 Configuration

```yaml
# .pre-commit-config.yaml
repos:
  # Ruff (lint + format)
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.9.4
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  # Type checking
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-requests, types-PyYAML]
        args: [--ignore-missing-imports]

  # Security
  - repo: https://github.com/PyCQA/bandit
    rev: 1.8.3
    hooks:
      - id: bandit
        args: [-c, pyproject.toml, -r, src/]

  # General checks
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: [--maxkb=1000]
      - id: check-merge-conflict
      - id: detect-private-key
```

### 4.2 Installation

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run on all files
pre-commit run --all-files

# Auto-update hooks
pre-commit autoupdate
```

---

## 5. Dependency Management

### 5.1 Requirements Structure

```
requirements.txt          # Production dependencies (pinned)
requirements-dev.txt      # Development tools
requirements-gpu.txt      # GPU-specific (CUDA)
constraints.txt           # Version constraints
```

### 5.2 requirements.txt (Production)

```txt
# Core ML
torch==2.1.2
torchvision==0.16.2
numpy==1.26.4

# API
fastapi==0.109.0
uvicorn==0.27.0
pydantic==2.6.0

# Security
cryptography==41.0.7

# Observability
opentelemetry-api==1.22.0
prometheus-fastapi-instrumentator==6.0.0
```

### 5.3 requirements-dev.txt

```txt
-r requirements.txt

# Testing
pytest==7.4.4
pytest-cov==4.1.0
pytest-asyncio==0.23.3

# Linting
ruff==0.9.4
mypy==1.8.0
bandit==1.8.3

# Types
types-requests
types-PyYAML

# Tools
pre-commit==3.6.0
pip-audit==2.7.0
```

### 5.4 Dependency Audit

```bash
# Check for vulnerabilities
pip-audit -r requirements.txt

# Check for outdated packages
pip list --outdated

# Generate license report
pip-licenses --format=markdown > LICENSES.md
```

---

## 6. Artifact Versioning

### 6.1 Model Version Naming

```
models/
├── v1.0.0/
│   ├── model.pth
│   ├── calibration.json
│   ├── config.yaml
│   └── metrics.json
├── v1.1.0/
│   └── ...
└── latest -> v1.1.0
```

### 6.2 Version Metadata

```json
{
  "version": "1.1.0",
  "created_at": "2026-01-19T00:00:00Z",
  "git_commit": "abc123def",
  "training_config": {
    "epochs": 50,
    "batch_size": 32,
    "learning_rate": 0.001
  },
  "metrics": {
    "auc_macro": 0.891,
    "ece": 0.032
  },
  "dependencies": {
    "torch": "2.1.2",
    "torchvision": "0.16.2"
  }
}
```

### 6.3 Semantic Versioning

| Change Type | Version Bump | Example |
|-------------|-------------|---------|
| Bug fixes, recalibration | PATCH | 1.0.0 → 1.0.1 |
| New features, architecture changes | MINOR | 1.0.0 → 1.1.0 |
| Breaking API changes | MAJOR | 1.0.0 → 2.0.0 |

---

## 7. Environment Configuration

### 7.1 Environment Variables

```bash
# .env.example
# API Configuration
API_KEY=your-api-key-here
HOST=0.0.0.0
PORT=8000

# Model Configuration
MODEL_PATH=/models/best_model.pth
CALIBRATION_PATH=/models/calibration.json
DEVICE=cuda

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Observability
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=vitruviano-api

# Security
TRUST_CHECKPOINT=false
MAX_UPLOAD_BYTES=10485760
```

### 7.2 Config Management

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """Application configuration from environment."""

    # API
    api_key: str
    host: str = "0.0.0.0"
    port: int = 8000

    # Model
    model_path: str
    calibration_path: str
    device: str = "cpu"

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Security
    trust_checkpoint: bool = False
    max_upload_bytes: int = 10 * 1024 * 1024

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

---

## 8. Deployment Strategies

### 8.1 Blue-Green Deployment

```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vitruviano-blue
spec:
  replicas: 3
  selector:
    matchLabels:
      app: vitruviano
      version: blue
  template:
    spec:
      containers:
        - name: api
          image: ghcr.io/org/vitruviano:1.0.0
          ports:
            - containerPort: 8000
          readinessProbe:
            httpGet:
              path: /ready
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 15
            periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: vitruviano
spec:
  selector:
    app: vitruviano
    version: blue  # Switch to 'green' for deployment
  ports:
    - port: 80
      targetPort: 8000
```

### 8.2 Canary Deployment

```yaml
# kubernetes/canary.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: vitruviano-canary
  annotations:
    nginx.ingress.kubernetes.io/canary: "true"
    nginx.ingress.kubernetes.io/canary-weight: "10"  # 10% traffic
spec:
  rules:
    - host: api.vitruviano.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: vitruviano-canary
                port:
                  number: 80
```

### 8.3 Rollback Procedure

```bash
# Check deployment history
kubectl rollout history deployment/vitruviano

# Rollback to previous version
kubectl rollout undo deployment/vitruviano

# Rollback to specific revision
kubectl rollout undo deployment/vitruviano --to-revision=2

# Check rollout status
kubectl rollout status deployment/vitruviano
```

---

## 9. Quick Reference

### 9.1 Quick Reference Card

```
╔══════════════════════════════════════════════════════════════╗
║               DEVOPS PATTERNS QUICK REFERENCE                ║
╠══════════════════════════════════════════════════════════════╣
║ DOCKER                                                       ║
║ ├─ Base Image:  python:3.11-slim (production)               ║
║ ├─ Multi-stage: deps → production (smaller image)           ║
║ ├─ Non-root:    USER vitruviano                              ║
║ └─ Health:      HEALTHCHECK with curl                        ║
╠══════════════════════════════════════════════════════════════╣
║ CI/CD                                                        ║
║ ├─ Lint:        ruff check + ruff format --check            ║
║ ├─ Type:        mypy --ignore-missing-imports                ║
║ ├─ Security:    bandit -r src/                               ║
║ ├─ Test:        pytest --cov=src                             ║
║ └─ Build:       docker/build-push-action                     ║
╠══════════════════════════════════════════════════════════════╣
║ PRE-COMMIT                                                   ║
║ ├─ Install:     pre-commit install                           ║
║ ├─ Run all:     pre-commit run --all-files                   ║
║ └─ Update:      pre-commit autoupdate                        ║
╠══════════════════════════════════════════════════════════════╣
║ DEPLOYMENT                                                   ║
║ ├─ Blue-Green:  Switch service selector                      ║
║ ├─ Canary:      nginx canary-weight annotation               ║
║ └─ Rollback:    kubectl rollout undo                         ║
╚══════════════════════════════════════════════════════════════╝
```

### 9.2 Makefile Example

```makefile
.PHONY: help lint test build deploy

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

lint: ## Run linting
	ruff check src/
	ruff format --check src/
	mypy src/ --ignore-missing-imports
	bandit -r src/ -c pyproject.toml

test: ## Run tests
	pytest tests/ -v --cov=src --cov-report=term-missing

build: ## Build Docker image
	docker build -t vitruviano:latest .

deploy: ## Deploy to Kubernetes
	kubectl apply -f kubernetes/

clean: ## Clean build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	rm -rf .coverage htmlcov/
```

---

*Last Updated: 2026-01-19 | Version: 1.0.0*
