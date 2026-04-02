# Agent Skills Ecosystem - Enterprise Edition

Ecossistema de skills para automação de tarefas de engenharia de software, MLOps e segurança.

## Arquitetura (8 Layers)

```
┌─────────────────────────────────────────────────────────────┐
│  🔬 Layer 8: Research    │  experiment-tracking, ablation  │
├─────────────────────────────────────────────────────────────┤
│  📊 Layer 7: MLOps       │  model-lineage, data-contracts  │
├─────────────────────────────────────────────────────────────┤
│  🔭 Layer 6: Observability│  slo-sli-tracking              │
├─────────────────────────────────────────────────────────────┤
│  🏛️ Layer 5: Architecture │  hexagonal-arch                │
├─────────────────────────────────────────────────────────────┤
│  🔐 Layer 4: Security     │  threat-modeling, vulnerability│
├─────────────────────────────────────────────────────────────┤
│  🔧 Layer 3: Refactoring  │  dead-code, complexity         │
├─────────────────────────────────────────────────────────────┤
│  ⚡ Layer 2: Performance  │  gpu-profiler, coverage        │
├─────────────────────────────────────────────────────────────┤
│  🏗️ Layer 1: Foundation   │  code-quality, type-safety     │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Basic quality check
make skill-all

# Enterprise analysis (DORA, SLO, GPU, Lineage)
make skill-enterprise

# Code health score
make skill-health
```

## Skills Disponíveis

### Foundation Layer
| Skill | Descrição |
|-------|-----------|
| `code-quality` | Ruff + gates avancados de algoritmo, seguranca e engenharia |
| `security-audit` | Bandit SAST |
| `type-safety` | MyPy strict mode |
| `documentation-as-code` | ADRs, OpenAPI, docstrings |
| `semantic-versioning` | Conventional commits |

### Performance Layer
| Skill | Descrição |
|-------|-----------|
| `performance-profiling` | pytest-benchmark |
| `test-coverage` | Coverage analysis |
| `gpu-profiler` | CUDA/torch profiling |

### Architecture Layer
| Skill | Descrição |
|-------|-----------|
| `hexagonal-arch` | Ports & Adapters validation |
| `refactor-patterns` | Design patterns |
| `complexity-reduction` | McCabe, cognitive |

### Security Layer
| Skill | Descrição |
|-------|-----------|
| `vulnerability-scanner` | CVE, secrets |
| `threat-modeling` | STRIDE/DREAD |
| `compliance-checker` | HIPAA, SOC2 |

### MLOps Layer
| Skill | Descrição |
|-------|-----------|
| `model-lineage` | Reproducibility tracking |
| `data-contracts` | Schema validation |
| `experiment-tracking` | MLflow patterns |

### Observability Layer
| Skill | Descrição |
|-------|-----------|
| `slo-sli-tracking` | Error budgets, burn rate |

## Workflows

| Workflow | Comando |
|----------|---------|
| `/full-quality-check` | Verificação completa |
| `/security-hardening` | Hardening OWASP/HIPAA |
| `/performance-optimization` | Profiling |
| `/refactor-session` | Refatoração guiada |

## Métricas Enterprise

| Categoria | Métrica | Target |
|-----------|---------|--------|
| DORA | Lead Time | < 1 day |
| DORA | Deployment Frequency | Daily |
| Code | Health Score | > 80 |
| SRE | Availability | 99.9% |
| ML | Reproducibility | 100% |
