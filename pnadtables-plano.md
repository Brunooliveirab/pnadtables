# pnadtables — plano de validação, release e pesquisa

*Revisado em 20/09/2026. Este documento registra o estado verificável do projeto, os critérios de aceite da primeira release e o plano de pesquisa. Datas de conferências e afirmações de novidade devem ser confirmadas em fontes primárias antes de divulgação.*

---

## 1. Decisão executiva

O `pnadtables` é um pacote Python **inspirado na arquitetura do `folktables`** para definir tarefas de predição e auditoria de fairness sobre os microdados da PNAD Contínua. A contribuição pretendida combina:

1. tarefas brasileiras reproduzíveis, com definições explícitas de universo, features e alvo;
2. análise de sensibilidade à taxonomia de cor ou raça;
3. estimação ponderada e, para inferência populacional, tratamento adequado do desenho amostral;
4. avaliação de variação geográfica e temporal no Brasil.

O pacote **ainda não está pronto para release pública**. A lógica foi validada com dados sintéticos, mas o esquema, as categorias e o fluxo completo ainda não foram validados contra dados reais. A prioridade é produzir um baseline real e reproduzível antes de outreach, DOI ou PyPI.

### Definição de sucesso da primeira release

A `v0.1.0` só será taggeada quando uma pessoa externa puder instalar o pacote, executar uma consulta pequena e reproduzir um relatório de baseline com proveniência, testes e limitações documentadas.

---

## 2. Posicionamento científico

O [`folktables`](https://github.com/socialfoundations/folktables), associado a Ding, Hardt, Miller e Schmidt (*Retiring Adult*, NeurIPS 2021), oferece tarefas padronizadas sobre o American Community Survey. O `pnadtables` usa essa ideia como ponto de partida, mas **não é hoje um substituto compatível nem uma tradução direta**:

- o `folktables` retorna normalmente `(X, y, group)`; o `pnadtables` retorna `(X, y, group, weight)`;
- ACS e PNADC têm universos, periodicidade, variáveis e desenhos amostrais diferentes;
- categorias de raça/cor não são semanticamente intercambiáveis entre os países;
- equivalência de nomes de tarefas não implica equivalência de construtos.

Assim, a formulação correta é **“API e protocolo de benchmark inspirados no `folktables`, adaptados à PNADC”**. Uma comparação Brasil–EUA precisará de um protocolo de harmonização, não apenas da execução de tarefas com nomes semelhantes.

### Hipóteses de pesquisa

1. Resultados de fairness variam materialmente entre UFs, períodos e tarefas na PNADC.
2. O agrupamento binário `Preta + Parda = Negra` pode mudar rankings, gaps e conclusões em relação à análise multigrupo.
3. Ponderação amostral pode alterar estimativas pontuais de desempenho e fairness.
4. Conclusões obtidas no ACS podem não se reproduzir sob um protocolo PNADC harmonizado.

A afirmação de que não existe benchmark equivalente no Sul Global é, por enquanto, **hipótese de novidade**. Antes do paper e do outreach, fazer busca documentada em ACM DL, IEEE Xplore, Scopus/OpenAlex, arXiv e Google Scholar e registrar trabalhos relacionados, inclusive pacotes que não usam o termo `folktables`.

---

## 3. Escopo funcional da `v0.1.0`

| Tarefa | Referência conceitual | Universo proposto | Alvo proposto |
|---|---|---|---|
| `PNADEmployment` | `ACSEmployment` | pessoas com idade ≥ 14 | ocupado (`vd4002 == 1`) |
| `PNADIncome` | `ACSIncome` | ocupados, idade ≥ 14, renda habitual válida | renda habitual acima de corte parametrizado |

Features iniciais: idade, sexo, cor ou raça, escolaridade e UF. Cor ou raça é o primeiro atributo de auditoria. Sexo e interseções cor/raça × sexo entram no protocolo experimental, desde que haja tamanho amostral suficiente.

O pacote deve oferecer:

- definições versionadas de tarefa;
- carregamento por ano, trimestre e UF, com estimativa/limite de custo;
- codificação categórica determinística;
- saída tabular e metadados de proveniência;
- métricas ponderadas e não ponderadas;
- exemplos reprodutíveis e testes offline;
- aviso explícito de que o pacote serve a pesquisa e auditoria, não a decisões individuais.

Tarefas adicionais, documentação Sphinx/MkDocs, LIME, contrafactuais e integração regulatória ficam fora do caminho crítico da `v0.1.0`.

---

## 4. Estado atual verificado em 20/09/2026

O artefato completo estava em `pnadtables.zip`. **Em 20/09/2026 o G0 foi fechado**: a árvore foi descompactada como fonte do repositório, os metadados foram corrigidos e o repositório Git foi criado (privado, conforme o gate G7 mantém a publicidade para depois). O ZIP permanece na pasta, fora do controle de versão, apenas como registro do artefato original.

### Confirmado localmente

- o ZIP contém pacote, testes, CI, READMEs, datasheet, licença, `pyproject.toml` e `CITATION.cff`;
- `pytest -q`: **16 testes aprovados** com dados sintéticos (10 originais + 6 regressões do G0);
- `python -m build --no-isolation` + `twine check`: **sdist e wheel construídos e validados**;
- **CI verde no GitHub** (run 35528500869, 20/09/2026): testes em Python 3.9, 3.11 e 3.12 e job de build, todos aprovados;
- existe correção para evitar que `sigla_uf` vire uma coluna toda `NaN`;
- as métricas atuais aceitam `weight`.

### Ainda não demonstrado

- consulta real à Base dos Dados/BigQuery;
- validade dos nomes, tipos e categorias das variáveis em cada safra;
- compatibilidade do cliente `basedosdados` em ambiente limpo;
- baseline com dados reais;
- reprodutibilidade por uma segunda pessoa;
- publicação no Zenodo ou PyPI (o repositório Git já existe, privado).

### Inconsistências de metadados — corrigidas em 20/09/2026

- ~~`CITATION.cff` declara `date-released: 2026-09-18`, embora não exista release~~ → `date-released` removido; versão passou a `0.1.0.dev0` em `CITATION.cff` e `pyproject.toml`, com aviso de pré-release;
- ~~URLs presumem a organização `pnadtables`, ainda não confirmada~~ → todas apontam para `github.com/Brunooliveirab/pnadtables`;
- ~~o README descreve o contrato como igual ao `folktables`~~ → README explicita a tupla de 4 elementos e que código escrito para o `folktables` não desempacota isso sem alteração;
- ~~a regra dos 4/5 menciona razão `> 1.25`~~ → docstring de `disparate_impact` explica que o modo padrão (referência = grupo de maior taxa) limita as razões a (0, 1] e que 1.25 só vale com `reference` explícita; dois testes de regressão fixam esse contrato;
- ~~`raca_5grupos` também preserva `Ignorada`~~ → docstring explicita que 'Ignorada' (código 9) é não resposta e não uma sexta categoria; novo parâmetro `incluir_ignorada` e alias `raca_5grupos_sem_ignorada` deixam a escolha explícita.

Correções adicionais feitas no mesmo lote:

- `.gitignore` tinha `*.json   # GCP credentials` com comentário na mesma linha — sintaxe que o Git não interpreta, de modo que **credenciais `.json` não estavam sendo ignoradas**. Corrigido;
- README, README.pt-BR e DATASHEET deixaram de tratar peso amostral como "número final obrigatório" e de prometer custo zero no BigQuery; a afirmação de novidade virou hipótese explícita; o PL 2338/2023 aparece como proposta em tramitação;
- `example_audit.py` passou a declarar que é demonstração de API, não protocolo válido (split com vazamento, encoding instável, SHAP ilustrativo);
- suíte de testes passou de 10 para 16 casos; `python -m build` + `twine check` passam.

---

## 5. Bloqueadores metodológicos e técnicos

### 5.1 Esquema e semântica dos dados

Rodar `inspect_schema()` não basta. Para cada ano suportado, comparar nomes, tipos, domínios e missingness com o dicionário oficial do IBGE. Criar um teste de integração pequeno que valide pelo menos:

- `ano`, `trimestre`, UF e identificadores de domicílio/pessoa;
- idade, sexo, cor ou raça e escolaridade;
- condição de ocupação e rendimento;
- peso, estrato e UPA necessários ao desenho amostral;
- valores especiais, categorias ignoradas e mudanças entre safras.

O código não deve converter alvo ausente silenciosamente em classe negativa. Linhas com alvo, peso ou features essenciais inválidos precisam de política explícita e contagens antes/depois de cada filtro.

### 5.2 Desenho amostral

`v1028` permite estimativas pontuais ponderadas, mas **peso sozinho não representa todo o desenho amostral complexo**. A PNADC usa estratificação e conglomerados em estágios; inferência populacional e intervalos de confiança exigem estrato/UPA e método apropriado. A documentação do [IBGE descreve o desenho por estratos, UPAs e domicílios](https://www.ibge.gov.br/biblioteca/visualizacao/livros/liv101640.pdf).

Para a primeira release:

- distinguir “métrica ponderada” de “inferência survey-aware”;
- incluir identificadores de desenho quando disponíveis;
- reportar intervalos de confiança por procedimento adequado ou declarar que a `v0.1.0` oferece apenas estimativas pontuais;
- sempre mostrar resultados ponderados e não ponderados como análise de sensibilidade, sem declarar um deles universalmente correto para todo objetivo algorítmico.

### 5.3 Codificação de features

`pd.factorize()` depende dos valores e da ordem observada. Isso pode atribuir códigos diferentes a UFs em execuções, períodos ou subconjuntos distintos. Além disso, sexo, raça e UF não devem ganhar sem justificativa uma geometria ordinal.

Substituir a codificação atual por uma destas opções:

- retornar categorias tipadas e deixar o pipeline do modelo fazer `OneHotEncoder(handle_unknown="ignore")`; ou
- manter vocabulários versionados e determinísticos no pacote.

O encoder deve ser ajustado apenas no treino e aplicado sem refit ao teste. Produzir baselines com e sem o atributo protegido entre as features, mantendo-o sempre para auditoria.

### 5.4 Validação de entradas e métricas

Adicionar validação de comprimentos, valores binários, `NaN`, pesos negativos/zerados, grupos vazios e denominadores nulos. Definir explicitamente:

- grupo de referência;
- diferença e razão de taxas;
- TPR, FPR, precision, calibration e desempenho global/por grupo;
- tamanho amostral bruto e soma dos pesos;
- intervalos de confiança e regra para grupos pequenos.

A regra dos 4/5 é uma heurística contextual, não um diagnóstico jurídico automático. A documentação deve dizer isso.

### 5.5 Particionamento e vazamento

Evitar split aleatório ingênuo por pessoa. Pessoas do mesmo domicílio são correlacionadas e a PNADC possui rotação de domicílios. O protocolo deve priorizar:

- split agrupado por domicílio quando houver um único trimestre;
- split temporal para avaliar mudança entre trimestres/anos;
- split geográfico para avaliar transferência entre UFs/regiões;
- identificação da mesma unidade ao combinar ondas, evitando sua presença em treino e teste.

### 5.6 Comparação com ACS

Antes de afirmar reprodução ou divergência, criar uma tabela de harmonização contendo construto, universo, janela de renda, features, categorias, unidade geográfica, desenho amostral e métrica. Diferenças devem ser interpretadas como combinação de contexto social, medição e modelagem — não automaticamente como efeito de país.

---

## 6. Protocolo experimental mínimo

### Dados

- uma safra principal congelada, com ano/trimestre/UFs e data de acesso;
- um recorte temporal ou geográfico fora da amostra para shift;
- manifesto com query SQL, hash do código, versões das dependências e contagens após cada filtro;
- cache local opcional sem redistribuir microdados, respeitando termos aplicáveis.

### Modelos

- baseline de maioria;
- regressão logística com preprocessing explícito;
- um modelo de árvores/boosting;
- mesmas seeds e divisões para todas as variantes.

SHAP/LIME não é requisito do primeiro benchmark. Explicabilidade só entra quando houver pergunta de pesquisa e protocolo de avaliação próprios; um ranking SHAP isolado não sustenta conclusão sobre “direito à explicação”.

### Relatório

- desempenho global e por grupo;
- seleção, TPR, FPR, precision e calibration por grupo;
- diferenças e razões com incerteza;
- versões ponderada e não ponderada;
- taxonomia multigrupo e binária, com exclusões quantificadas;
- análise com e sem atributos protegidos nas features;
- resultados por pelo menos um recorte temporal ou geográfico;
- limitações e testes de robustez.

---

## 7. Gates de release

| Gate | Critério de aceite | Estado |
|---|---|---|
| G0 — fonte | ZIP descompactado em repositório Git; URLs e autoria corretas; nenhum segredo | ✅ 20/09/2026 |
| G1 — dados | esquema e domínios confirmados; consulta pequena real; fixture anonimizada/sintética representativa | ⬜ |
| G2 — correção | encoding determinístico; missingness e validação de pesos; testes de integração | ⬜ |
| G3 — metodologia | splits sem vazamento; protocolo de peso/desenho; métricas e incerteza definidos | ⬜ |
| G4 — evidência | notebook/script reproduzível com baseline real e tabela no README | ⬜ |
| G5 — engenharia | testes em Python suportado, build e instalação limpa passam no CI | 🟨 CI verde 20/09/2026; falta instalação limpa com `basedosdados` |
| G6 — documentação | datasheet completo, limitações, proveniência, licenças/termos verificados | ⬜ |
| G7 — publicação | repo público, tag `v0.1.0`, release arquivada e DOI | ⬜ |
| G8 — distribuição | publicação no PyPI e teste de `pip install pnadtables` | ⬜ |

O CI verde fecha a parte de testes do G5, mas **o gate continua aberto**: falta verificar que `basedosdados>=2.0` instala em ambiente limpo em todas as versões declaradas de Python e que a instalação a partir do wheel/sdist funciona com import e uso mínimo. O CI atual roda offline com o stub de `tests/conftest.py`, então ele não é evidência sobre o cliente real nem sobre o esquema (G1).

---

## 8. Reprodutibilidade, custos e enquadramento jurídico

O pacote não pretende redistribuir microdados, mas isso **não autoriza concluir genericamente “sem impedimento”**. Antes da release, registrar:

- licença do código do pacote;
- termos e atribuição do IBGE e da Base dos Dados;
- regras de acesso, uso e eventual cache;
- privacy statement e proibição de reidentificação;
- finalidade de pesquisa e limitação contra uso decisório individual.

O PL 2338/2023 não deve ser descrito como obrigação vigente: em 20/09/2026, a [ficha oficial da Câmara](https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao=2487262) o apresenta em tramitação. A relação com LGPD, explicação e auditoria deve ser tratada como pergunta jurídica separada, com fontes e revisão especializada.

O BigQuery oferece franquia mensal para consultas sob certas condições, mas custo não deve ser prometido como zero. A documentação oficial recomenda estimar bytes e usar limites de cobrança; ver [controle de custos do BigQuery](https://docs.cloud.google.com/bigquery/docs/best-practices-costs). O pacote deve oferecer dry run ou instrução equivalente e `maximum_bytes_billed` quando a biblioteca permitir.

---

## 9. Estratégia de publicação e outreach

### Pré-condições para contato

Iniciar outreach somente depois de G0–G5. O link enviado deve abrir um repositório com instalação funcional, baseline real, limitações claras e issue curta descrevendo a colaboração desejada.

### Quem procurar

1. autores de trabalhos que usam `folktables` e discutem validade externa, dataset shift ou limites culturais/geográficos;
2. pesquisadores brasileiros de fairness, ML responsável, estatística amostral e desigualdade racial;
3. especialistas em PNADC capazes de revisar variáveis, universos e desenho amostral;
4. pesquisadores jurídicos apenas quando existir uma pergunta jurídica delimitada.

Priorizar aderência temática e contribuição complementar, não suposta probabilidade de carta. Coautoria e recomendação são resultados possíveis de trabalho substantivo, não marcos que o cronograma possa garantir.

### Mensagem

E-mail curto com: problema; evidência já produzida; link para repo e baseline; uma lacuna técnica específica na qual a pessoa pode contribuir; pedido de conversa de 20 minutos. Fazer contatos em pequenos lotes e ajustar a mensagem conforme respostas.

### Venue

Preparar um paper de dataset/benchmark com contribuição metodológica. FAccT, AIES, EAAMO, NeurIPS Datasets & Benchmarks e venues brasileiros são candidatos, mas trilhas, escopo e deadlines de 2027 devem ser consultados nas chamadas oficiais antes de entrarem no cronograma.

---

## 10. Cronograma operacional

| Prazo | Entrega |
|---|---|
| ~~23/09/2026~~ ✅ 20/09/2026 | G0: promover o ZIP a repositório, corrigir metadados e abrir lista de issues |
| 30/09/2026 | G1: validar esquema/domínios e executar consulta real pequena |
| 07/10/2026 | G2: corrigir encoding, missingness, validação e testes de integração |
| 14/10/2026 | G3: fechar protocolo de splits, desenho amostral, métricas e incerteza |
| 28/10/2026 | G4: baseline real reproduzível e tabela no README |
| 04/11/2026 | G5–G6: CI limpo, instalação externa e datasheet revisado |
| 11/11/2026 | G7: release pública e DOI; iniciar outreach em lotes |
| nov–dez/2026 | literatura relacionada, experimentos de shift e rascunho do paper |

Se uma etapa metodológica falhar, a release é adiada; a data não reduz o critério de aceite. PyPI (G8) pode ocorrer junto de G7 ou depois, sem bloquear o primeiro contato se a instalação via Git estiver validada.

---

## 11. Registro de riscos

| Risco | Impacto | Mitigação |
|---|---|---|
| Variáveis/categorias incorretas | invalida tarefas e resultados | dicionário oficial + teste real por safra |
| Peso tratado como desenho completo | falsa precisão | estrato/UPA, incerteza survey-aware ou ressalva explícita |
| Encoding instável/ordinal | resultados não reproduzíveis | pipeline categórico determinístico ajustado no treino |
| Vazamento por domicílio/onda | desempenho inflado | splits agrupados, temporais e geográficos |
| Grupos pequenos | métricas instáveis/exposição indevida | limiar de reporte, incerteza e supressão responsável |
| Comparabilidade ACS–PNADC fraca | conclusão causal indevida | tabela de harmonização e linguagem descritiva |
| Novidade superestimada | enfraquece paper/outreach | revisão sistemática de trabalhos relacionados |
| Custo de consulta | cobrança inesperada | projeção de bytes, limites e recortes pequenos |
| Dependência da Base dos Dados | quebra de esquema/disponibilidade | versões, contrato de schema e caminho alternativo oficial |
| Enquadramento jurídico excessivo | claims incorretos | separar benchmark técnico de análise jurídica especializada |

---

## 12. Próximas cinco ações

1. ~~Descompactar o artefato como fonte do repositório e remover a falsa data de release.~~ ✅ 20/09/2026
2. **Próxima ação bloqueante:** obter credenciais/projeto de billing e validar esquema, domínios e uma amostra real pequena.
3. Corrigir encoding categórico, missingness, validação de pesos e documentação do contrato.
4. Definir identificadores de domicílio, estrato e UPA e implementar splits sem vazamento.
5. Produzir um baseline real reproduzível antes de abrir o repositório para outreach.
