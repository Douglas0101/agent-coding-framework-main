---
name: dependency-audit
description: Auditoria de dependências para CVEs e pacotes outdated
---

# Dependency Audit Skill

## Objetivo

Auditar dependências do projeto para identificar CVEs conhecidas, pacotes desatualizados e licenças incompatíveis.

## Ferramentas Utilizadas

| Ferramenta | Propósito |
|------------|-----------|
| **safety** | Scan de CVEs em dependências |
| **pip-audit** | Auditoria de vulnerabilidades (OSV database) |
| **pip list --outdated** | Pacotes desatualizados |

## Comandos

### Scan de Vulnerabilidades

```bash
# Com Safety
safety check -r requirements.txt

# Com pip-audit
pip-audit

# Output JSON
pip-audit --format json > vulnerabilities.json
```

### Pacotes Outdated

```bash
# Listar outdated
pip list --outdated --format=columns

# Formato JSON
pip list --outdated --format=json
```

### Via Script

```bash
python .agent/skills/dependency-audit/scripts/dep_audit.py --scan
python .agent/skills/dependency-audit/scripts/dep_audit.py --outdated
python .agent/skills/dependency-audit/scripts/dep_audit.py --report
```

## Dependências Críticas

### Segurança
```
cryptography>=41.0.7    # Criptografia
opacus>=1.4.0           # Differential Privacy
```

### ML Core
```
torch==2.1.2            # Deep Learning
torchvision==0.16.2     # Vision models
scikit-learn==1.3.2     # ML utilities
```

### API/Serving
```
fastapi==0.109.0        # Web framework
uvicorn==0.27.0         # ASGI server
pydantic==2.6.0         # Validation
```

## Política de Atualizações

### Patch Updates (x.x.Y)
- Pode atualizar imediatamente
- Ex: 2.1.1 → 2.1.2

### Minor Updates (x.Y.0)
- Testar em staging primeiro
- Ex: 2.1.0 → 2.2.0

### Major Updates (Y.0.0)
- Requer análise de breaking changes
- Ex: 1.x → 2.0

## CVE Response

### Severidade CRITICAL
- **Response Time**: 24h
- **Action**: Patch imediato ou rollback

### Severidade HIGH
- **Response Time**: 7 dias
- **Action**: Sprint prioritário

### Severidade MEDIUM/LOW
- **Response Time**: 30 dias
- **Action**: Próximo release

## Integração CI

```yaml
- name: Dependency Audit
  run: |
    pip-audit --strict --desc
    safety check -r requirements.txt
```

## Licenças Compatíveis

✅ **Permitidas**:
- MIT
- Apache 2.0
- BSD (2/3 clause)
- PSF

⚠️ **Revisar**:
- LGPL
- MPL

❌ **Bloqueadas**:
- GPL (viral)
- AGPL

## Métricas de Sucesso

- Zero CVEs HIGH/CRITICAL em produção
- Dependências críticas com patches < 30 dias
- Licenças compatíveis verificadas
