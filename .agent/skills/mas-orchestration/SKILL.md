---
name: mas-orchestration
description: Skill para desenhar e implementar o fluxo de controle de um Sistema Multiagente
  (MAS) usando LangGraph/LangChain.
metadata:
  version: 1.0
---

# 🤖 MAS Orchestration Skill

## 1. Objetivo
Transformar o Vitruviano de um conjunto de scripts isolados em um sistema coordenado onde um "Agente Central" delega tarefas para especialistas.

## 2. Padrão de Design: "Supervisor"
Usaremos o padrão **Supervisor** (ou *Router*):
1.  **State:** O estado global contém a `Image`, `Metadata`, e `DiagnosticResults` (dict vazio no início).
2.  **Nodes:**
    *   `Triage`: Verifica qualidade da imagem.
    *   `Specialist_A_Node`: Invoca EfficientNet-B3 (V5).
    *   `Specialist_B_Node`: Invoca EfficientNet-B3 (Struct).
    *   `Aggregator`: Junta os resultados.

## 3. Implementação (Pseudocódigo LangGraph)
```python
class AgentState(TypedDict):
    image_path: str
    findings: dict
    report: str

def triage_node(state):
    # Lógica de qualidade
    return {"status": "ok"}

def specialist_a_node(state):
    # Chama inferência do Grupo A
    probs = run_inference_a(state['image_path'])
    return {"findings": {"group_a": probs}}

# Graph Definition
workflow = StateGraph(AgentState)
workflow.add_node("triage", triage_node)
workflow.add_node("spec_a", specialist_a_node)
# ...
workflow.set_entry_point("triage")
```

## 4. Integração Open Source
*   **Biblioteca:** `langgraph`
*   **Execução:** Local Python process.
