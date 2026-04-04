# Core Specifications

This directory contains the domain-agnostic Core specifications for the Agent Orchestration Framework.

## Structure

```
specs/core/
├── orchestration-contract.yaml   # Core orchestration interfaces and protocols
├── README.md                    # This file
```

## Core Contract

The Core defines the **grammatical layer** of orchestration — the protocols, interfaces, and invariants that all Domain Packs must conform to. It does NOT contain domain-specific logic.

### Key Components

1. **Orchestration Contract** — Interfaces for Agent, Orchestrator, Gate, Evidence
2. **Protocol Definitions** — Verifier, Synthesizer, Handoff, Evidence
3. **Invariant Enforcement** — Constitutional rules that all packs must follow

## Constitutional Invariants

| ID | Statement | Enforcement |
|----|-----------|-------------|
| INV-001 | Core remains domain-agnostic | Static analysis |
| INV-002 | Domain capabilities use DomainPack contract | Runtime exception |
| INV-003 | Evidence Trail is immutable and cross-domain | Cryptographic verification |
| INV-004 | Handoff Contracts are backward-compatible | CI validation |
| INV-005 | Verifier/Synthesizer are Core protocols | Interface segregation |
| INV-006 | No raw sensitive data in Core | Static analysis |
| INV-007 | Public contracts sanitized, implementations private | Release governance |

## Usage

The Core contract is used by:
- Domain Packs to validate compliance
- CI/CD pipelines for constitutional enforcement
- Documentation for architecting new domains

## Versioning

The Core contract follows semantic versioning:
- **Major:** Breaking changes to interfaces or protocols
- **Minor:** New capabilities, backward-compatible extensions
- **Patch:** Documentation, clarifications

All Core changes are governed by the Constitution (`docs/CONSTITUTION_emendada.md`).