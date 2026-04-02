---
name: slo-sli-tracking
description: Service Level Objectives e Indicators para ML Systems
---

# SLO/SLI Tracking Skill

## Objetivo

Definir e monitorar Service Level Objectives (SLOs) e Service Level Indicators (SLIs) para sistemas ML em produção, seguindo práticas SRE do Google.

---

## Conceitos

### SLI (Service Level Indicator)
Métrica quantitativa do comportamento do serviço.

### SLO (Service Level Objective)
Target para SLIs (ex: "99.9% das requisições < 100ms").

### Error Budget
Margem para falha: `Error Budget = 1 - SLO Target`

---

## SLIs para ML Systems

### 1. Availability SLI

```python
# Fórmula
availability = successful_requests / total_requests * 100

# Target típico
SLO: 99.9% availability (8.76h downtime/ano)
```

### 2. Latency SLI

```python
# Percentis
p50_latency < 50ms   # Mediana
p95_latency < 200ms  # 95th percentile
p99_latency < 500ms  # 99th percentile

# SLO típico para inference
SLO: 95% of requests < 100ms
```

### 3. ML-Specific SLIs

```python
# Model Quality
model_auc > 0.80
model_calibration_error < 0.05

# Data Freshness
feature_staleness < 1 hour
model_age < 30 days

# Throughput
inference_throughput > 1000 req/s
training_throughput > 100 samples/s
```

---

## Error Budget

### Cálculo

```python
# Se SLO = 99.9%
error_budget = 1 - 0.999 = 0.1%

# Por mês (30 dias)
monthly_budget_minutes = 30 * 24 * 60 * 0.001 = 43.2 minutos

# Burn rate
burn_rate = current_error_rate / error_budget
# burn_rate > 1 = consumindo budget mais rápido que o permitido
```

### Alertas Baseados em Burn Rate

| Burn Rate | Budget Consumido em | Severidade |
|-----------|---------------------|------------|
| 14.4x | 1 hora | Critical |
| 6x | 4 horas | High |
| 3x | 1 dia | Medium |
| 1x | 30 dias | Low |

---

## Configuração

### slo_config.yaml

```yaml
slos:
  - name: inference-availability
    type: availability
    target: 0.999
    window: 30d

  - name: inference-latency
    type: latency
    target: 0.95
    threshold_ms: 100
    window: 7d

  - name: model-quality
    type: threshold
    metric: auc
    target: 0.80
    window: 24h

  - name: data-freshness
    type: freshness
    max_age_hours: 1
    window: 24h

error_budget_policies:
  - if_remaining < 10%:
      action: freeze_deployments
  - if_remaining < 25%:
      action: require_extra_review
  - if_remaining < 50%:
      action: notify_oncall
```

---

## Script de Cálculo

```python
#!/usr/bin/env python3
"""SLO Calculator."""

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class SLOStatus:
    name: str
    target: float
    current: float
    remaining_budget_percent: float
    burn_rate: float

    @property
    def is_healthy(self) -> bool:
        return self.remaining_budget_percent > 25


def calculate_error_budget(
    target: float,
    current_success_rate: float,
    window_days: int,
) -> dict:
    """Calcula error budget restante."""

    error_budget = 1 - target
    current_error_rate = 1 - current_success_rate

    budget_used = current_error_rate / error_budget if error_budget > 0 else 1
    remaining = max(0, 1 - budget_used) * 100

    burn_rate = current_error_rate / (error_budget / window_days) if error_budget > 0 else float('inf')

    return {
        "error_budget_total": error_budget * 100,
        "budget_used_percent": budget_used * 100,
        "remaining_percent": remaining,
        "burn_rate": burn_rate,
        "projected_exhaustion_days": window_days / burn_rate if burn_rate > 0 else float('inf'),
    }
```

---

## Dashboards

### Grafana Panels

```json
{
  "panels": [
    {
      "title": "Availability SLO",
      "type": "gauge",
      "targets": [
        {
          "expr": "sum(rate(requests_success_total[30d])) / sum(rate(requests_total[30d]))"
        }
      ],
      "thresholds": [
        {"value": 99.9, "color": "green"},
        {"value": 99.5, "color": "yellow"},
        {"value": 99.0, "color": "red"}
      ]
    },
    {
      "title": "Error Budget Remaining",
      "type": "stat",
      "targets": [
        {
          "expr": "1 - (sum(rate(requests_errors_total[30d])) / 0.001)"
        }
      ]
    },
    {
      "title": "Burn Rate (6h)",
      "type": "timeseries",
      "targets": [
        {
          "expr": "sum(rate(errors_total[6h])) / sum(rate(requests_total[6h])) / 0.001"
        }
      ]
    }
  ]
}
```

---

## Prometheus Rules

```yaml
# prometheus_rules.yaml
groups:
  - name: slo_alerts
    rules:
      # Critical: 14.4x burn rate (1h budget consumption)
      - alert: SLOBurnRateCritical
        expr: |
          (
            sum(rate(http_requests_total{status=~"5.."}[5m]))
            / sum(rate(http_requests_total[5m]))
          ) > (14.4 * 0.001)
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "SLO burn rate critical - consuming error budget in 1 hour"

      # High: 6x burn rate (4h budget consumption)
      - alert: SLOBurnRateHigh
        expr: |
          (
            sum(rate(http_requests_total{status=~"5.."}[30m]))
            / sum(rate(http_requests_total[30m]))
          ) > (6 * 0.001)
        for: 15m
        labels:
          severity: warning
```

---

## Runbook

### Quando Error Budget < 25%

1. **Freeze deployments**: Sem mudanças até recuperar
2. **Priorize reliability**: Foque em bugs e estabilidade
3. **Post-mortem**: Analise incidentes recentes
4. **Ajuste SLOs**: Se necessário, revise targets

### Quando Error Budget Esgotado

1. **Incident mode**: Declare incidente
2. **All hands**: Mobilize equipe
3. **Rollback**: Reverta mudanças recentes
4. **Blameless review**: Analise root cause

---

## Métricas de Sucesso

| Métrica | Target | Verificação |
|---------|--------|-------------|
| SLO Coverage | 100% serviços | Config review |
| Error Budget > 50% | > 90% do tempo | Dashboard |
| Burn Rate < 1 | > 95% do tempo | Alerts |
| SLO Review | Quarterly | Calendar |
