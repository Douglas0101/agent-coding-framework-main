---
name: specialist-group-d
description: Skill para treinar um modelo especialista focado na interação hemodinâmica
  (Coração-Pulmão) e patologias do espaço pleural.
metadata:
  version: 1.0
---

# 🫁 Specialist Group D: Pleural & Hemodynamic Support

## 1. O Problema (Contexto Fisiopatológico)
Nossa análise dos Grupos A e B revelou falhas em doenças conectadas à mecânica dos fluidos e pressão:
*   **Pneumotórax:** Caiu performance no Grupo B (estrutural) pois exige alta definição pleural.
*   **Edema:** Estagnou no Grupo A (textura) pois perdeu o contexto cardíaco.
*   **Cardiomegalia e Derrame (Effusion):** Tiveram sucesso, mas são clinicamente as *causas* do Edema.

## 2. A Solução: Agrupamento Hemodinâmico
O Grupo D unifica patologias que compartilham causa e efeito na fisiologia cardiotorácica:
> "O coração falha (Cardiomegaly) -> Aumenta pressão -> Vaza líquido (Edema/Effusion) -> Altera pleura".

### 2.1 Alvos (Target Pathologies)
1.  **Pneumothorax:** (Ar na pleura). Exige alta resolução.
2.  **Effusion:** (Líquido na pleura). Forte correlação com coração.
3.  **Edema:** (Líquido no pulmão). Depende do coração para diagnóstico correto.
4.  **Cardiomegaly:** A "âncora" visual. É a pista macroscópica para as outras.

**Remoção de Outros Grupos:**
*   Ao ativar o Grupo D, estas doenças devem ser ignoradas/removidas das métricas principais dos Grupos A e B para evitar conflito de especialistas (ou usadas em Ensemble Weighted).

## 3. Configuração Técnica

### 3.1 Arquitetura
*   **Backbone:** `EfficientNet-B3` (O novo padrão ouro do projeto).
*   **Resolução:** **512px** (Mandatório para ver a linha fina do Pneumotórax).
*   **Loss:** Focal Loss com `gamma=2.0` (Gama menor, pois Cardiomegaly/Effusion são classes "fáceis" e abundantes, queremos equilíbrio).

### 3.2 Dynamic Output Head
O modelo terá **4 saídas**.
*   Isso simplifica drasticamente o problema para a rede neural. Ela não precisa saber o que é uma "Massa" ou "Pneumonia", focando 100% em bordas cardíacas e pleurais.

## 4. Integração Arquitetural (Safety Check)
*   **Config:** Adicionar em `src/specialists/config.py`.
*   **Database:** O sistema usa `active_labels` dinâmico. O banco aceitará as métricas dessas 4 classes sem alterar schema.
*   **Dashboard:** O frontend agrupa por `run_id`. O Grupo D aparecerá automaticamente como uma nova coluna/linha. Não requer mudança de código UI.

## 5. Plano de Treinamento
1.  Esperar término do Grupo C (Nódulos).
2.  Rodar:
    ```bash
    python scripts/train_specialist.py --group group_d_hemodynamic --epochs 20 --workers 5
    ```
