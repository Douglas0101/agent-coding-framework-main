---
name: agentic-reporting
description: Skill para geração de laudos médicos estruturados usando LLMs open-source
  (Ollama/Llama3) e Engenharia de Prompt.
metadata:
  version: 1.0
---

# ✍️ Agentic Reporting Skill

## 1. Objetivo
Transformar dados brutos (Probabilidades JSON + Contexto RAG) em um laudo radiológico profissional e humanizado.

## 2. Engenharia de Prompt (Medical Persona)
O prompt deve impor uma "Persona" rígida para evitar alucinações e manter o tom profissional.

**Template:**
```text
Você é o Dr. Vitruvius, um radiologista sênior experiente.
Sua tarefa é escrever um laudo baseando-se APENAS nos dados fornecidos.

DADOS DA IMAGEM:
{findings_json}

CONTEXTO CLÍNICO (GUIDELINES):
{rag_context}

INSTRUÇÕES:
1. Comece com uma seção "Achados".
2. Use terminologia técnica (ex: "Opacidade em vidro fosco" em vez de "mancha branca").
3. Se a probabilidade for < 50%, relate como "Ausência de sinais significativos".
4. Adicione uma seção "Impressão Diagnóstica" no final.
5. Cite a guideline se relevante.
```

## 3. Integração Open Source
*   **Engine:** **Ollama** (Servidor Local).
*   **Model:** `llama3` ou `mistral` (7B quantized).
*   **Interface:** `langchain_community.llms.Ollama`.

## 4. Validação (Self-Consistency)
O agente deve ter um loop de revisão:
1.  Gera Laudo.
2.  Agente "Crítico" lê o laudo e compara com o JSON original.
3.  Se houver discrepância (ex: JSON diz "Sem Nódulo" e Texto diz "Nódulo presente"), regenera.
