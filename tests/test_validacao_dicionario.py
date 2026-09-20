"""Lógica de comparação do validador de dicionário.

Offline: a função de rede (`carregar_dicionario`) não é exercitada aqui. O que
se testa é a decisão — dado um dicionário, quais declarações conferem.
"""
import importlib.util
from pathlib import Path

import pytest

from pnadtables import columns as C

_spec = importlib.util.spec_from_file_location(
    "validar_dicionario",
    Path(__file__).resolve().parent.parent / "scripts" / "validar_dicionario.py",
)
validar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validar)


# --- normalização ----------------------------------------------------------
@pytest.mark.parametrize("entrada,esperado", [
    ("Cor ou raça", "cor ou raca"),
    ("CONDIÇÃO  DE   OCUPAÇÃO", "condicao de ocupacao"),
    ("Unidade Primária de Amostragem (UPA)", "unidade primaria de amostragem (upa)"),
    ("Número\nde ordem", "numero de ordem"),
])
def test_normalizar_remove_acento_caixa_e_espaco(entrada, esperado):
    assert validar.normalizar(entrada) == esperado


# --- decisão da conferência ------------------------------------------------
def test_confere_quando_descricao_oficial_contem_o_esperado():
    dic = {cod: esp for cod, esp in C.SIGNIFICADO_ESPERADO.items()}
    dic["v2010"] = "Cor ou raça"
    resultados = validar.conferir(dic)
    v2010 = next(r for r in resultados if r["codigo"] == "v2010")
    assert v2010["ok"] and v2010["situacao"] == "confere"


def test_acusa_ausente_quando_codigo_nao_existe_no_dicionario():
    resultados = validar.conferir({})
    assert all(r["situacao"] == "AUSENTE" for r in resultados)
    assert not any(r["ok"] for r in resultados)


def test_acusa_divergencia_quando_variavel_foi_trocada():
    """O cenário que motiva o script: rendimento habitual virar efetivo."""
    dic = dict(C.SIGNIFICADO_ESPERADO)
    dic["vd4019"] = "Rendimento mensal efetivo de todos os trabalhos"
    resultados = validar.conferir(dic)
    vd4019 = next(r for r in resultados if r["codigo"] == "vd4019")
    assert not vd4019["ok"]
    assert vd4019["situacao"] == "DIVERGE"


def test_conferencia_ignora_acento_e_caixa_do_dicionario():
    dic = dict(C.SIGNIFICADO_ESPERADO)
    dic["vd4002"] = "CONDIÇÃO DE OCUPAÇÃO na semana de referência"
    resultados = validar.conferir(dic)
    assert next(r for r in resultados if r["codigo"] == "vd4002")["ok"]


# --- pesos replicados ------------------------------------------------------
def test_pesos_replicados_completos():
    dic = {c: "Peso replicado" for c in C.COLS_PESO_REPLICADO}
    n, ok = validar.conferir_pesos_replicados(dic)
    assert n == C.N_PESOS_REPLICADOS and ok


def test_pesos_replicados_incompletos_sao_acusados():
    dic = {c: "Peso replicado" for c in C.COLS_PESO_REPLICADO[:10]}
    n, ok = validar.conferir_pesos_replicados(dic)
    assert n == 10 and not ok


def test_nomes_dos_pesos_replicados_tem_tres_digitos():
    assert C.COLS_PESO_REPLICADO[0] == "v1028001"
    assert C.COLS_PESO_REPLICADO[-1] == "v1028200"
    assert len(set(C.COLS_PESO_REPLICADO)) == C.N_PESOS_REPLICADOS


# --- chave de domicílio ----------------------------------------------------
def test_chave_de_domicilio_nao_e_so_o_numero_do_domicilio():
    """v1008 sozinho não identifica domicílio: repete entre UPAs e painéis."""
    assert C.COL_DOMICILIO in C.CHAVE_DOMICILIO
    assert C.COL_UPA in C.CHAVE_DOMICILIO
    assert len(C.CHAVE_DOMICILIO) == 3


# --- relatório -------------------------------------------------------------
def test_relatorio_lista_pendencias_quando_ha_falha():
    texto = validar.montar_relatorio(
        validar.conferir({}), n_replicados=0, replicados_ok=False, total_dicionario=420
    )
    assert "Pendências" in texto and "AUSENTE".lower() in texto.lower()


def test_relatorio_registra_limites_da_verificacao():
    texto = validar.montar_relatorio(
        validar.conferir(dict(C.SIGNIFICADO_ESPERADO)),
        n_replicados=200, replicados_ok=True, total_dicionario=420,
    )
    assert "Limites desta verificação" in texto
    assert "v1027" in texto  # a ambiguidade conhecida precisa constar
