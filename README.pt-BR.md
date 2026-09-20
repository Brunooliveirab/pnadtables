# pnadtables

Tarefas de *fairness* com API inspirada no
[folktables](https://github.com/socialfoundations/folktables), definidas sobre a
**PNAD Contínua** (IBGE) e acessadas via **Base dos Dados** / BigQuery.

## Status — pré-release, ainda não validado com dados reais

A versão `0.1.0.dev0` é um esqueleto funcional: 10 testes offline passam com dados
sintéticos, mas **nenhuma consulta real à PNADC foi executada**. Nomes de coluna, tipos,
domínios de valor e o fluxo ponta a ponta continuam não verificados contra o dicionário
oficial do IBGE. Não há release, tag nem DOI. Os gates pendentes (G1–G8) estão em
[`pnadtables-plano.md`](pnadtables-plano.md) e no README em inglês.

Uso pretendido: pesquisa e auditoria de sistemas algorítmicos — **não** decisões sobre
pessoas individuais.

## Estrutura
```
pnadtables/
├── columns.py      # ÚNICA fonte de verdade dos nomes de coluna + mapas de cor/raça
├── data_source.py  # PNADCDataSource (query na BD/BigQuery) + inspect_schema()
├── problems.py     # BasicProblem + PNADEmployment, PNADIncome
└── metrics.py      # razão de taxas, TPR/FPR por grupo — com peso amostral
example_audit.py    # ponta a ponta: dados -> modelo -> auditoria -> SHAP
DATASHEET.md        # decisões metodológicas (cor/raça, peso)
```

## Setup
```bash
pip install basedosdados pandas numpy scikit-learn
pip install shap   # opcional, para a etapa de explicabilidade
```
É preciso um projeto no Google Cloud (`billing_project_id`). **A consulta é cobrada de quem
a executa** — não há servidor nem hospedagem deste projeto: você instala o pacote e consulta
a tabela pública por conta própria.

`get_data()` nunca executa às cegas: faz antes um **dry run** (gratuito, não lê dado algum),
mostra quantos bytes a consulta varreria e recusa se passar de `max_gb`. O mesmo teto vai
como `maximum_bytes_billed` para o BigQuery, que aborta do lado do servidor se a estimativa
estiver errada.

```python
print(src.dry_run())            # gratuito: quanto custaria
df = src.get_data()             # recusa acima de DEFAULT_MAX_GB (5 GB)
df = src.get_data(max_gb=20)    # eleva o teto deliberadamente
df = src.get_data(max_gb=None)  # desativa as duas proteções
```

Ordem de grandeza: o BigQuery cobra **US$ 6,25 por TiB varrido**, com **1 TiB por mês
gratuito** por conta de faturamento. Um trimestre com as 11 colunas de `DEFAULT_COLUMNS`
fica na casa de dezenas de MB. Confirme com `dry_run()` em vez de confiar na estimativa, e
configure um limite de cobrança no projeto de qualquer forma.

## Passo a passo
```python
from pnadtables import inspect_schema
# 1) CONFIRME os nomes de coluna antes de tudo — contra o seu ambiente E contra
#    o dicionário oficial do IBGE da safra que você vai usar:
print(inspect_schema(billing_project_id="seu-projeto"))
#    Ajuste columns.py se algo divergir.

from pnadtables import PNADCDataSource, PNADEmployment, audit_report
# 2) Carregue e construa a tarefa:
src = PNADCDataSource("seu-projeto", ano=2024, trimestre=1, ufs=["MT","SP"])
X, y, group, weight = PNADEmployment.df_to_pandas(src.get_data())
# Tupla de 4 elementos: o folktables devolve (X, y, group); aqui há o peso amostral
# a mais. Código escrito para o folktables NÃO desempacota isso sem alteração.
```
Ou rode o exemplo completo (ajuste `BILLING_PROJECT_ID` no topo):
```bash
python example_audit.py
```

## Notas rápidas
- **Cor ou raça**: rode em `raca_5grupos` *e* `raca_branca_negra` (Preta+Parda) e
  quantifique quantas linhas cada colapso exclui. `raca_5grupos` preserva 'Ignorada'
  (código 9, não resposta) por padrão; use `incluir_ignorada=False` para restringir às
  5 categorias. Ver DATASHEET.
- **Peso**: `weight` dá estimativa pontual ponderada, **não** inferência survey-aware.
  Estrato e UPA ainda não estão implementados, então este pacote não produz intervalo de
  confiança correto. Reporte ponderado *e* não ponderado como análise de sensibilidade;
  nenhum dos dois é universalmente o número final.
- **Split**: evite split aleatório ingênuo — pessoas do mesmo domicílio são correlacionadas
  e a PNADC tem rotação de domicílios. Splits agrupados/temporais/geográficos são o gate G3.
- **Corte de renda** (`PNADIncome`): é parâmetro — ajuste ao ano de referência.
- **Regra dos 4/5**: heurística contextual de triagem, não diagnóstico jurídico automático.
- **Enquadramento jurídico**: o PL 2338/2023 está em tramitação, não é obrigação vigente.
  A relação com LGPD, explicação e auditoria é pergunta jurídica separada, que exige
  fontes primárias e revisão especializada — não trate como premissa deste pacote.
- Trocar de fonte para a **RAIS** muda o viés (censo administrativo formal, sem
  informalidade).
