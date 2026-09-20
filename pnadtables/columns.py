"""
Mapa de colunas e categorias da PNAD Contínua na Base dos Dados (BD).

CONVENÇÃO DA BD
---------------
A Base dos Dados padroniza apenas as colunas de identificação/geografia
(ano, trimestre, sigla_uf, ...) e PRESERVA os códigos de variável do IBGE
em minúsculas (v2007, v2009, v2010, vd4002, ...).

>>> ANTES DE RODAR <<<
Os nomes derivados (vd...) variam menos, mas confirme tudo com
`pnadtables.data_source.inspect_schema(...)`. Se algum nome divergir no seu
ambiente, ajuste SOMENTE este arquivo — o resto do pacote lê daqui.

Referências dos códigos: dicionário oficial da PNADC (IBGE) e tabela
`basedosdados.br_ibge_pnadc.microdados` no BigQuery público.
"""

# Caminho da tabela no BigQuery público da Base dos Dados
BQ_TABLE = "basedosdados.br_ibge_pnadc.microdados"

# --- Identificação / geografia (padronizadas pela BD) ---
COL_ANO = "ano"
COL_TRIMESTRE = "trimestre"
COL_UF = "sigla_uf"

# --- Peso amostral ---
# v1028 = peso com pós-estratificação/calibração (use este nas métricas ponderadas).
# v1027 = peso sem calibração. Confirme qual existe na sua versão da tabela.
COL_PESO = "v1028"

# --- Variáveis de pessoa (códigos IBGE preservados, minúsculos) ---
COL_SEXO = "v2007"        # 1 Homem, 2 Mulher
COL_IDADE = "v2009"       # idade em anos
COL_RACA = "v2010"        # 1 Branca 2 Preta 3 Amarela 4 Parda 5 Indígena 9 Ignorada
COL_INSTRUCAO = "vd3004"  # nível de instrução mais elevado alcançado (categórico)
COL_FORCA_TRAB = "vd4001" # 1 = na força de trabalho, 2 = fora da força de trabalho
COL_OCUPACAO = "vd4002"   # 1 = pessoa ocupada, 2 = pessoa desocupada
COL_RENDA_HAB = "vd4019"  # rendimento mensal habitual de todos os trabalhos (R$)

# Idade mínima da população em idade de trabalhar na PNADC (14 anos).
IDADE_TRABALHO = 14

# ---------------------------------------------------------------------------
# Identificadores de desenho amostral e de unidade.
#
# Necessários para inferência survey-aware (gate G3) e para splits sem
# vazamento (gate G3). NÃO entram em DEFAULT_COLUMNS ainda: primeiro é preciso
# confirmar que existem com esses nomes na tabela da Base dos Dados, que
# padroniza parte das colunas e preserva o resto em minúsculas.
# ---------------------------------------------------------------------------
COL_UPA = "upa"            # Unidade Primária de Amostragem — conglomerado
COL_DOMICILIO = "v1008"    # número de seleção do domicílio
COL_PAINEL = "v1014"       # painel (rotação de domicílios)
COL_ORDEM = "v2003"        # número de ordem da pessoa no domicílio

# Chave de domicílio na PNADC: a combinação abaixo, e não v1008 sozinho.
# É o que um split agrupado por domicílio precisa usar.
CHAVE_DOMICILIO = (COL_UPA, COL_DOMICILIO, COL_PAINEL)

# Pesos replicados V1028001..V1028200. O IBGE os fornece justamente para
# estimação de variância sob o desenho amostral complexo; são o caminho para
# intervalos de confiança corretos sem depender de estrato (que não existe
# como variável no dicionário trimestral).
N_PESOS_REPLICADOS = 200
COLS_PESO_REPLICADO = tuple(f"v1028{i:03d}" for i in range(1, N_PESOS_REPLICADOS + 1))

# ---------------------------------------------------------------------------
# Declarações verificáveis.
#
# Mapeia cada coluna que o pacote usa ao que ele ASSUME que ela significa.
# `scripts/validar_dicionario.py` confere isto contra o dicionário oficial da
# PNADC. Trechos esperados são minúsculos e sem acento, e a checagem é por
# substring — o objetivo é pegar troca de variável, não divergência redacional.
# ---------------------------------------------------------------------------
SIGNIFICADO_ESPERADO = {
    COL_PESO: "peso do domicilio e das pessoas",
    COL_SEXO: "sexo",
    COL_IDADE: "idade do morador",
    COL_RACA: "cor ou raca",
    COL_INSTRUCAO: "nivel de instrucao",
    COL_FORCA_TRAB: "condicao em relacao a forca de trabalho",
    COL_OCUPACAO: "condicao de ocupacao",
    COL_RENDA_HAB: "rendimento mensal habitual",
    COL_UPA: "unidade primaria de amostragem",
    COL_DOMICILIO: "numero de selecao do domicilio",
    COL_PAINEL: "painel",
    COL_ORDEM: "numero de ordem",
}

# ---------------------------------------------------------------------------
# Mapas de valor (códigos -> rótulos)
# ---------------------------------------------------------------------------
SEXO = {1: "Homem", 2: "Mulher"}

RACA_5 = {
    1: "Branca",
    2: "Preta",
    3: "Amarela",
    4: "Parda",
    5: "Indígena",
    9: "Ignorada",
}

# Nível de instrução (VD3004) — rótulos resumidos (confira o dicionário do ano).
INSTRUCAO = {
    1: "Sem instrução",
    2: "Fundamental incompleto",
    3: "Fundamental completo",
    4: "Médio incompleto",
    5: "Médio completo",
    6: "Superior incompleto",
    7: "Superior completo",
}


# ---------------------------------------------------------------------------
# Transformações do atributo protegido "cor ou raça"
#
# ATENÇÃO METODOLÓGICA: o colapso para um eixo binário branca x negra
# (Preta + Parda) é uma ESCOLHA analítica, não um dado bruto. Mantém
# paralelo com o framing privilegiado/desprivilegiado usado com o folktables,
# mas embute uma teoria sobre a estrutura racial brasileira. Documente isso
# no datasheet. As categorias Amarela/Indígena/Ignorada são removidas neste
# colapso — use `raca_5grupos` para auditoria multigrupo. Sempre quantifique
# e reporte quantas linhas cada colapso exclui.
# ---------------------------------------------------------------------------
def raca_5grupos(serie, incluir_ignorada=True):
    """
    Mapeia o código IBGE de cor ou raça para rótulos.

    ATENÇÃO AO NOME: a PNADC tem 5 categorias autodeclaradas (Branca, Preta,
    Amarela, Parda, Indígena) MAIS o código 9 = 'Ignorada', que não é uma
    sexta categoria de cor ou raça, e sim ausência de resposta.

    incluir_ignorada=True  (padrão): preserva 'Ignorada' como nível próprio,
        para que a não resposta seja contabilizada e reportada, não descartada
        em silêncio. O resultado tem, portanto, 6 níveis possíveis.
    incluir_ignorada=False: mapeia o código 9 para NaN, restringindo a saída
        às 5 categorias que o nome da função anuncia.

    Códigos fora de RACA_5 viram NaN nos dois modos.
    """
    out = serie.map(RACA_5)
    if not incluir_ignorada:
        out = out.where(out != "Ignorada")
    return out


def raca_5grupos_sem_ignorada(serie):
    """`raca_5grupos` restrita às 5 categorias; 'Ignorada' (código 9) -> NaN."""
    return raca_5grupos(serie, incluir_ignorada=False)


def raca_branca_negra(serie):
    """
    Colapso binário: 'Branca' (referência) vs 'Negra' (Preta + Parda).
    Demais categorias -> NaN (excluídas da auditoria binária).
    """
    mapa = {1: "Branca", 2: "Negra", 4: "Negra"}
    return serie.map(mapa)
