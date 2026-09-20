import numpy as np
import pandas as pd
import pytest

from pnadtables import (
    PNADEmployment, PNADIncome, make_pnad_income, audit_report,
    disparate_impact, selection_rates, columns as C,
)


@pytest.fixture
def synthetic_pnadc():
    """PNADC-like frame with STRING-typed values, as Base dos Dados returns them."""
    rng = np.random.default_rng(0)
    n = 3000
    return pd.DataFrame({
        "ano": ["2024"] * n,
        "trimestre": ["1"] * n,
        "sigla_uf": rng.choice(["MT", "SP", "RJ"], n),
        "v1028": rng.uniform(50, 400, n).round(1).astype(str),
        "v2007": rng.choice(["1", "2"], n),
        "v2009": rng.integers(5, 80, n).astype(str),
        "v2010": rng.choice(["1", "2", "3", "4", "5", "9"], n, p=[.43, .1, .01, .43, .02, .01]),
        "vd3004": rng.choice([str(i) for i in range(1, 8)], n),
        "vd4001": rng.choice(["1", "2"], n),
        "vd4002": rng.choice(["1", "2"], n, p=[.9, .1]),
        "vd4019": rng.uniform(0, 8000, n).round(2).astype(str),
    })


def test_employment_contract(synthetic_pnadc):
    X, y, g, w = PNADEmployment.df_to_pandas(synthetic_pnadc)
    assert len(X) == len(y) == len(g) == len(w)
    assert set(y.unique()) <= {0, 1}
    assert set(g.unique()) <= {"Branca", "Negra"}
    # universe filter: working age only
    assert (X[C.COL_IDADE] >= C.IDADE_TRABALHO).all()


def test_text_categorical_is_encoded_not_nulled(synthetic_pnadc):
    X, *_ = PNADEmployment.df_to_pandas(synthetic_pnadc)
    assert X[C.COL_UF].notna().all(), "sigla_uf must be label-encoded, not coerced to NaN"
    assert X[C.COL_UF].nunique() == 3


def test_binary_race_drops_other_categories(synthetic_pnadc):
    n_in = (synthetic_pnadc[C.COL_IDADE].astype(int) >= C.IDADE_TRABALHO).sum()
    X, *_ = PNADEmployment.df_to_pandas(synthetic_pnadc)
    assert len(X) < n_in  # Amarela / Indígena / Ignorada removed


def test_five_group_race_keeps_everything(synthetic_pnadc):
    prob = make_pnad_income(group_transform=C.raca_5grupos)
    _, _, g, _ = prob.df_to_pandas(synthetic_pnadc)
    assert set(g.unique()) <= set(C.RACA_5.values())


def test_income_threshold_changes_positives(synthetic_pnadc):
    _, y_lo, _, _ = make_pnad_income(threshold=1000).df_to_pandas(synthetic_pnadc)
    _, y_hi, _, _ = make_pnad_income(threshold=6000).df_to_pandas(synthetic_pnadc)
    assert y_lo.sum() > y_hi.sum()


def test_income_universe_is_employed_with_positive_income(synthetic_pnadc):
    X, y, g, w = PNADIncome.df_to_pandas(synthetic_pnadc)
    assert len(X) > 0
    assert len(X) < len(synthetic_pnadc)


def test_weighted_selection_rate():
    y_pred = np.array([1, 1, 0, 0])
    group = np.array(["A", "A", "B", "B"])
    weight = np.array([1.0, 3.0, 1.0, 1.0])
    rates = selection_rates(y_pred, group, weight)
    assert rates["A"] == 1.0 and rates["B"] == 0.0


def test_weighting_changes_result():
    y_pred = np.array([1, 0, 1, 0])
    group = np.array(["A", "A", "B", "B"])
    unweighted = selection_rates(y_pred, group)
    weighted = selection_rates(y_pred, group, weight=np.array([9.0, 1.0, 1.0, 9.0]))
    assert unweighted["A"] == 0.5 and weighted["A"] == 0.9
    assert weighted["B"] == pytest.approx(0.1)


def test_disparate_impact_reference_is_max_rate():
    y_pred = np.array([1, 1, 1, 0, 1, 0])
    group = np.array(["A", "A", "A", "B", "B", "B"])
    di, ref = disparate_impact(y_pred, group)
    assert ref == "A" and di["A"] == 1.0
    assert di["B"] == pytest.approx(1 / 3)


def test_audit_report_shape(synthetic_pnadc):
    X, y, g, w = PNADEmployment.df_to_pandas(synthetic_pnadc)
    y_pred = np.random.default_rng(1).integers(0, 2, len(y))
    rep = audit_report(y.to_numpy(), y_pred, g.to_numpy(), weight=w.to_numpy())
    assert list(rep.columns) == ["n", "taxa_selecao", "TPR", "FPR", "disparate_impact_vs_ref"]
    assert rep.attrs["referencia"] in rep.index
    assert rep["n"].sum() == len(y)


# ---------------------------------------------------------------------------
# Regressões dos ajustes do gate G0 (coerência entre nome, doc e comportamento)
# ---------------------------------------------------------------------------
def test_raca_5grupos_keeps_ignorada_by_default():
    serie = pd.Series([1, 2, 3, 4, 5, 9])
    out = C.raca_5grupos(serie)
    assert "Ignorada" in set(out.dropna())
    assert out.notna().all()


def test_raca_5grupos_can_drop_ignorada():
    serie = pd.Series([1, 2, 3, 4, 5, 9])
    out = C.raca_5grupos(serie, incluir_ignorada=False)
    assert "Ignorada" not in set(out.dropna())
    assert out.isna().sum() == 1
    assert set(out.dropna()) == {"Branca", "Preta", "Amarela", "Parda", "Indígena"}
    # o alias nomeado precisa concordar com o parâmetro
    pd.testing.assert_series_equal(out, C.raca_5grupos_sem_ignorada(serie))


def test_raca_5grupos_maps_unknown_code_to_nan():
    out = C.raca_5grupos(pd.Series([1, 7]))
    assert out.isna().sum() == 1


def test_disparate_impact_default_reference_bounds_ratios_at_one():
    """Com a referência = grupo de maior taxa, nenhuma razão pode passar de 1.

    É por isso que o limiar superior de 1.25 da regra dos 4/5 não se aplica ao
    modo padrão — a documentação de `disparate_impact` depende disso.
    """
    y_pred = np.array([1, 1, 1, 1, 0, 1, 0, 0])
    group = np.array(["A"] * 4 + ["B"] * 4)
    di, ref = disparate_impact(y_pred, group)
    assert ref == "A"
    assert all(v <= 1.0 for v in di.values())


def test_disparate_impact_explicit_reference_allows_ratio_above_one():
    y_pred = np.array([1, 1, 1, 1, 0, 1, 0, 0])
    group = np.array(["A"] * 4 + ["B"] * 4)
    di, ref = disparate_impact(y_pred, group, reference="B")
    assert ref == "B"
    assert di["A"] > 1.0


def test_disparate_impact_rejects_unknown_reference():
    y_pred = np.array([1, 0])
    group = np.array(["A", "B"])
    with pytest.raises(KeyError):
        disparate_impact(y_pred, group, reference="Z")
