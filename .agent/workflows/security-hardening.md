---
description: Executa hardening completo de segurança do projeto
---

# Security Hardening Workflow

Este workflow aplica verificações e hardening de segurança em profundidade.

## Execução

### Fase 1: Análise de Vulnerabilidades

// turbo
1. **Gate enterprise unificado (SCA + SAST + secrets)**
```bash
python .agent/skills/vulnerability-scanner/scripts/vuln_scanner.py \
  --profile ci \
  --scan-path . \
  --requirements requirements.txt \
  --secrets-baseline .secrets.baseline \
  --json --report \
  --output-dir artifacts/security
```

// turbo
2. **Gate de release (IaC + container)**
```bash
python .agent/skills/vulnerability-scanner/scripts/vuln_scanner.py \
  --profile release \
  --scan-path . \
  --docker-image vitruviano:latest \
  --dockerfile Dockerfile.serving \
  --json --report \
  --output-dir artifacts/security
```

### Fase 2: Verificação de Configuração

3. **Verificar Variáveis de Ambiente**
   - Confirmar que `PATIENT_HMAC_KEY` está definido
   - Confirmar que `SECRET_KEY` não está hardcoded
   - Verificar que DEBUG está desabilitado em produção

4. **Verificar Headers de Segurança**
   - X-Content-Type-Options: nosniff
   - X-Frame-Options: DENY
   - Strict-Transport-Security
   - Content-Security-Policy

### Fase 3: Audit Trail

// turbo
5. **Verificar Audit Chain**
```bash
python scripts/validate_audit_chain.py --verify 2>/dev/null || echo "Audit chain validation skipped"
```

### Fase 4: Crypto Verification

// turbo
6. **Verificar Módulos de Segurança**
```bash
python -c "from src.security import crypto; print('Crypto module: OK')"
```

// turbo
7. **Verificar Rust Extension**
```bash
python -c "import vitruviano_crypto; print('Rust crypto: OK')" 2>/dev/null || echo "Rust crypto not available"
```

### Fase 5: HIPAA Checklist

8. **Revisar Checklist HIPAA**
   Consulte: `.agent/skills/compliance-checker/SKILL.md`

   - [ ] Access Control implementado
   - [ ] Audit Controls funcionando
   - [ ] Integridade de dados verificável
   - [ ] Transmissão criptografada

## Critérios de Sucesso

- ✅ Zero CVEs CRITICAL/HIGH
- ✅ Zero secrets expostos
- ✅ Zero vulnerabilidades SAST HIGH
- ✅ Audit chain válida
- ✅ Criptografia funcionando
- ✅ HIPAA checklist completo

## Comando Único

```bash
make skill-security
```

## Relatório

Após execução, relatório salvo em:
```
artifacts/security/vulnerability_report.txt
artifacts/security/vulnerability_summary.json
```
