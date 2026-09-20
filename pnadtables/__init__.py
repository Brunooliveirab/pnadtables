"""
pnadtables — tarefas de fairness com API inspirada no folktables, definidas sobre
a PNAD Contínua (IBGE) e acessadas via Base dos Dados / BigQuery.

PRÉ-RELEASE NÃO VALIDADO: nenhuma consulta real à PNADC foi executada; nomes de
coluna e domínios em `columns.py` ainda não foram conferidos contra o dicionário
oficial do IBGE. Ver a seção "Status" do README antes de publicar qualquer número.

Exemplo mínimo:
    from pnadtables import PNADCDataSource, PNADEmployment, audit_report
    src = PNADCDataSource(billing_project_id="seu-projeto", ano=2024, trimestre=1)
    X, y, group, weight = PNADEmployment.df_to_pandas(src.get_data())

A tupla tem 4 elementos (o folktables devolve 3): o quarto é o peso amostral.
"""
from .data_source import PNADCDataSource, inspect_schema
from .problems import BasicProblem, PNADEmployment, PNADIncome, make_pnad_income
from .metrics import (
    audit_report,
    disparate_impact,
    selection_rates,
    rate_by_group,
)
from . import columns

__all__ = [
    "PNADCDataSource",
    "inspect_schema",
    "BasicProblem",
    "PNADEmployment",
    "PNADIncome",
    "make_pnad_income",
    "audit_report",
    "disparate_impact",
    "selection_rates",
    "rate_by_group",
    "columns",
]
