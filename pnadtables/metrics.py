"""
Métricas de fairness de grupo, com suporte a PESO amostral.

Implementa o essencial para uma auditoria no estilo folktables:
  - taxa de seleção por grupo  -> razão de taxas (heurística da regra dos 4/5)
  - TPR e FPR por grupo        -> equalized odds / equal opportunity

Todas aceitam `weight` (peso amostral calibrado da PNADC).

ESCOPO E LIMITES (v0.1.0.dev0)
------------------------------
1. `weight` produz ESTIMATIVAS PONTUAIS ponderadas. Isso NÃO é inferência
   survey-aware: a PNADC é uma amostra complexa com estratos e UPAs, e os
   intervalos de confiança corretos exigem esses identificadores de desenho,
   ainda não implementados aqui. Não reporte IC a partir destas funções.
2. Nenhuma das duas versões (ponderada/não ponderada) é universalmente "a
   certa": a escolha depende do objetivo. Reporte as duas como análise de
   sensibilidade e explicite qual pergunta cada uma responde.
3. A razão entre taxas é uma HEURÍSTICA contextual de triagem, não um
   diagnóstico jurídico automático de discriminação.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _wmean(mask_num, weight):
    """Média ponderada de um vetor booleano/0-1 sob um subconjunto."""
    mask_num = np.asarray(mask_num, dtype=float)
    if weight is None:
        return mask_num.mean() if len(mask_num) else np.nan
    weight = np.asarray(weight, dtype=float)
    s = weight.sum()
    return float((mask_num * weight).sum() / s) if s > 0 else np.nan


def selection_rates(y_pred, group, weight=None):
    """P(ŷ=1) por grupo."""
    y_pred = np.asarray(y_pred)
    group = np.asarray(group)
    out = {}
    for g in pd.unique(group):
        idx = group == g
        w = None if weight is None else np.asarray(weight)[idx]
        out[g] = _wmean(y_pred[idx] == 1, w)
    return out


def disparate_impact(y_pred, group, weight=None, reference=None):
    """
    Razão entre a taxa de seleção de cada grupo e a do grupo de referência.

    Referência (`reference=None`, padrão): o grupo de MAIOR taxa de seleção.
    Sob essa escolha as razões ficam, por construção, no intervalo (0, 1] — o
    limiar superior de 1.25 da regra dos 4/5 NÃO se aplica aqui, porque nenhum
    grupo pode exceder a referência. O sinal de atenção é razão < 0.8.

    Passando `reference` explicitamente (ex.: um grupo de comparação fixado no
    protocolo, e não o máximo empírico), razões > 1 passam a ser possíveis e
    o par de limiares 0.8 / 1.25 volta a fazer sentido.

    Retorna (dict {grupo: razão}, grupo_de_referência).

    A regra dos 4/5 é heurística de triagem, sensível a tamanho amostral e à
    escolha de referência. Ela não estabelece discriminação por si só.
    """
    rates = selection_rates(y_pred, group, weight)
    if reference is None:
        reference = max(rates, key=rates.get)  # grupo com maior taxa
    if reference not in rates:
        raise KeyError(
            f"grupo de referência {reference!r} não existe nos dados; "
            f"grupos disponíveis: {sorted(map(str, rates))}"
        )
    base = rates[reference]
    return {g: (r / base if base else np.nan) for g, r in rates.items()}, reference


def rate_by_group(y_true, y_pred, group, weight=None, condition=1):
    """
    TPR (condition=1) ou FPR (condition=0) por grupo.
    TPR = P(ŷ=1 | y=1);  FPR = P(ŷ=1 | y=0).
    """
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    group = np.asarray(group)
    out = {}
    for g in pd.unique(group):
        idx = (group == g) & (y_true == condition)
        w = None if weight is None else np.asarray(weight)[idx]
        out[g] = _wmean(y_pred[idx] == 1, w)
    return out


def audit_report(y_true, y_pred, group, weight=None):
    """Monta um DataFrame-resumo por grupo: n, taxa de seleção, TPR, FPR, DI."""
    di, ref = disparate_impact(y_pred, group, weight)
    sr = selection_rates(y_pred, group, weight)
    tpr = rate_by_group(y_true, y_pred, group, weight, condition=1)
    fpr = rate_by_group(y_true, y_pred, group, weight, condition=0)
    group = np.asarray(group)
    rows = []
    for g in sr:
        rows.append({
            "grupo": g,
            "n": int((group == g).sum()),
            "taxa_selecao": sr[g],
            "TPR": tpr.get(g, np.nan),
            "FPR": fpr.get(g, np.nan),
            "disparate_impact_vs_ref": di[g],
        })
    df = pd.DataFrame(rows).set_index("grupo")
    df.attrs["referencia"] = ref
    return df
