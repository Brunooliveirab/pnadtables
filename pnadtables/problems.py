"""
Tarefas de predição no estilo folktables, definidas sobre a PNAD Contínua.

Espelha a arquitetura de `folktables.BasicProblem`: cada tarefa declara
features, alvo (target), transformação do alvo, atributo de grupo (protegido)
e um pré-processamento. O método `df_to_pandas` devolve (X, y, group, weight).

Diferença em relação ao folktables: carregamos opcionalmente o PESO amostral
(v1028), porque a PNADC é amostra complexa e métricas de fairness não
ponderadas podem enviesar a leitura.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import columns as C


def _num(serie):
    """Converte para numérico de forma robusta (a BD costuma trazer STRING)."""
    return pd.to_numeric(serie, errors="coerce")


def _encode_feature(serie):
    """
    Codifica uma feature para uso no modelo:
      - colunas numéricas (ou strings de número) -> numérico;
      - colunas categóricas de texto (ex.: sigla_uf 'MT') -> códigos inteiros.
    Evita o bug de zerar features de texto ao coagi-las a numérico.
    """
    num = pd.to_numeric(serie, errors="coerce")
    if num.isna().all() and serie.notna().any():
        codes, _ = pd.factorize(serie, use_na_sentinel=True)
        out = pd.Series(codes, index=serie.index, dtype="float64")
        out[out == -1] = np.nan
        return out
    return num


class BasicProblem:
    def __init__(self, features, target, target_transform, group,
                 preprocess=None, group_transform=None, weight=C.COL_PESO):
        self.features = list(features)
        self.target = target
        self.target_transform = target_transform
        self.group = group
        self.preprocess = preprocess or (lambda d: d)
        self.group_transform = group_transform or (lambda s: s)
        self.weight = weight

    def df_to_pandas(self, df):
        """Devolve (X, y, group, weight). `weight` é None se não houver coluna de peso."""
        df = self.preprocess(df.copy())
        X = df[self.features].apply(_encode_feature)
        y = self.target_transform(df[self.target])
        g = self.group_transform(_num(df[self.group]))
        w = _num(df[self.weight]) if self.weight and self.weight in df else None

        # Alinha tudo e descarta linhas sem grupo definido (ex.: colapso binário).
        keep = g.notna()
        X, y, g = X[keep], y[keep], g[keep]
        if w is not None:
            w = w[keep]
        return X, y, g, w

    def df_to_numpy(self, df):
        X, y, g, w = self.df_to_pandas(df)
        w_arr = None if w is None else w.to_numpy()
        return X.to_numpy(), y.to_numpy(), g.to_numpy(), w_arr


# ---------------------------------------------------------------------------
# Pré-processamentos
# ---------------------------------------------------------------------------
def _universo_idade_trabalho(df):
    """Mantém apenas pessoas em idade de trabalhar (14+ na PNADC)."""
    return df[_num(df[C.COL_IDADE]) >= C.IDADE_TRABALHO]


def _universo_ocupados(df):
    """Mantém ocupados (vd4002 == 1) em idade de trabalhar e com renda > 0."""
    df = _universo_idade_trabalho(df)
    ocupado = _num(df[C.COL_OCUPACAO]) == 1
    renda_pos = _num(df[C.COL_RENDA_HAB]) > 0
    return df[ocupado & renda_pos]


# ---------------------------------------------------------------------------
# PNADEmployment — análogo de ACSEmployment
#   Universo: população em idade de trabalhar (14+).
#   Alvo: pessoa ocupada (vd4002 == 1). Fora da força/desocupada -> 0.
#   Grupo protegido: cor ou raça.
# ---------------------------------------------------------------------------
PNADEmployment = BasicProblem(
    features=[C.COL_IDADE, C.COL_SEXO, C.COL_RACA, C.COL_INSTRUCAO, C.COL_UF],
    target=C.COL_OCUPACAO,
    target_transform=lambda s: (_num(s) == 1).astype(int),
    group=C.COL_RACA,
    preprocess=_universo_idade_trabalho,
    group_transform=C.raca_branca_negra,  # troque para C.raca_5grupos p/ multigrupo
)


# ---------------------------------------------------------------------------
# PNADIncome — análogo de ACSIncome
#   Universo: ocupados, 14+, renda > 0.
#   Alvo: renda mensal habitual > threshold.
#   Grupo protegido: cor ou raça.
#
# folktables usa um corte fixo (US$ 50k). Aqui o corte é PARÂMETRO: o padrão
# (R$ 3.036) é ~2x o salário mínimo de 2025 (R$ 1.518). AJUSTE ao ano de
# referência dos seus dados — o corte muda quem é "positivo" e, portanto, as
# métricas de fairness.
# ---------------------------------------------------------------------------
def make_pnad_income(threshold=3036.0, group_transform=C.raca_branca_negra):
    return BasicProblem(
        features=[C.COL_IDADE, C.COL_SEXO, C.COL_RACA, C.COL_INSTRUCAO, C.COL_UF],
        target=C.COL_RENDA_HAB,
        target_transform=lambda s: (_num(s) > threshold).astype(int),
        group=C.COL_RACA,
        preprocess=_universo_ocupados,
        group_transform=group_transform,
    )


PNADIncome = make_pnad_income()
