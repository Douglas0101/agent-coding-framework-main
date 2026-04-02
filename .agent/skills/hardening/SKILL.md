---
name: hardening
description: Hardening de segurança com melhores práticas OWASP e CIS
---

# Security Hardening Skill

## Objetivo

Aplicar melhores práticas de hardening de segurança baseadas em padrões OWASP, CIS Benchmarks e requisitos HIPAA para sistemas de saúde.

## Checklist de Hardening

### 1. Dependências

- [ ] Remover dependências não utilizadas
- [ ] Fixar versões exatas em requirements.txt
- [ ] Habilitar Dependabot/Renovate
- [ ] CVE scan em CI

### 2. Configuração

- [ ] DEBUG=False em produção
- [ ] Secrets em variáveis de ambiente
- [ ] HTTPS obrigatório
- [ ] Headers de segurança configurados

### 3. Autenticação

- [ ] Senhas com hash forte (argon2)
- [ ] Rate limiting em login
- [ ] Session timeout configurado
- [ ] 2FA disponível

### 4. Autorização

- [ ] RBAC implementado
- [ ] Least privilege principle
- [ ] Verificação de ownership

### 5. Dados

- [ ] Encryption at rest
- [ ] Encryption in transit (TLS 1.3)
- [ ] Data masking em logs
- [ ] Backup criptografado

### 6. Logging

- [ ] Eventos de segurança logados
- [ ] Logs protegidos contra tampering
- [ ] Alertas para anomalias
- [ ] Retenção conforme compliance

## Headers de Segurança

### FastAPI Middleware

```python
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

app = FastAPI()
app.add_middleware(SecurityHeadersMiddleware)
```

## Configuração Segura

### Environment Variables

```bash
# .env.example (NÃO commitar valores reais)
DEBUG=false
SECRET_KEY=<generate-with-secrets-module>
DATABASE_URL=postgresql://...
PATIENT_HMAC_KEY=<32-bytes-hex>
ALLOWED_HOSTS=["api.example.com"]
```

### Secrets Management

```python
import os
from functools import lru_cache

@lru_cache
def get_secret(name: str) -> str:
    """Obtém secret de variável de ambiente."""
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"Required secret {name} not set")
    return value

# Uso
hmac_key = get_secret("PATIENT_HMAC_KEY")
```

## Rate Limiting

```python
from fastapi import FastAPI
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter

@app.post("/api/login")
@limiter.limit("5/minute")
async def login(request: Request):
    ...
```

## Input Validation

```python
from pydantic import BaseModel, Field, validator
import re

class PatientInput(BaseModel):
    patient_id: str = Field(..., min_length=8, max_length=64)
    age: int = Field(..., ge=0, le=150)

    @validator("patient_id")
    def validate_id(cls, v):
        if not re.match(r"^[A-Z0-9-]+$", v):
            raise ValueError("Invalid patient ID format")
        return v
```

## Audit Logging

```python
import logging
from datetime import datetime, timezone

security_logger = logging.getLogger("security")

def log_security_event(
    event_type: str,
    user_id: str,
    resource: str,
    action: str,
    success: bool,
    details: dict | None = None,
) -> None:
    """Log security event for audit trail."""
    security_logger.info(
        "SecurityEvent",
        extra={
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "resource": resource,
            "action": action,
            "success": success,
            "details": details or {},
        },
    )
```

## HIPAA Specific

### PHI Data Handling

```python
from src.security.crypto import encrypt_phi, mask_patient_id

class PatientRecord:
    def __init__(self, patient_id: str, diagnosis: str):
        self._patient_id = encrypt_phi(patient_id)
        self._diagnosis = encrypt_phi(diagnosis)

    def get_masked_id(self) -> str:
        """Retorna ID mascarado para logging."""
        return mask_patient_id(self._patient_id)
```

### Minimum Necessary Access

```python
from enum import Enum, auto

class AccessLevel(Enum):
    READ = auto()
    WRITE = auto()
    ADMIN = auto()

def require_access(level: AccessLevel):
    """Decorator para verificar nível de acesso."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            user = get_current_user(request)
            if not has_access(user, level):
                raise HTTPException(403, "Insufficient permissions")
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator
```

## Verificação de Hardening

```bash
# Via script
python .agent/skills/hardening/scripts/hardening_check.py --full



# Checklist manual
.agent/skills/hardening/CHECKLIST.md
```

## Métricas de Sucesso

- Todos os headers de segurança implementados
- Rate limiting em endpoints críticos
- Audit logging completo
- Zero secrets em código
- 100% HIPAA checklist
