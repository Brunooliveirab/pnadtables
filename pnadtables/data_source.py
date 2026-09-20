"""
Fonte de dados: consulta a PNAD Contínua no BigQuery público da Base dos Dados.

Pré-requisitos:
    pip install basedosdados pandas
    Um projeto no Google Cloud (billing_project_id) — a consulta é cobrada
    no SEU projeto, mas a BD oferece ~1 TB/mês grátis. Os dados em si são
    públicos.

Uso típico:
    from pnadtables.data_source import PNADCDataSource, inspect_schema
    src = PNADCDataSource(billing_project_id="seu-projeto", ano=2024,
                          trimestre=1, ufs=["MT", "SP"])
    df = src.get_data()
"""
from __future__ import annotations

import basedosdados as bd

from . import columns as C

# Colunas mínimas para as tarefas atuais. Adicione aqui se criar novas tarefas.
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


class PNADCDataSource:
    def __init__(self, billing_project_id, ano, trimestre, ufs=None,
                 columns=None):
        self.billing_project_id = billing_project_id
        self.ano = int(ano)
        self.trimestre = int(trimestre)
        self.ufs = list(ufs) if ufs else None
        self.columns = columns or DEFAULT_COLUMNS

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

    def get_data(self):
        """Executa a query e devolve um DataFrame pandas (valores como vieram da BD)."""
        return bd.read_sql(self._build_query(),
                           billing_project_id=self.billing_project_id)


def inspect_schema(billing_project_id):
    """
    Lista (column_name, data_type) da tabela de microdados. RODE ISSO PRIMEIRO
    para conferir os nomes em columns.py contra o seu ambiente.
    """
    sql = (
        "SELECT column_name, data_type\n"
        "FROM `basedosdados.br_ibge_pnadc.INFORMATION_SCHEMA.COLUMNS`\n"
        "WHERE table_name = 'microdados'\n"
        "ORDER BY ordinal_position"
    )
    return bd.read_sql(sql, billing_project_id=billing_project_id)
