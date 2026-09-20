# Datasheet — Benchmark de fairness derivado da PNAD Contínua (`pnadtables`)

Estrutura baseada em *Datasheets for Datasets* (Gebru et al., 2021) — a mesma
referência adotada pelo folktables. Documenta as **escolhas** por trás das
tarefas, não só os dados. Os trechos marcados com ⚠️ são decisões metodológicas
com implicações jurídicas e devem ser citadas explicitamente no artigo.

> ⚠️ **Estado em 20/09/2026: pré-release não validado.** Nenhuma consulta real à
> PNADC foi executada. Nomes de coluna, tipos, domínios de valor e rótulos abaixo
> são *propostos* e ainda não conferidos contra o dicionário oficial do IBGE de
> cada safra (gate G1). Este datasheet descreve o desenho pretendido, não um
> artefato verificado.

> Observação: este benchmark é derivado da PNAD Contínua (IBGE), acessada via
> Base dos Dados. Ele **não** substitui investigação substantiva sobre
> desigualdade — serve para *benchmarking* de algoritmos de fairness e
> explicabilidade, espelhando a ressalva análoga feita pelos autores do folktables.
> Não deve ser usado para decisões sobre pessoas individuais.

---

## 1. Motivação

**Para que o conjunto foi criado?** Para dar à literatura de fair ML e à
discussão regulatória brasileira um análogo nacional ao folktables: tarefas de
predição reprodutíveis, com atributo protegido bem definido, sobre microdados
oficiais. Permite (a) auditoria de viés no estilo folktables e, potencialmente,
(b) avaliação empírica de métodos de explicabilidade (SHAP, LIME, contrafactuais).

⚠️ O eixo jurídico é uma **pergunta separada, ainda em aberto**, não uma premissa
deste pacote. O PL 2338/2023 está em tramitação e não é obrigação vigente; a
relação com a LGPD, com "direito à explicação" e com o padrão norte-americano de
*adverse action* (FCRA/ECOA) exige fontes primárias e revisão especializada.
Explicabilidade só entra no benchmark quando houver pergunta de pesquisa e
protocolo de avaliação próprios — um ranking SHAP isolado não sustenta conclusão
jurídica alguma.

**Quem criou e financiou?** [Bruno e Letícia — preencher afiliação]. Os
microdados são produzidos pelo IBGE; a camada de acesso tratado é mantida pela
Base dos Dados.

## 2. Composição

**O que cada instância representa?** Uma pessoa entrevistada na PNAD Contínua,
em idade de trabalhar (14+), num dado ano/trimestre.

**Quantas instâncias?** Variável conforme o recorte (ano, trimestre, UFs).
Documente o recorte exato usado em cada experimento.

**Tarefas pré-definidas:**
- **PNADEmployment** (análogo de ACSEmployment): prever se a pessoa está ocupada
  (`vd4002 == 1`). Universo: população em idade de trabalhar (14+).
- **PNADIncome** (análogo de ACSIncome): prever se o rendimento mensal habitual
  (`vd4019`) supera um corte. Universo: ocupados, 14+, renda > 0.

**Features:** idade (`v2009`), sexo (`v2007`), cor/raça (`v2010`), nível de
instrução (`vd3004`), UF (`sigla_uf`).

**Atributo protegido:** cor ou raça (`v2010`).

**Há dados faltantes?** Sim (ex.: renda só para ocupados; raça "Ignorada").
Tratados conforme cada tarefa; o modelo de exemplo (`HistGradientBoosting`)
lida com NaN nativamente.

**Há rótulos sensíveis?** Sim — raça/cor e sexo. Os microdados são públicos e
anonimizados pelo IBGE; não se deve tentar reidentificar pessoas.

## 3. ⚠️ Atributo protegido: a categoria "cor ou raça" não é traduzível 1:1

Esta é a decisão analítica central e o coração da contribuição comparativa.

- O IBGE classifica `v2010` em cinco categorias autodeclaradas — **Branca,
  Preta, Amarela, Parda, Indígena** (+ Ignorada) —, construto distinto das
  categorias de raça do *Census* dos EUA que o folktables usa.
- `pnadtables` oferece **duas** codificações:
  - `raca_5grupos`: preserva as cinco categorias **mais 'Ignorada'** (código 9,
    que é não resposta, não uma sexta cor ou raça) para auditoria multigrupo;
    `incluir_ignorada=False` restringe às cinco categorias;
  - `raca_branca_negra`: colapsa **Preta + Parda = Negra** vs **Branca**,
    excluindo Amarela/Indígena/Ignorada. ⚠️ Reporte sempre quantas linhas essa
    exclusão remove, em contagem bruta e em soma de pesos.
- ⚠️ O colapso binário **embute uma teoria** sobre a estrutura racial brasileira
  (a categoria *parda* e o critério de autodeclaração). Ele facilita o paralelo
  com o framing privilegiado/desprivilegiado do folktables, mas é uma escolha,
  não um dado. **Reporte resultados nas duas codificações** e discuta a
  divergência — é exatamente onde o eixo jurídico (discriminação, opacidade
  algorítmica) encontra o eixo técnico.

## 4. ⚠️ Coleta e desenho amostral

- A PNADC é **amostra complexa**: pesos, estratificação e conglomerados em
  estágios. `pnadtables` carrega o peso calibrado (`v1028`) e as métricas em
  `metrics.py` aceitam `weight`.
- ⚠️ **Peso não é o desenho amostral completo.** `weight` produz estimativas
  pontuais ponderadas; inferência populacional e intervalos de confiança exigem
  estrato e UPA, que esta versão ainda **não** carrega. Não reporte IC a partir
  das métricas atuais (gate G3).
- ⚠️ Nenhuma das versões é universalmente "a certa". Métricas não ponderadas
  descrevem a amostra; ponderadas estimam a população. Para uma pergunta sobre o
  comportamento do modelo na amostra de treino/teste, a não ponderada pode ser a
  pertinente. **Reporte as duas como análise de sensibilidade** e explicite qual
  pergunta cada uma responde, em vez de declarar uma delas final.
- Alternativa de fonte: a **RAIS** (vínculos formais) é censo administrativo, não
  amostra — sem pesos, mas exclui o trabalho informal (enorme no Brasil). É outro
  viés, de natureza diferente. Documente qual fonte foi usada e por quê.

## 5. Pré-processamento

- Valores vêm da Base dos Dados frequentemente como STRING; o pacote coage a
  numérico e codifica features categóricas de texto (ex.: UF).
- ⚠️ **Limitação conhecida (gate G2):** a codificação atual usa `pd.factorize()`,
  cujos códigos dependem dos valores e da ordem observada. UFs podem receber
  códigos diferentes entre execuções, períodos ou subconjuntos, e sexo/cor-raça/UF
  ganham uma geometria ordinal sem justificativa. Substituir por categorias
  tipadas com `OneHotEncoder(handle_unknown="ignore")` ajustado só no treino, ou
  por vocabulários versionados e determinísticos no pacote.
- ⚠️ **Missingness:** alvo ausente não deve virar classe negativa em silêncio.
  Definir política explícita e reportar contagens antes e depois de cada filtro.
- Filtros de universo (idade, ocupação, renda > 0) ficam explícitos em
  `problems.py::preprocess`.
- O corte de renda de `PNADIncome` é **parâmetro** (padrão ~2× salário mínimo de
  2025). ⚠️ Ajuste ao ano de referência: o corte redefine quem é "positivo" e,
  portanto, todas as métricas de fairness.

## 6. Usos

**Usos pretendidos:** benchmarking de algoritmos de fairness e de métodos de
explicabilidade; estudo comparado de padrões regulatórios.

**Usos a evitar:** conclusões substantivas sobre desigualdade baseadas só neste
benchmark; reidentificação de indivíduos.

## 7. Distribuição e manutenção

- Os microdados originais são públicos (IBGE); o acesso tratado é da Base dos
  Dados (BigQuery). O pacote `pnadtables` apenas define tarefas e métricas sobre
  eles.
- **Versionamento de reprodutibilidade:** registre, para cada experimento,
  (ano, trimestre, UFs), a versão da tabela na BD, a query SQL, as versões das
  dependências e o `git hash` do `columns.py`, já que nomes e variáveis derivadas
  podem mudar entre safras do IBGE.
- ⚠️ **Particionamento (gate G3):** pessoas do mesmo domicílio são correlacionadas
  e a PNADC tem rotação de domicílios. Split aleatório ingênuo por pessoa infla o
  desempenho. Usar split agrupado por domicílio, temporal ou geográfico; ao
  combinar ondas, impedir que a mesma unidade apareça em treino e teste.
- **Termos de uso e licenças (gate G6):** licença do código, termos e atribuição
  do IBGE e da Base dos Dados, regras de cache e proibição de reidentificação
  precisam ser registrados e verificados antes de qualquer publicação.

---

### Verificação obrigatória antes de publicar números
1. Rodar `inspect_schema()` e confirmar todos os nomes em `columns.py`.
2. Conferir os rótulos de `vd3004` (instrução) no dicionário do ano usado.
3. Confirmar que `v1028` é o peso calibrado na sua safra (senão, ajustar).
4. Reportar resultados em `raca_5grupos` **e** `raca_branca_negra`, com as
   exclusões quantificadas.
5. Reportar métricas ponderadas **e** não ponderadas, sem tratar uma delas como
   número final universal.
6. Usar split sem vazamento (domicílio, tempo ou geografia), não split aleatório.
