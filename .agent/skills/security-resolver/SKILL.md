---
name: security-resolver
description: Autonomously resolves vulnerabilities identified by the vulnerability
  scanner and saved in PostgreSQL using an LLM.
metadata:
  version: 1.0
---

# 🛡️ Security Resolver Skill

This skill acts as the Semantic Solver Node for the Autonomous Swarm. It connects to the PostgreSQL database, retrieves OPEN vulnerabilities with HIGH or CRITICAL severity, and uses a local LLM API (Ollama) directly to generate code patches to remediate them.

It utilizes a pure Python orchestration flow to handle:
1.  **Triage**: Fetching and prioritizing vulnerabilities.
2.  **Solve**: Generating a patch diff for the target finding via native HTTP calls.
3.  **Verify**: Ensuring the patch parses correctly and passes basic linting before being proposed.
