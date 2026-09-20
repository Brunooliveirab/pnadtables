"""Proteção de custo: dry run, teto de bytes e aritmética de cobrança.

Tudo aqui roda offline. Nenhum teste toca no BigQuery: o caminho de recusa é
verificado justamente por ele não precisar do cliente para funcionar.
"""
import pytest

from pnadtables import columns as C
from pnadtables.data_source import (
    BYTES_PER_TIB,
    DEFAULT_COLUMNS,
    DEFAULT_MAX_GB,
    USD_PER_TIB,
    CostEstimate,
    PNADCDataSource,
    QueryTooLargeError,
)


@pytest.fixture
def src():
    return PNADCDataSource(billing_project_id="projeto-fake", ano=2024,
                           trimestre=1, ufs=["MT", "SP"])


# --- aritmética de custo ---------------------------------------------------
def test_cost_estimate_converte_bytes_para_tib_e_dolar():
    est = CostEstimate(bytes_processed=BYTES_PER_TIB, query="SELECT 1")
    assert est.tebibytes == 1.0
    assert est.usd_sem_franquia == pytest.approx(USD_PER_TIB)
    assert est.fracao_da_franquia == pytest.approx(1.0)


def test_cost_estimate_de_consulta_pequena_e_fracao_irrisoria_da_franquia():
    """~50 MB é a ordem de grandeza de um trimestre com DEFAULT_COLUMNS."""
    est = CostEstimate(bytes_processed=50 * 1024 ** 2, query="SELECT 1")
    assert est.gigabytes == pytest.approx(0.0488, abs=1e-3)
    assert est.fracao_da_franquia < 0.0001
    assert est.usd_sem_franquia < 0.001


def test_cost_estimate_str_menciona_gb_e_franquia():
    texto = str(CostEstimate(bytes_processed=2 * 1024 ** 3, query="SELECT 1"))
    assert "GB" in texto and "franquia" in texto


# --- construção da query ---------------------------------------------------
def test_query_filtra_ano_trimestre_e_ufs(src):
    sql = src._build_query()
    assert "ano = 2024" in sql
    assert "trimestre = 1" in sql
    assert "'MT', 'SP'" in sql
    assert C.BQ_TABLE in sql


def test_query_sem_ufs_nao_tem_clausula_in():
    sql = PNADCDataSource("p", 2024, 1)._build_query()
    assert " IN (" not in sql


def test_query_nunca_usa_select_star(src):
    """SELECT * multiplicaria o custo: a tabela tem centenas de colunas."""
    assert "SELECT *" not in src._build_query()
    for col in DEFAULT_COLUMNS:
        assert col in src._build_query()


# --- teto de bytes ---------------------------------------------------------
def test_get_data_recusa_consulta_acima_do_teto(src, monkeypatch, capsys):
    grande = CostEstimate(bytes_processed=40 * 1024 ** 3, query="SELECT 1")
    monkeypatch.setattr(PNADCDataSource, "dry_run", lambda self: grande)

    with pytest.raises(QueryTooLargeError) as erro:
        src.get_data(max_gb=5.0)

    msg = str(erro.value)
    assert "40.00 GB" in msg
    assert "5.00 GB" in msg
    assert "US$" in msg


def test_recusa_acontece_sem_precisar_do_cliente_bigquery(src, monkeypatch):
    """O guard precede qualquer import de google.cloud.

    Se `_client` fosse chamado, este teste falharia — é o que garante que a
    recusa funciona mesmo em ambiente sem o cliente instalado.
    """
    def explode(self):
        raise AssertionError("_client() não deveria ser chamado ao recusar")

    monkeypatch.setattr(PNADCDataSource, "_client", explode)
    monkeypatch.setattr(
        PNADCDataSource, "dry_run",
        lambda self: CostEstimate(bytes_processed=99 * 1024 ** 3, query="q"),
    )
    with pytest.raises(QueryTooLargeError):
        src.get_data(max_gb=1.0)


def test_consulta_dentro_do_teto_nao_e_recusada(src, monkeypatch):
    pequena = CostEstimate(bytes_processed=50 * 1024 ** 2, query="SELECT 1")
    monkeypatch.setattr(PNADCDataSource, "dry_run", lambda self: pequena)
    monkeypatch.setattr(PNADCDataSource, "_client",
                        lambda self: (_ for _ in ()).throw(ImportError("sem gcloud")))

    # Passa do guard e só falha adiante, ao tentar o cliente: prova que o teto
    # não barrou a consulta.
    with pytest.raises(ImportError):
        src.get_data(max_gb=5.0, verbose=False)


def test_max_gb_none_pula_o_dry_run(src, monkeypatch):
    def explode(self):
        raise AssertionError("dry_run não deveria rodar com max_gb=None")

    monkeypatch.setattr(PNADCDataSource, "dry_run", explode)
    monkeypatch.setattr(PNADCDataSource, "_client",
                        lambda self: (_ for _ in ()).throw(ImportError("sem gcloud")))
    with pytest.raises(ImportError):
        src.get_data(max_gb=None)


def test_teto_padrao_e_folgado_para_um_trimestre():
    """O padrão precisa acomodar uso normal sem virar carta branca."""
    assert 1.0 <= DEFAULT_MAX_GB <= 20.0
