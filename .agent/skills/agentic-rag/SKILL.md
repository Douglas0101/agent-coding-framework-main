---
name: agentic-rag
description: Skill para implementação de Retrieval-Augmented Generation (RAG) focado
  em diretrizes médicas usando ChromaDB e LangChain.
metadata:
  version: 1.0
---

# 📚 Clinical RAG Skill

## 1. Objetivo
Permitir que o sistema "justifique" seus diagnósticos consultando literatura médica confiável, em vez de alucinar.

## 2. Arquitetura RAG
1.  **Ingestão:**
    *   Fonte: PDFs de Guidelines (ACR, Fleischner Society, Artigos PubMed).
    *   Splitter: `RecursiveCharacterTextSplitter` (chunks de 500 tokens).
    *   Embedding: `sentence-transformers/all-MiniLM-L6-v2` (Local, HuggingFace).
2.  **Vector Store:**
    *   **ChromaDB** (Persistente no disco local `data/chroma_db`).
3.  **Retrieval:**
    *   Query: "Conduta para nódulo pulmonar sólido de 7mm em paciente fumante".
    *   Busca: Top-3 chunks mais similares.

## 3. Implementação Prática
```python
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# Setup
embedding_func = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
db = Chroma(persist_directory="./data/chroma_db", embedding_function=embedding_func)

# Query
docs = db.similarity_search("Nodule handling guidelines", k=3)
context = "\n".join([d.page_content for d in docs])
```

## 4. Integração Open Source
*   **Embeddings:** HuggingFace (Local).
*   **Database:** ChromaDB.
*   **Orchestrator:** LangChain.
