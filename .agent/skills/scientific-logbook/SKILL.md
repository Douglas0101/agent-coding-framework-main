---
name: scientific-logbook
description: Skill para análise qualitativa de experimentos, transformando métricas
  brutas em narrativas científicas para o Diário de Bordo.
metadata:
  version: 1.0
---

# 📔 Scientific Logbook Skill

## 1. Objetivo
Automatizar ou guiar a atualização do `docs/TRAINING_LOGBOOK.md`, garantindo que cada experimento tenha uma conclusão clara (Sucesso, Falha, Anomalia) e uma lição aprendida.

## 2. Metodologia de Análise (O Protocolo "V.I.T.R.U.")

Para cada treino finalizado, o agente deve aplicar o protocolo:

### **V - Validation Check**
*   O `Loss (Train)` chegou a 0.0000? (Sinal de Overfitting/Memorização).
*   A diferença `Loss(Val) - Loss(Train)` é > 0.01? (Sinal de Divergência).
*   **Ação:** Se sim, marcar como "Alerta de Overfitting" no diário.

### **I - Improvement (Delta)**
*   Comparar AUC de cada classe contra:
    1.  O Generalista (Baseline).
    2.  A versão anterior do Especialista.
*   **Fórmula:** `Delta = AUC_Novo - AUC_Antigo`.
*   **Classificação:**
    *   `> +0.05`: **Revolutionary** 🚀
    *   `> +0.01`: **Success** 🟢
    *   `± 0.01`: **Stagnation** 🟡
    *   `< -0.01`: **Regression** 🔴

### **T - Texture vs Geometry**
*   Analisar quais classes melhoraram:
    *   Se Hérnia/Enfisema melhorou: "Sucesso Geométrico" (CNNs ganham).
    *   Se Fibrose/Infiltração melhorou: "Sucesso Textural" (Hybrid/Transformers ganham).
    *   Se Nódulo (pequeno) millhorou: "Sucesso de Resolução" (Input Size ganha).

### **R - Recommendation**
*   Baseado no resultado, qual o próximo passo?
    *   *Overfitting?* -> Aumentar Regularização (DropPath) ou mais dados.
    *   *Estagnação?* -> Mudar Arquitetura (B3 -> ConvNeXt).
    *   *Regressão?* -> Reverter Configuração.

### **U - Update Logbook**
*   Formatar a conclusão em Markdown e anexar ao arquivo `TRAINING_LOGBOOK.md`.

## 3. Template de Entrada no Diário

```markdown
### 🧪 Experimento [ID] - [Nome do Grupo]
**Data:** YYYY-MM-DD
**Config:** [Backbone] @ [Resolution]px

**📊 Resultados Chave:**
*   [Classe A]: 0.XX (Delta: +Y%) 🟢
*   [Classe B]: 0.XX (Delta: -Z%) 🔴

**🧠 Análise V.I.T.R.U.:**
O modelo apresentou [Comportamento, ex: Overfitting rápido]. A hipótese de que [Hipótese Inicial] se confirmou/falhou porque [Razão Técnica].

**💡 Próximo Passo:**
[Recomendação, ex: Testar ConvNeXt com DropPath 0.4]
```

## 4. Integração com Agentes
Esta skill deve ser usada pelo **Agente Relator** ou **Agente Analista** ao final de cada pipeline de treinamento.
