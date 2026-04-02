---
name: hexagonal-arch
description: Validação de arquitetura hexagonal (Ports & Adapters)
---

# Hexagonal Architecture Skill

## Objetivo

Validar e manter arquitetura hexagonal (Ports & Adapters), garantindo separação clara entre domínio, aplicação e infraestrutura.

---

## Princípios

```
                    ┌─────────────────────────────────────┐
                    │         INFRASTRUCTURE              │
                    │  (Adapters: DB, API, Files, etc.)   │
                    │                                     │
                    │    ┌─────────────────────────────┐  │
                    │    │        APPLICATION          │  │
                    │    │   (Use Cases, Services)     │  │
                    │    │                             │  │
                    │    │    ┌─────────────────────┐  │  │
                    │    │    │       DOMAIN        │  │  │
                    │    │    │ (Entities, Values,  │  │  │
                    │    │    │  Domain Services)   │  │  │
                    │    │    └─────────────────────┘  │  │
                    │    │                             │  │
                    │    └─────────────────────────────┘  │
                    │                                     │
                    └─────────────────────────────────────┘
```

---

## Regras de Dependência

### Allowed Dependencies

```
Domain      → (nenhuma dependência externa)
Application → Domain
Infrastructure → Application, Domain
```

### Forbidden Dependencies

```
Domain      ✗→ Application, Infrastructure
Application ✗→ Infrastructure
```

---

## Estrutura de Diretórios

```
src/
├── domain/                 # Core business logic
│   ├── entities/           # Domain entities (Patient, Model, etc.)
│   ├── value_objects/      # Immutable value types
│   ├── services/           # Domain services
│   ├── events/             # Domain events
│   └── exceptions/         # Domain-specific exceptions
│
├── application/            # Use cases and orchestration
│   ├── ports/              # Interfaces (Ports)
│   │   ├── inbound/        # Driving ports (API contracts)
│   │   └── outbound/       # Driven ports (Repository interfaces)
│   ├── services/           # Application services
│   └── dto/                # Data Transfer Objects
│
└── infrastructure/         # External concerns (Adapters)
    ├── adapters/
    │   ├── inbound/        # Controllers, CLI handlers
    │   └── outbound/       # Database, external APIs
    ├── config/             # Configuration
    └── persistence/        # Database implementations
```

---

## Ports (Interfaces)

### Inbound Port (Driving)

```python
# application/ports/inbound/inference_port.py
from abc import ABC, abstractmethod
from domain.entities import PredictionRequest, PredictionResult

class InferencePort(ABC):
    """Port for inference operations."""

    @abstractmethod
    def predict(self, request: PredictionRequest) -> PredictionResult:
        """Execute model prediction."""
        pass

    @abstractmethod
    def batch_predict(self, requests: list[PredictionRequest]) -> list[PredictionResult]:
        """Execute batch predictions."""
        pass
```

### Outbound Port (Driven)

```python
# application/ports/outbound/model_repository.py
from abc import ABC, abstractmethod
from domain.entities import Model

class ModelRepository(ABC):
    """Port for model persistence."""

    @abstractmethod
    def load(self, model_id: str) -> Model:
        """Load model by ID."""
        pass

    @abstractmethod
    def save(self, model: Model) -> str:
        """Save model and return ID."""
        pass
```

---

## Adapters

### Inbound Adapter (REST API)

```python
# infrastructure/adapters/inbound/rest_controller.py
from fastapi import APIRouter
from application.ports.inbound import InferencePort
from application.dto import PredictionRequestDTO, PredictionResponseDTO

class InferenceController:
    def __init__(self, inference_service: InferencePort):
        self._service = inference_service
        self.router = APIRouter()
        self._register_routes()

    def _register_routes(self):
        @self.router.post("/predict")
        def predict(request: PredictionRequestDTO) -> PredictionResponseDTO:
            result = self._service.predict(request.to_domain())
            return PredictionResponseDTO.from_domain(result)
```

### Outbound Adapter (Database)

```python
# infrastructure/adapters/outbound/postgres_model_repository.py
from application.ports.outbound import ModelRepository
from domain.entities import Model

class PostgresModelRepository(ModelRepository):
    def __init__(self, connection_string: str):
        self._conn = connection_string

    def load(self, model_id: str) -> Model:
        # Implementation
        pass

    def save(self, model: Model) -> str:
        # Implementation
        pass
```

---

## Dependency Injection

```python
# infrastructure/config/container.py
from dependency_injector import containers, providers

class Container(containers.DeclarativeContainer):
    # Configuration
    config = providers.Configuration()

    # Repositories (Outbound Adapters)
    model_repository = providers.Singleton(
        PostgresModelRepository,
        connection_string=config.database.url,
    )

    # Application Services
    inference_service = providers.Factory(
        InferenceService,
        model_repository=model_repository,
    )

    # Controllers (Inbound Adapters)
    inference_controller = providers.Factory(
        InferenceController,
        inference_service=inference_service,
    )
```

---

## Validação de Dependências

### Import Linter Configuration

```toml
# pyproject.toml
[tool.importlinter]
root_packages = ["src"]

[[tool.importlinter.contracts]]
name = "Domain independence"
type = "independence"
packages = ["src.domain"]

[[tool.importlinter.contracts]]
name = "Layered architecture"
type = "layers"
layers = [
    "src.infrastructure",
    "src.application",
    "src.domain",
]
```

```bash
# Verificar arquitetura
pip install import-linter
lint-imports
```

---

## Checklist de Validação

### Domain Layer
- [ ] Sem imports de frameworks (FastAPI, SQLAlchemy)
- [ ] Sem imports de infraestrutura
- [ ] Entidades são imutáveis ou controladas
- [ ] Exceções são domain-specific

### Application Layer
- [ ] Apenas interfaces (ports), não implementações
- [ ] Use cases são stateless
- [ ] DTOs para comunicação externa
- [ ] Orquestra domain objects

### Infrastructure Layer
- [ ] Implementa ports definidos em application
- [ ] Dependency injection configurado
- [ ] Configuration externa (env vars)
- [ ] Adapters são substituíveis

---

## Métricas

| Métrica | Target | Ferramenta |
|---------|--------|------------|
| Dependency violations | 0 | import-linter |
| Port coverage | 100% | Manual review |
| Domain purity | No external imports | AST analysis |
| Adapter testability | Mockable | DI container |
