---
name: compliance-checker
description: Verificação de compliance HIPAA e SOC2 para sistemas de saúde
---

# Compliance Checker Skill

## Objetivo

Verificar conformidade com regulamentações HIPAA (Health Insurance Portability and Accountability Act) e SOC2 para sistemas que processam dados médicos.

## Frameworks de Compliance

### HIPAA (Obrigatório para Healthcare)

| Regra | Descrição |
|-------|-----------|
| **Privacy Rule** | Proteção de PHI |
| **Security Rule** | Salvaguardas técnicas |
| **Breach Notification** | Notificação de incidentes |
| **Enforcement Rule** | Penalidades |

### SOC2 (Recomendado)

| Trust Principle | Descrição |
|-----------------|-----------|
| **Security** | Proteção contra acesso não autorizado |
| **Availability** | Sistema disponível para operação |
| **Processing Integrity** | Processamento completo e preciso |
| **Confidentiality** | Dados confidenciais protegidos |
| **Privacy** | Dados pessoais coletados/usados conforme política |

## Checklist HIPAA

### Administrative Safeguards (§164.308)

- [ ] Security Officer designado
- [ ] Risk Assessment documentado
- [ ] Workforce training
- [ ] Contingency plan (backup/recovery)
- [ ] Incident response procedures

### Physical Safeguards (§164.310)

- [ ] Facility access controls
- [ ] Workstation security
- [ ] Device disposal procedures
- [ ] Data backup procedures

### Technical Safeguards (§164.312)

#### Access Control (§164.312(a))
- [ ] Unique user identification
- [ ] Emergency access procedure
- [ ] Automatic logoff
- [ ] Encryption/decryption

#### Audit Controls (§164.312(b))
- [ ] Hardware audit mechanisms
- [ ] Software audit mechanisms
- [ ] Procedural controls

#### Integrity (§164.312(c))
- [ ] Authentication of PHI
- [ ] Mechanism to verify PHI integrity

#### Transmission Security (§164.312(e))
- [ ] Integrity controls
- [ ] Encryption

## Verificação Automática

### Código

```python
# Verificar uso de criptografia para PHI
grep -r "encrypt" src/security/
grep -r "PATIENT_HMAC" src/

# Verificar audit logging
grep -r "audit_log\|security_log" src/

# Verificar autenticação
grep -r "@require_auth\|authenticate" src/serving/
```

### Configuração

```bash
# Verificar variáveis de ambiente
env | grep -E "(KEY|SECRET|PASSWORD)" | wc -l

# Verificar TLS
openssl s_client -connect api.example.com:443 -tls1_3

# Verificar headers
curl -I https://api.example.com/health
```

### Via Script

```bash
python .agent/skills/compliance-checker/scripts/compliance_check.py --hipaa
python .agent/skills/compliance-checker/scripts/compliance_check.py --soc2
python .agent/skills/compliance-checker/scripts/compliance_check.py --report
```

## Controles Implementados no Projeto

### Criptografia (✅ Implementado)

```
src/security/crypto.py      # AES-256-GCM, SHA-256
src/security/key_manager.py # Gerenciamento de chaves
src/security/rust_crypto/   # Crypto acelerado
```

### Pseudonimização (✅ Implementado)

```
src/data/pseudonym.py       # HMAC-SHA256 para IDs
src/data/labels.py          # Processamento anonimizado
```

### Audit Trail (✅ Implementado)

```
src/security/audit.py       # Blockchain-style audit
src/telemetry/              # Logging estruturado
```

### Integridade (✅ Implementado)

```
src/security/integrity.py   # Verificação de integridade
scripts/validate_audit_chain.py  # Validação de chain
```

## Documentação Necessária

### Business Associate Agreement (BAA)
- Contrato com fornecedores que acessam PHI
- Cláusulas de segurança e breach notification

### Risk Assessment
- Identificação de ameaças
- Análise de impacto
- Plano de mitigação

### Incident Response Plan
- Detecção de incidentes
- Procedimentos de resposta
- Notificação (72h para breach)

## Relatório de Compliance

```markdown
# Compliance Status Report

## HIPAA Technical Safeguards

| Control | Status | Evidence |
|---------|--------|----------|
| Access Control | ✅ | src/security/crypto.py |
| Audit Controls | ✅ | src/security/audit.py |
| Integrity | ✅ | src/security/integrity.py |
| Transmission | ✅ | TLS 1.3 configured |

## Gaps Identified

1. [ ] Emergency access procedure documentation
2. [ ] Annual risk assessment update

## Remediation Timeline

| Gap | Owner | Due Date |
|-----|-------|----------|
| Emergency access doc | Security | 2026-02-01 |
| Risk assessment | Compliance | 2026-03-01 |
```

## Métricas de Sucesso

- 100% dos controles técnicos implementados
- Documentação de compliance atualizada
- Risk assessment anual
- Zero findings em auditorias
- Breach notification process testado
