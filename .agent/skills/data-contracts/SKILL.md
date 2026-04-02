---
name: data-contracts
description: Contratos de dados para qualidade e governança de ML pipelines
---

# Data Contracts Skill

## Objetivo

Definir e validar contratos de dados entre produtores e consumidores, garantindo qualidade, schema evolution e SLAs para pipelines ML.

---

## Conceitos

### Data Contract

Acordo formal entre produtor e consumidor de dados especificando:
- **Schema**: Estrutura e tipos
- **Quality**: Regras de validação
- **SLA**: Freshness e availability
- **Ownership**: Responsabilidades

---

## Schema Definition

### YAML Format

```yaml
# contracts/patient_features.yaml
contract:
  name: "patient_features"
  version: "1.0.0"
  description: "Features de pacientes para modelo de classificação"

owner:
  team: "ml-platform"
  contact: "ml-team@example.com"

schema:
  type: "object"
  properties:
    patient_id:
      type: "string"
      format: "uuid"
      pii: true

    age:
      type: "integer"
      minimum: 0
      maximum: 120

    bmi:
      type: "number"
      minimum: 10.0
      maximum: 60.0
      nullable: true

    diagnosis_date:
      type: "string"
      format: "date"

    risk_score:
      type: "number"
      minimum: 0.0
      maximum: 1.0

  required:
    - patient_id
    - age
    - diagnosis_date

quality:
  rules:
    - name: "no_future_dates"
      expression: "diagnosis_date <= today()"
      severity: "error"

    - name: "valid_age_range"
      expression: "age >= 0 AND age <= 120"
      severity: "error"

    - name: "bmi_completeness"
      expression: "count(bmi) / total_rows >= 0.95"
      severity: "warning"

sla:
  freshness:
    max_age: "24h"

  availability:
    target: 0.999

  volume:
    expected_rows_per_day: 1000
    tolerance: 0.2  # ±20%
```

---

## Validação com Great Expectations

```python
import great_expectations as gx

def create_expectations_from_contract(contract: dict):
    """Converte contrato para Great Expectations."""

    context = gx.get_context()
    suite = context.add_expectation_suite("patient_features")

    for prop, spec in contract["schema"]["properties"].items():
        # Type validation
        if spec["type"] == "integer":
            suite.add_expectation(
                gx.expectations.ExpectColumnValuesToBeOfType(
                    column=prop,
                    type_="int64"
                )
            )

        # Range validation
        if "minimum" in spec:
            suite.add_expectation(
                gx.expectations.ExpectColumnValuesToBeBetween(
                    column=prop,
                    min_value=spec.get("minimum"),
                    max_value=spec.get("maximum"),
                )
            )

        # Nullability
        if prop in contract["schema"]["required"]:
            suite.add_expectation(
                gx.expectations.ExpectColumnValuesToNotBeNull(column=prop)
            )

    return suite
```

---

## Pydantic Models

```python
from pydantic import BaseModel, Field, field_validator
from datetime import date
from uuid import UUID


class PatientFeatures(BaseModel):
    """Schema de features de paciente."""

    patient_id: UUID
    age: int = Field(ge=0, le=120)
    bmi: float | None = Field(default=None, ge=10.0, le=60.0)
    diagnosis_date: date
    risk_score: float = Field(ge=0.0, le=1.0)

    @field_validator("diagnosis_date")
    @classmethod
    def validate_not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("diagnosis_date cannot be in the future")
        return v

    class Config:
        extra = "forbid"  # Reject unknown fields
```

---

## Schema Evolution

### Versioning Rules

| Change Type | Version Bump | Backward Compatible |
|-------------|--------------|---------------------|
| Add optional field | MINOR | ✅ Yes |
| Add required field | MAJOR | ❌ No |
| Remove field | MAJOR | ❌ No |
| Change type | MAJOR | ❌ No |
| Rename field | MAJOR | ❌ No |
| Add enum value | MINOR | ✅ Yes |
| Remove enum value | MAJOR | ❌ No |

### Migration Example

```yaml
# contracts/patient_features_v2.yaml
contract:
  name: "patient_features"
  version: "2.0.0"  # MAJOR bump
  previous_version: "1.0.0"

migration:
  breaking_changes:
    - type: "field_added_required"
      field: "smoking_status"
      migration: "Set default to 'unknown'"

  backward_compatible:
    - type: "field_added_optional"
      field: "exercise_frequency"
```

---

## Data Quality Rules

### Common Rules

```yaml
quality_rules:
  completeness:
    - column: "*"
      rule: "null_rate < 0.05"
      severity: "error"

  uniqueness:
    - columns: ["patient_id"]
      rule: "is_unique"
      severity: "error"

  consistency:
    - rule: "diagnosis_date >= birth_date"
      severity: "error"

  timeliness:
    - column: "updated_at"
      rule: "max(updated_at) > now() - interval '24 hours'"
      severity: "warning"

  accuracy:
    - column: "age"
      rule: "age == date_diff(today, birth_date, 'year')"
      severity: "warning"
```

---

## SLA Monitoring

```python
from datetime import datetime, timedelta

def check_data_sla(contract: dict, last_update: datetime) -> dict:
    """Verifica SLAs de dados."""

    sla = contract["sla"]
    now = datetime.now()

    # Freshness check
    max_age = parse_duration(sla["freshness"]["max_age"])  # e.g., "24h"
    age = now - last_update
    freshness_ok = age <= max_age

    return {
        "freshness": {
            "ok": freshness_ok,
            "age_hours": age.total_seconds() / 3600,
            "max_age_hours": max_age.total_seconds() / 3600,
        },
        "timestamp": now.isoformat(),
    }
```

---

## CI/CD Integration

```yaml
# .github/workflows/data-contracts.yml
name: Data Contract Validation

on:
  pull_request:
    paths:
      - 'contracts/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Validate Contract Schema
        run: |
          pip install pyyaml jsonschema
          python scripts/validate_contracts.py contracts/

      - name: Check Breaking Changes
        run: |
          python scripts/check_breaking_changes.py \
            --old contracts/patient_features.yaml \
            --new contracts/patient_features_v2.yaml
```

---

## Comandos

```bash
# Validar contrato
python .agent/skills/data-contracts/scripts/validate.py \
    contracts/patient_features.yaml

# Gerar Pydantic model
python .agent/skills/data-contracts/scripts/generate_model.py \
    --contract contracts/patient_features.yaml \
    --output src/domain/models/patient.py

# Verificar breaking changes
python .agent/skills/data-contracts/scripts/check_compat.py \
    --old v1.0.0 --new v2.0.0

# Validar dados contra contrato
python .agent/skills/data-contracts/scripts/validate_data.py \
    --contract contracts/patient_features.yaml \
    --data data/patients.parquet
```

---

## Métricas

| Métrica | Target | Verificação |
|---------|--------|-------------|
| Contract Coverage | 100% datasets | Audit |
| Schema Compliance | 100% | CI validation |
| SLA Violations | < 1/month | Monitoring |
| Breaking Changes | 0 unannounced | PR review |
