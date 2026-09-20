# Validação de `columns.py` contra o dicionário oficial da PNADC

Gerado por `scripts/validar_dicionario.py` em 2026-09-20.

Fonte: dicionário da PNAD Contínua trimestral, baixado do FTP público do IBGE via [`pnadium`](https://github.com/ggximenez/pnadium). Não requer conta no Google Cloud.

O dicionário desta safra declara **420 variáveis**.

## Variáveis declaradas pelo pacote

| Código | O pacote assume | Descrição oficial do IBGE | Situação |
|---|---|---|---|
| `upa` | unidade primaria de amostragem | Unidade Primária de Amostragem (UPA) | ✅ confere |
| `v1008` | numero de selecao do domicilio | Número de seleção do domicílio | ✅ confere |
| `v1014` | painel | Painel | ✅ confere |
| `v1028` | peso do domicilio e das pessoas | Peso do domicílio e das pessoas | ✅ confere |
| `v2003` | numero de ordem | Número de ordem | ✅ confere |
| `v2007` | sexo | Sexo | ✅ confere |
| `v2009` | idade do morador | Idade do morador na data de referência | ✅ confere |
| `v2010` | cor ou raca | Cor ou raça | ✅ confere |
| `vd3004` | nivel de instrucao | Nível de instrução mais elevado alcançado (pessoas de 5 anos ou mais de idade) padronizado para o Ensino fundamental -  SISTEMA DE 9 ANOS | ✅ confere |
| `vd4001` | condicao em relacao a forca de trabalho | Condição em relação à força de trabalho na semana de referência para pessoas de 14 anos ou mais de idade | ✅ confere |
| `vd4002` | condicao de ocupacao | Condição de ocupação na semana de referência para pessoas de 14 anos ou mais de idade | ✅ confere |
| `vd4019` | rendimento mensal habitual | Rendimento mensal habitual de todos os trabalhos para pessoas de 14 anos ou mais de idade (apenas para pessoas que receberam em dinheiro, produtos ou mercadorias em qualquer trabalho) | ✅ confere |

## Pesos replicados

Encontrados **200 de 200** pesos replicados (`V1028001`–`V1028200`). ✅

O IBGE fornece esses pesos para estimação de variância sob o desenho amostral complexo. São o caminho para intervalos de confiança corretos — e são necessários porque **não existe variável de estrato** no dicionário trimestral, apenas `UPA`.

## Limites desta verificação

Isto confere **nome e significado declarado** de cada variável. Não confere:

- os domínios de valor (que `vd4002 == 1` seja mesmo *ocupado*, e não outro código);
- os rótulos de `vd3004`, que dependem do dicionário do ano;
- a distinção entre `v1027` e `v1028`, que têm descrição idêntica no dicionário;
- se a tabela da Base dos Dados preserva esses nomes e valores na ingestão.

Esses pontos exigem inspecionar os dados, não só o dicionário.
