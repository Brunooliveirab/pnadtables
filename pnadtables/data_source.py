"""
Fonte de dados: consulta a PNAD Contínua no BigQuery público da Base dos Dados.

CUSTO — LEIA ANTES DE RODAR
---------------------------
Os microdados são públicos, mas no BigQuery **a consulta é cobrada de quem
consulta**, não de quem hospeda: o `billing_project_id` é o projeto para onde
vai a conta. A cobrança é por bytes varridos pela query.

Por isso este módulo **nunca executa uma consulta sem antes estimar o custo**.
A estimativa usa o modo dry run do BigQuery, que é gratuito e não lê dado
algum — ele só devolve quantos bytes a query varreria.

    src = PNADCDataSource(billing_project_id="seu-projeto", ano=2024,
                          trimestre=1, ufs=["MT", "SP"])
    print(src.dry_run())        # gratuito: quanto essa consulta custaria
    df = src.get_data()         # só executa se couber no limite de bytes

`get_data()` tem um teto padrão (`DEFAULT_MAX_GB`) e o aplica em dois níveis:
recusa localmente com base no dry run, e ainda passa `maximum_bytes_billed`
para o BigQuery, que aborta a query do lado do servidor se ela crescer além
do teto. Passe `max_gb=None` para desativar — sabendo o que está fazendo.

Pré-requisitos:
    pip install basedosdados pandas
    Um projeto no Google Cloud com billing ativo.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import columns as C

# --- Constantes de cobrança do BigQuery (on-demand) -------------------------
# Confira em https://cloud.google.com/bigquery/pricing antes de citar números:
# preço e franquia mudam, e a franquia é por conta de faturamento, compartilhada
# com qualquer outro uso seu de BigQuery no mês.
BYTES_PER_TIB = 1024 ** 4
USD_PER_TIB = 6.25
FREE_TIER_TIB_MONTH = 1.0

# Teto padrão de bytes por consulta. Um trimestre da PNADC com as 11 colunas de
# DEFAULT_COLUMNS fica na casa de dezenas de MB, então 5 GB é folgado para uso
# normal e ainda assim barra um engano do tipo "esqueci o filtro de ano".
DEFAULT_MAX_GB = 5.0

# Colunas mínimas para as tarefas atuais. Adicione aqui se criar novas tarefas.
# Manter essa lista curta é a principal alavanca de custo: o BigQuery é colunar
# e cobra pelas colunas lidas, então SELECT * custa ordens de grandeza mais.
DEFAULT_COLUMNS = [
    C.COL_ANO,
    C.COL_TRIMESTRE,
    C.COL_UF,
    C.COL_PESO,
    C.COL_SEXO,
    C.COL_IDADE,
    C.COL_RACA,
    C.COL_INSTRUCAO,
    C.COL_FORCA_TRAB,
    C.COL_OCUPACAO,
    C.COL_RENDA_HAB,
]


class QueryTooLargeError(RuntimeError):
    """A consulta varreria mais bytes do que o teto autorizado."""


@dataclass(frozen=True)
class CostEstimate:
    """Resultado de um dry run: quanto a query varreria, e o que isso custaria.

    `usd_sem_franquia` é o custo **se nenhuma franquia gratuita estiver
    disponível**. É o pior caso, de propósito: a franquia é mensal e por conta
    de faturamento, então este objeto não tem como saber quanto dela já foi
    consumido por outros usos seus.
    """

    bytes_processed: int
    query: str

    @property
    def gigabytes(self) -> float:
        return self.bytes_processed / 1024 ** 3

    @property
    def tebibytes(self) -> float:
        return self.bytes_processed / BYTES_PER_TIB

    @property
    def usd_sem_franquia(self) -> float:
        return self.tebibytes * USD_PER_TIB

    @property
    def fracao_da_franquia(self) -> float:
        """Que fração da franquia mensal gratuita esta consulta consumiria."""
        return self.tebibytes / FREE_TIER_TIB_MONTH

    def __str__(self) -> str:
        return (
            f"dry run: {self.gigabytes:.3f} GB varridos "
            f"({self.fracao_da_franquia:.2%} da franquia mensal de "
            f"{FREE_TIER_TIB_MONTH:g} TiB) — "
            f"US$ {self.usd_sem_franquia:.4f} se a franquia já estiver esgotada"
        )


def _credentials(from_file: bool = False, reauth: bool = False):
    """Credenciais do Google Cloud, pela mesma via que o `basedosdados` usa.

    Reaproveita o fluxo do `basedosdados` para que `dry_run()` e `get_data()`
    autentiquem igual a `bd.read_sql`. Se essa função interna mudar de lugar
    numa versão futura, cai no Application Default Credentials.
    """
    try:
        from basedosdados.download.download import _credentials as _bd_credentials
        return _bd_credentials(from_file=from_file, reauth=reauth)
    except Exception:  # pragma: no cover - depende do ambiente
        return None  # google.cloud.bigquery cai no ADC


class PNADCDataSource:
    def __init__(self, billing_project_id, ano, trimestre, ufs=None,
                 columns=None, from_file=False):
        self.billing_project_id = billing_project_id
        self.ano = int(ano)
        self.trimestre = int(trimestre)
        self.ufs = list(ufs) if ufs else None
        self.columns = columns or DEFAULT_COLUMNS
        self.from_file = from_file

    def _build_query(self):
        cols = ", ".join(self.columns)
        sql = (
            f"SELECT {cols}\n"
            f"FROM `{C.BQ_TABLE}`\n"
            f"WHERE {C.COL_ANO} = {self.ano} "
            f"AND {C.COL_TRIMESTRE} = {self.trimestre}"
        )
        if self.ufs:
            ufs = ", ".join(f"'{u}'" for u in self.ufs)
            sql += f"\nAND {C.COL_UF} IN ({ufs})"
        return sql

    def _client(self):
        from google.cloud import bigquery
        return bigquery.Client(
            project=self.billing_project_id,
            credentials=_credentials(from_file=self.from_file),
        )

    def dry_run(self) -> CostEstimate:
        """Estima os bytes da consulta SEM executá-la. Gratuito.

        O dry run do BigQuery não lê dados nem gera cobrança: ele só planeja a
        query e informa quantos bytes ela varreria. Use isto antes de qualquer
        consulta nova, sobretudo ao mudar colunas, ano ou recorte de UF.
        """
        from google.cloud import bigquery

        sql = self._build_query()
        job = self._client().query(
            sql,
            job_config=bigquery.QueryJobConfig(
                dry_run=True,
                use_query_cache=False,
            ),
        )
        return CostEstimate(bytes_processed=job.total_bytes_processed, query=sql)

    def get_data(self, max_gb=DEFAULT_MAX_GB, verbose=True):
        """Executa a query e devolve um DataFrame pandas.

        Antes de executar, faz um dry run (gratuito) e recusa a consulta se ela
        exceder `max_gb`. O mesmo teto vai como `maximum_bytes_billed` para o
        BigQuery, que aborta a query do lado do servidor caso ela ultrapasse o
        limite — proteção que sobrevive a uma estimativa errada.

        max_gb=None desativa os dois níveis de proteção.
        """
        sql = self._build_query()

        # A checagem de custo vem ANTES de qualquer import do cliente BigQuery,
        # para que uma consulta grande demais seja recusada sem depender de
        # google.cloud estar instalado.
        if max_gb is not None:
            estimativa = self.dry_run()
            if verbose:
                print(estimativa)
            if estimativa.gigabytes > max_gb:
                raise QueryTooLargeError(
                    f"a consulta varreria {estimativa.gigabytes:.2f} GB, acima do "
                    f"teto de {max_gb:.2f} GB "
                    f"(US$ {estimativa.usd_sem_franquia:.2f} sem franquia).\n"
                    f"Reduza o recorte (menos UFs, menos colunas) ou, se for "
                    f"mesmo o que você quer, chame get_data(max_gb=...) com um "
                    f"teto maior.\n\nQuery:\n{sql}"
                )

        from google.cloud import bigquery

        job_config = bigquery.QueryJobConfig(
            maximum_bytes_billed=(
                None if max_gb is None else int(max_gb * 1024 ** 3)
            )
        )
        return self._client().query(sql, job_config=job_config).to_dataframe()


def inspect_schema(billing_project_id, from_file=False):
    """
    Lista (column_name, data_type) da tabela de microdados. RODE ISSO PRIMEIRO
    para conferir os nomes em columns.py contra o seu ambiente.

    Consultas ao INFORMATION_SCHEMA não varrem as tabelas de dados, então esta
    chamada é essencialmente gratuita.

    ATENÇÃO: isto responde "quais colunas existem e de que tipo", e **não** o
    que cada uma significa. Nome e tipo corretos não garantem que `vd4019` seja
    rendimento habitual e não efetivo. A conferência semântica exige o
    dicionário oficial da PNADC do ano usado.
    """
    import basedosdados as bd

    sql = (
        "SELECT column_name, data_type\n"
        "FROM `basedosdados.br_ibge_pnadc.INFORMATION_SCHEMA.COLUMNS`\n"
        "WHERE table_name = 'microdados'\n"
        "ORDER BY ordinal_position"
    )
    return bd.read_sql(sql, billing_project_id=billing_project_id,
                       from_file=from_file)
