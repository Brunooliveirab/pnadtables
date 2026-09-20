# pnadtables

[![CI](https://github.com/Brunooliveirab/pnadtables/actions/workflows/ci.yml/badge.svg)](https://github.com/Brunooliveirab/pnadtables/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Fairness benchmark tasks on Brazil's PNAD Contínua (IBGE), with an API inspired by
[folktables](https://github.com/socialfoundations/folktables).** Microdata are accessed
through **Base dos Dados** / BigQuery.

*Leia em [português](README.pt-BR.md).*

## Status — pre-release, not validated against real data

This package is **not ready for use in published results.** Version `0.1.0.dev0` is a
working skeleton: the logic passes 10 offline tests on synthetic PNADC-shaped data, but
the column names, value domains and end-to-end flow have **never been executed against a
real PNADC query**. No release has been tagged and no DOI exists.

Open gates before `v0.1.0` (see [`pnadtables-plano.md`](pnadtables-plano.md)):

| Gate | What it requires | Status |
|---|---|---|
| G0 | Git repository, correct metadata, no secrets | ✅ |
| G1 | Schema and value domains confirmed against the IBGE dictionary; one real small query | ⬜ |
| G2 | Deterministic encoding, missingness policy, weight validation, integration tests | ⬜ |
| G3 | Leakage-free splits, survey-design protocol, metrics with uncertainty | ⬜ |
| G4 | Reproducible real-data baseline with a results table | ⬜ |
| G5 | CI green on supported Python versions, clean install from artifact | ⬜ |
| G6 | Datasheet, limitations, provenance, verified licences/terms | ⬜ |
| G7 | Public repo, `v0.1.0` tag, archived release, DOI | ⬜ |
| G8 | PyPI publication, verified `pip install pnadtables` | ⬜ |

```python
from pnadtables import PNADCDataSource, PNADEmployment, audit_report

src = PNADCDataSource(billing_project_id="my-gcp-project", ano=2024, trimestre=1)
X, y, group, weight = PNADEmployment.df_to_pandas(src.get_data())
# 4-tuple: folktables returns (X, y, group); pnadtables adds the PNADC survey weight.
# Code written against folktables will NOT unpack this without modification.
```

## Why

Most empirical fairness research is calibrated on U.S. Census data (UCI Adult, then
folktables). Whether its conclusions transfer to the Global South is, as far as we know,
largely untested — but **this is a hypothesis we have not yet verified with a systematic
literature search** (ACM DL, IEEE Xplore, Scopus/OpenAlex, arXiv, Google Scholar). Do not
cite this README as evidence that no comparable benchmark exists. `pnadtables` adapts the
`BasicProblem` design to Brazil's official labour survey and targets two things:

- **Racial taxonomies are not translatable 1:1.** IBGE uses five self-declared categories
  (Branca, Preta, Amarela, Parda, Indígena), plus code 9 for "Ignorada" (non-response).
  Collapsing *Preta + Parda* into a binary Black/white axis is a theoretical choice, not a
  data fact. The package ships both encodings so results can be reported under each.
- **Complex survey design.** PNADC is a weighted, stratified, clustered sample. Every
  metric here accepts `weight`, which yields weighted **point estimates** — not
  survey-aware inference. Strata and PSU identifiers are not implemented yet, so this
  package cannot produce correct confidence intervals (gate G3).

### Not a drop-in folktables replacement

Name parity is not construct parity. ACS and PNADC differ in universe, periodicity,
variables and sample design, and the race/colour categories are not semantically
interchangeable. A Brazil–U.S. comparison needs an explicit harmonisation table
(construct, universe, income window, features, categories, geography, design, metric),
not just running tasks with similar names.

## Tasks

| Task | Conceptual reference | Universe | Target |
|---|---|---|---|
| `PNADEmployment` | ACSEmployment | age ≥ 14 | employed (`vd4002 == 1`) |
| `PNADIncome` | ACSIncome | employed, age ≥ 14, income > 0 | monthly income > threshold (parameter) |

Features: age, sex, race/colour, education level, state (UF). Protected attribute:
race/colour. Build new tasks with `BasicProblem(features, target, target_transform, group, ...)`.

## Install

```bash
pip install git+https://github.com/Brunooliveirab/pnadtables
pip install "pnadtables[examples]"   # adds scikit-learn + shap for example_audit.py
```

You need a Google Cloud project for BigQuery billing (`billing_project_id`). The microdata
are public, but **queries are billed to whoever runs them** — your project, not ours. There
is no server and no hosting: you install the package and query the public table yourself.

### Cost control

`get_data()` never runs a query blind. It first performs a BigQuery **dry run**, which is
free and reads no data, and refuses the query if it would scan more than `max_gb`. The same
ceiling is passed to BigQuery as `maximum_bytes_billed`, so the server aborts the query even
if the estimate was wrong.

```python
src = PNADCDataSource(billing_project_id="my-gcp-project", ano=2024,
                      trimestre=1, ufs=["MT", "SP"])

print(src.dry_run())     # free: what this query would cost, before running it
df = src.get_data()      # refuses above DEFAULT_MAX_GB (5 GB)
df = src.get_data(max_gb=20)   # raise the ceiling deliberately
df = src.get_data(max_gb=None) # disable both guards — know what you are doing
```

For scale: BigQuery on-demand charges **US$ 6.25 per TiB scanned**, with **1 TiB free per
month** per billing account. One quarter with the 11 columns in `DEFAULT_COLUMNS` is on the
order of tens of MB — a small fraction of the free tier. Verify with `dry_run()` rather than
trusting that estimate, and set a billing limit on the project anyway. See
[BigQuery pricing](https://cloud.google.com/bigquery/pricing) and
[cost controls](https://docs.cloud.google.com/bigquery/docs/best-practices-costs).

The query selects only the columns a task needs. Never replace it with `SELECT *`: BigQuery
is columnar and bills by columns read, so that alone would cost orders of magnitude more.

## Before you publish numbers

1. Run `inspect_schema(billing_project_id)` and confirm every column name in
   `pnadtables/columns.py` against your BigQuery environment **and** the official IBGE
   dictionary for each year you use. All names live in that single file.
2. Set the income threshold in `make_pnad_income(threshold=...)` to the reference year of
   your data.
3. Report results under **both** `raca_5grupos` and `raca_branca_negra`, and quantify how
   many rows each collapse excludes.
4. Report **both** weighted and unweighted metrics as a sensitivity analysis. Neither is
   universally the correct headline number — say which question each one answers.
5. Do not use a naive random split: people in the same household are correlated and PNADC
   rotates households. Prefer household-grouped, temporal or geographic splits (gate G3,
   not yet implemented here).

See [DATASHEET.md](DATASHEET.md) (Gebru et al. structure) for the full methodological record.

## Metrics

`selection_rates`, `disparate_impact`, `rate_by_group` (TPR/FPR), `audit_report` — all with
optional survey weights. By default `disparate_impact` uses the highest-rate group as
reference, so ratios fall in (0, 1] and the 0.8 threshold is the relevant one; the
symmetric 1.25 threshold only applies when you pass a fixed `reference` yourself. The 4/5
rule is a contextual screening heuristic, **not** an automatic legal diagnosis of
discrimination.

`example_audit.py` runs the full loop: data → model → weighted audit → SHAP attributions.
SHAP is illustrative only; a standalone feature-importance ranking does not support claims
about a "right to explanation".

## Intended use

Research and auditing of algorithmic systems. **Not** for decisions about individuals, and
not a substitute for substantive research on inequality. Do not attempt to re-identify
respondents.

## Development

```bash
pip install -e ".[dev]"
pytest
```
Tests run offline with synthetic PNADC-shaped data; no BigQuery access needed. Passing them
is **not** evidence that the schema matches real PNADC data (gate G1).

## Citation

See [CITATION.cff](CITATION.cff). Note that no version has been released yet. Please also
cite folktables:

> Ding, F., Hardt, M., Miller, J., & Schmidt, L. (2021). *Retiring Adult: New Datasets for
> Fair Machine Learning.* NeurIPS 34.

## License

MIT for this package's code. Microdata © IBGE, distributed through Base dos Dados under
their respective terms; this package redistributes no data. Attribution and access terms
for IBGE and Base dos Dados must be verified before publication (gate G6).
