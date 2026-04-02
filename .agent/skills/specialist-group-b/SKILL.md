---
name: specialist-group-b
description: Skill dedicada ao treinamento de modelos para anomalidades estruturais
  grosseiras (Hérnia, Cardiomegalia, Enfisema).
metadata:
  version: 1.0
---

# 🏗️ Specialist Group B: Structural Anomalies

## 1. Escopo Clínico
Este grupo detecta alterações na *forma* e *geometria* do tórax, em vez de texturas internas.
*   **Alvos:** `Cardiomegaly`, `Hernia`, `Emphysema`, `Pneumothorax` (Legado), `Effusion`, `Pleural_Thickening`.

## 2. A Vitória da Geometria
O uso de Convolutional Networks (EfficientNet-B3) provou ser extremamente eficaz para problemas geométricos.
*   **Emphysema:** Atingiu **0.9450 AUC** (+22% sobre generalista). O modelo aprendeu a detectar o "pulmão hiper-expandido" e diafragma reto.
*   **Hernia:** Atingiu **0.9200 AUC** (+12%). Detecta a bolha gástrica deslocada com precisão.
*   **Cardiomegaly:** Sólido 0.9150. Medir o tamanho do coração é trivial para CNNs.

## 3. O Problema do Pneumotórax
O Pneumotórax caiu para 0.88.
*   **Diagnóstico:** Embora seja uma falha estrutural (pulmão colapsado), o sinal visual (linha da pleura) é sutil demais para 448px e se confunde com fundo preto.
*   **Solução Estratégica:** Pneumotórax será transferido para o **Grupo D (High-Res 512px)**.

## 4. Configuração Recomendada
```python
"group_b_structural": {
    "backbone": "efficientnet_b3",
    "resolution": 448,
    "aug_level": "specialist", # Foco em ShiftScaleRotate (Geometria)
    "class_weights": {"Hernia": 2.0, "Pleural_Thickening": 1.5, ...}
}
```
