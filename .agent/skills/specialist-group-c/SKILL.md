---
name: specialist-group-c
description: Skill dedicada ao treinamento de modelos especialistas para detecção
  de lesões focais (Nódulos, Massas) e Fibrose.
metadata:
  version: 1.0
---

# 🧬 Specialist Group C: Oncology & Small Objects

## 1. O Desafio Clínico
Este grupo foca nas lesões mais críticas para diagnóstico precoce de câncer (Nódulos/Massas) e cicatrizes crônicas (Fibrose).
*   **Nódulos:** Pequenos (<3cm), exigem alta resolução.
*   **Fibrose:** Padrão de textura difusa ("riscos"), exige contexto global.

## 2. Lições Aprendidas (Round 1 - EfficientNet-B3)
O primeiro experimento com EfficientNet-B3 @ 512px mostrou:
*   ✅ **Sucesso em Nódulos:** AUC 0.83 (Ganho de +4% vs Generalista).
*   ❌ **Falha em Fibrose:** AUC 0.67 (Queda massiva).

**Diagnóstico:** CNNs puras como EfficientNet focam muito em texturas locais quando treinadas em alta resolução, perdendo o padrão global necessário para identificar Fibrose espalhada.

## 3. Estratégia "The Challenger": ConvNeXt
Para o Round 2, utilizaremos **ConvNeXt-Tiny**.
*   **Por que ConvNeXt?** Usa patches grandes (4x4) e blocos residuais inspirados em Vision Transformers.
*   **Hipótese:** A capacidade do ConvNeXt de modelar dependências de longo alcance ajudará a recuperar a Fibrose sem perder a precisão nos Nódulos.

## 4. Configuração Técnica
*   **Backbone:** `convnext_tiny`
*   **Resolução:** 512px (Mantido).
*   **Batch Size:** 14 (Ajustado para memória).
*   **Otimizador:** AdamW (Melhor para arquiteturas modernas).
*   **Learning Rate:** 2e-5 (Menor que CNNs).

## 5. Critérios de Sucesso
*   **Nodule:** Manter > 0.83
*   **Fibrose:** Recuperar > 0.80

## 6. Comandos
```bash
python scripts/train_specialist.py --group group_c_nodules_cxt --epochs 20 --workers 5
```
