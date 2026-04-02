---
name: specialist-group-a
description: Skill para treinar o especialista em opacidades pulmonares difusas (Pneumonia,
  Infiltração, etc.), documentando a evolução até a versão V5.
metadata:
  version: 1.0
---

# ☁️ Specialist Group A: Opacities & Infections

## 1. Escopo Clínico
Este grupo foca nas patologias mais comuns e letais em ambiente hospitalar, caracterizadas por "manchas brancas" no pulmão (opacidades).
*   **Alvos:** `Pneumonia`, `Infiltration`, `Atelectasis`, `Consolidation`, `Edema`.

## 2. Histórico de Evolução
Testamos múltiplas configurações até chegar ao campeão atual.

### V1-V3 (The Heavyweights)
*   **Tentativa:** EfficientNet-B4 @ 512px.
*   **Problema:** Overfitting rápido e resultados estagnados em Infiltração (<0.78). O modelo era "grande demais" para a quantidade de dados de alta qualidade.

### V4 (The Rescue Run)
*   **Tentativa:** EfficientNet-B4 @ 448px com Class Weights agressivos.
*   **Resultado:** Melhorou Consolidação, mas Pneumonia continuou instável.

### 🏆 V5 (The Agile Champion)
*   **Config Atual:** `group_a_opacities_v5`
*   **Backbone:** `EfficientNet-B3`.
*   **Resolução:** 448px.
*   **Segredo:** Uma rede mais leve (B3) generalizou melhor que a B4.
*   **Performance:**
    *   **Infiltration:** 0.8027 (Recorde).
    *   **Atelectasis:** 0.8308.
    *   **Consolidation:** 0.8857.

## 3. O Dilema do Edema
O Edema permaneceu em ~0.71.
*   **Causa:** Edema é visualmente similar a Infiltração. O diferencial é o *contexto cardíaco* (Coração Grande).
*   **Solução Estratégica:** O Edema será movido (ou reforçado) pelo **Grupo D (Hemodinâmico)**, que vê o coração. O Grupo A foca na textura da mancha.

## 4. Configuração Recomendada
```python
"group_a_opacities_v5": {
    "backbone": "efficientnet_b3",
    "resolution": 448,
    "class_weights": {"Pneumonia": 3.0, "Infiltration": 2.0, ...},
    "augmentations": ["CLAHE", "GridMask", "MixUp"]
}
```
