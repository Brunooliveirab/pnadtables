"""
Exemplo de ponta a ponta: PNADEmployment -> modelo -> auditoria de viés -> SHAP.

⚠️ ESTE ARQUIVO É DEMONSTRAÇÃO DE API, NÃO UM PROTOCOLO EXPERIMENTAL VÁLIDO.
Não use os números que ele imprime em nenhum resultado publicado. Limitações
deliberadas, todas pendentes nos gates do plano:

  - o split é aleatório por pessoa (G3). Pessoas do mesmo domicílio são
    correlacionadas e a PNADC tem rotação de domicílios: isso vaza informação
    entre treino e teste e infla o desempenho. O protocolo real precisa de split
    agrupado por domicílio, temporal ou geográfico;
  - a codificação de features usa `pd.factorize()` (G2), que não é determinística
    entre execuções/subconjuntos e impõe ordinalidade a UF/sexo/cor-raça;
  - a auditoria sai só na versão ponderada; o protocolo pede ponderada E não
    ponderada, e só com estimativa pontual — sem intervalo de confiança, porque
    estrato e UPA ainda não são carregados;
  - o ranking SHAP é ilustrativo. Sozinho, ele não sustenta nenhuma conclusão
    sobre "direito à explicação": esse é um tema jurídico separado, com o PL
    2338/2023 ainda em tramitação.

Rode:  python example_audit.py
(É preciso ter credenciais do Google Cloud configuradas e ter rodado
inspect_schema() para confirmar os nomes de coluna em columns.py. A consulta é
cobrada no seu projeto — estime os bytes e restrinja ano/trimestre/UF.)
"""
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import HistGradientBoostingClassifier  # lida com NaN nativamente

from pnadtables import PNADCDataSource, PNADEmployment, audit_report, columns

BILLING_PROJECT_ID = "seu-projeto-gcp"  # <-- ajuste


def main():
    # 1) Carrega a PNADC (ajuste ano/trimestre/UFs conforme sua janela de análise)
    src = PNADCDataSource(
        billing_project_id=BILLING_PROJECT_ID,
        ano=2024, trimestre=1, ufs=None,  # None = Brasil inteiro
    )
    df = src.get_data()

    # 2) Constrói a tarefa no estilo folktables: (X, y, grupo protegido, peso)
    X, y, group, weight = PNADEmployment.df_to_pandas(df)
    print(f"Amostra: {len(X)} pessoas | grupos: {group.value_counts().to_dict()}")

    # 3) Treina/testa — ⚠️ split aleatório por pessoa: vaza domicílio (ver aviso
    #    no topo do arquivo). Substituir por GroupShuffleSplit por domicílio.
    Xtr, Xte, ytr, yte, gtr, gte, wtr, wte = train_test_split(
        X, y, group, weight, test_size=0.3, random_state=42, stratify=group
    )
    clf = HistGradientBoostingClassifier(random_state=42)
    clf.fit(Xtr, ytr, sample_weight=wtr)  # peso amostral também no treino
    ypred = clf.predict(Xte)

    # 4) Auditoria de viés — PONDERADA pelo peso da PNADC
    rel = audit_report(yte.to_numpy(), ypred, gte.to_numpy(), weight=wte.to_numpy())
    print(f"\nGrupo de referência (maior taxa de seleção): {rel.attrs['referencia']}")
    print(rel.round(3))

    # 5) Gancho de explicabilidade: SHAP no modelo já treinado. Ilustrativo —
    #    ver o aviso no topo do arquivo sobre o que isso NÃO demonstra.
    try:
        import shap
        explainer = shap.Explainer(clf, Xtr.sample(min(500, len(Xtr)), random_state=1))
        sv = explainer(Xte.iloc[:200])
        importancia = np.abs(sv.values).mean(axis=0)
        ranking = sorted(zip(X.columns, importancia), key=lambda t: -t[1])
        print("\nImportância média |SHAP| por feature:")
        for nome, val in ranking:
            print(f"  {nome:>10}: {val:.4f}")
    except ImportError:
        print("\n(Instale `shap` para a etapa de explicabilidade: pip install shap)")


if __name__ == "__main__":
    main()
