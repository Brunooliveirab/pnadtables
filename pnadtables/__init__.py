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

CUSTO: no BigQuery a consulta é cobrada de quem consulta. `get_data()` estima
os bytes por dry run (gratuito) e recusa a consulta acima de um teto. Ver
`data_source` para detalhes.
"""
from .data_source import (
    PNADCDataSource,
    inspect_schema,
    CostEstimate,
    QueryTooLargeError,
    DEFAULT_MAX_GB,
)
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
    "CostEstimate",
    "QueryTooLargeError",
    "DEFAULT_MAX_GB",
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
