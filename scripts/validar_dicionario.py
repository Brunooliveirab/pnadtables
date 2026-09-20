#!/usr/bin/env python3
"""Confere columns.py contra o dicionário oficial da PNAD Contínua (IBGE).

Este script é a evidência do gate G1: ele responde se as variáveis que o pacote
declara usar são de fato o que o pacote afirma que elas são.

Por que existe
--------------
`inspect_schema()` diz quais colunas existem no BigQuery e de que tipo. Isso
não é a mesma pergunta. Nome e tipo corretos não garantem que `vd4019` seja
rendimento HABITUAL e não EFETIVO — só o dicionário oficial responde isso, e
uma troca dessas invalida silenciosamente todo resultado do benchmark.

Fonte
-----
O dicionário vem do FTP do IBGE, via `pnadium`. Não exige conta no Google
Cloud, credencial nem billing: é download público.

Uso
---
    pip install -e ".[validation]"
    python scripts/validar_dicionario.py                 # relatório no terminal
    python scripts/validar_dicionario.py --escrever      # grava docs/validacao-dicionario.md

Sai com código 1 se alguma variável declarada não for encontrada ou divergir,
para poder rodar em CI ou pre-commit.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pnadtables import columns as C  # noqa: E402

RELATORIO = Path(__file__).resolve().parent.parent / "docs" / "validacao-dicionario.md"


def normalizar(texto) -> str:
    """Minúsculas, sem acento e com espaços colapsados, para comparar."""
    texto = str(texto)
    sem_acento = "".join(
        ch for ch in unicodedata.normalize("NFD", texto)
        if unicodedata.category(ch) != "Mn"
    )
    return " ".join(sem_acento.lower().split())


def carregar_dicionario():
    """Baixa o dicionário oficial da PNADC trimestral e devolve {codigo: descricao}."""
    try:
        import pnadium
    except ImportError:  # pragma: no cover
        raise SystemExit(
            "pnadium não instalado. Rode: pip install -e '.[validation]'\n"
            "Ele baixa o dicionário do FTP público do IBGE — sem conta no GCP."
        )

    df = pnadium.consultar_variaveis(descricao="")
    return {
        str(linha["Código"]).strip().lower(): str(linha["Descrição"]).strip()
        for _, linha in df.iterrows()
    }


def conferir(dicionario: dict[str, str]) -> list[dict]:
    """Compara cada declaração de SIGNIFICADO_ESPERADO com o dicionário oficial."""
    resultados = []
    for codigo, esperado in sorted(C.SIGNIFICADO_ESPERADO.items()):
        oficial = dicionario.get(codigo.lower())
        if oficial is None:
            situacao, ok = "AUSENTE", False
        elif normalizar(esperado) in normalizar(oficial):
            situacao, ok = "confere", True
        else:
            situacao, ok = "DIVERGE", False
        resultados.append({
            "codigo": codigo,
            "esperado": esperado,
            "oficial": oficial or "—",
            "situacao": situacao,
            "ok": ok,
        })
    return resultados


def conferir_pesos_replicados(dicionario: dict[str, str]) -> tuple[int, bool]:
    """Confirma que os 200 pesos replicados existem (base da variância survey-aware)."""
    achados = sum(1 for col in C.COLS_PESO_REPLICADO if col.lower() in dicionario)
    return achados, achados == C.N_PESOS_REPLICADOS


def montar_relatorio(resultados, n_replicados, replicados_ok, total_dicionario) -> str:
    hoje = dt.date.today().isoformat()
    falhas = [r for r in resultados if not r["ok"]]

    linhas = [
        "# Validação de `columns.py` contra o dicionário oficial da PNADC",
        "",
        f"Gerado por `scripts/validar_dicionario.py` em {hoje}.",
        "",
        "Fonte: dicionário da PNAD Contínua trimestral, baixado do FTP público do "
        "IBGE via [`pnadium`](https://github.com/ggximenez/pnadium). "
        "Não requer conta no Google Cloud.",
        "",
        f"O dicionário desta safra declara **{total_dicionario} variáveis**.",
        "",
        "## Variáveis declaradas pelo pacote",
        "",
        "| Código | O pacote assume | Descrição oficial do IBGE | Situação |",
        "|---|---|---|---|",
    ]
    for r in resultados:
        marca = "✅" if r["ok"] else "❌"
        oficial = r["oficial"].replace("\n", " ").replace("|", "\\|")
        linhas.append(
            f"| `{r['codigo']}` | {r['esperado']} | {oficial} | {marca} {r['situacao']} |"
        )

    linhas += [
        "",
        "## Pesos replicados",
        "",
        f"Encontrados **{n_replicados} de {C.N_PESOS_REPLICADOS}** pesos replicados "
        f"(`V1028001`–`V1028{C.N_PESOS_REPLICADOS:03d}`). "
        + ("✅" if replicados_ok else "❌ contagem divergente."),
        "",
        "O IBGE fornece esses pesos para estimação de variância sob o desenho "
        "amostral complexo. São o caminho para intervalos de confiança corretos — "
        "e são necessários porque **não existe variável de estrato** no dicionário "
        "trimestral, apenas `UPA`.",
        "",
        "## Limites desta verificação",
        "",
        "Isto confere **nome e significado declarado** de cada variável. Não confere:",
        "",
        "- os domínios de valor (que `vd4002 == 1` seja mesmo *ocupado*, e não outro código);",
        "- os rótulos de `vd3004`, que dependem do dicionário do ano;",
        "- a distinção entre `v1027` e `v1028`, que têm descrição idêntica no dicionário;",
        "- se a tabela da Base dos Dados preserva esses nomes e valores na ingestão.",
        "",
        "Esses pontos exigem inspecionar os dados, não só o dicionário.",
        "",
    ]

    if falhas:
        linhas += [
            "## Pendências",
            "",
            *[f"- `{r['codigo']}`: {r['situacao'].lower()} — esperado "
              f"\"{r['esperado']}\", oficial \"{r['oficial']}\"" for r in falhas],
            "",
        ]

    return "\n".join(linhas)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--escrever", action="store_true",
                    help=f"grava o relatório em {RELATORIO.relative_to(RELATORIO.parent.parent)}")
    args = ap.parse_args()

    print("Baixando o dicionário oficial da PNADC do FTP do IBGE...")
    dicionario = carregar_dicionario()
    print(f"{len(dicionario)} variáveis no dicionário.\n")

    resultados = conferir(dicionario)
    n_rep, rep_ok = conferir_pesos_replicados(dicionario)

    largura = max(len(r["codigo"]) for r in resultados)
    for r in resultados:
        marca = "ok  " if r["ok"] else "FALHA"
        print(f"{marca} {r['codigo']:<{largura}}  {r['oficial'][:90]}")
    print(f"\npesos replicados encontrados: {n_rep}/{C.N_PESOS_REPLICADOS}")

    falhas = [r for r in resultados if not r["ok"]]
    if args.escrever:
        RELATORIO.parent.mkdir(parents=True, exist_ok=True)
        RELATORIO.write_text(
            montar_relatorio(resultados, n_rep, rep_ok, len(dicionario)),
            encoding="utf-8",
        )
        print(f"\nrelatório gravado em {RELATORIO}")

    if falhas or not rep_ok:
        print(f"\n{len(falhas)} divergência(s). Ajuste columns.py ou a declaração.")
        return 1
    print("\nTodas as declarações conferem com o dicionário oficial.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
