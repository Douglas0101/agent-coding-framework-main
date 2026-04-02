---
name: security-audit
description: Auditoria de segurança SAST com Bandit e análise de vulnerabilidades
---

# Security Audit Skill

## Objetivo

Executar análise estática de segurança (SAST) para identificar vulnerabilidades comuns no código Python, classificar por severidade e fornecer recomendações de correção.

## Ferramentas Utilizadas

| Ferramenta | Propósito |
|------------|-----------|
| **Bandit** | SAST para Python - detecta vulnerabilidades comuns |
| **Ruff S*** | Regras de segurança (flake8-bandit) integradas |

## Vulnerabilidades Detectadas

### Alta Severidade (CRITICAL)
- `B102` - exec() usado
- `B301` - pickle inseguro
- `B303` - MD5/SHA1 para criptografia
- `B608` - SQL injection

### Média Severidade (WARNING)
- `B101` - assert usado (removido em produção)
- `B110` - try/except com pass
- `B501` - requests sem verificação SSL
- `B603` - subprocess com shell=True

### Baixa Severidade (INFO)
- `B104` - bind em 0.0.0.0
- `B311` - random inseguro para crypto

## Comandos

### Scan Básico

```bash
# Scan de todo o src/
bandit -r src/ -ll

# Scan com output JSON
bandit -r src/ -f json -o bandit_report.json

# Scan específico de arquivos críticos
bandit -r src/security/ src/data/ingest/ -ll
```

### Via Script

```bash
python .agent/skills/security-audit/scripts/bandit_scan.py --report
python .agent/skills/security-audit/scripts/bandit_scan.py --critical-only
python .agent/skills/security-audit/scripts/bandit_scan.py --json
```

## Configuração

Configuração em `.bandit` e `pyproject.toml`:

```toml
# pyproject.toml
[tool.bandit]
exclude_dirs = ["tests", "venv", ".venv"]
skips = ["B101"]  # assert permitido em testes
```

## Workflow de Uso

1. **Pré-commit**: Inclua scan de arquivos modificados
2. **CI/CD**: Scan completo com `bandit -r src/ -ll`
3. **Release**: Scan com severidade mínima HIGH

## Áreas Críticas do Projeto

Para este projeto médico (HIPAA), foque em:

```bash
# Dados sensíveis
bandit -r src/data/ingest/ src/data/labels.py src/data/pseudonym.py -ll

# Criptografia
bandit -r src/security/ -ll

# API/Serving
bandit -r src/serving/ -ll
```

## Tratamento de Falsos Positivos

Use `# nosec` com justificativa:

```python
# Falso positivo - XML vem de fonte confiável interna
tree = ET.parse(config_file)  # nosec B314 - internal config only
```

## Métricas de Sucesso

- Zero vulnerabilidades HIGH/CRITICAL em CI
- Falsos positivos documentados com `# nosec`
- Áreas de código sensível auditadas semanalmente
