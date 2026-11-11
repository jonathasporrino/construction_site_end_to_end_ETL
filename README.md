# Synthetic data: construction management P&L

[Português](README.pt-BR.md)

> **All data here is fictitious.** Company names, people, CNPJs (formatted, with deliberately invalid check digits), values and dates are generated. Nothing comes from the original client.

## What this is

The original Power BI model read spreadsheets from fixed local paths (`C:\Users\…\Downloads`, `G:\Meu Drive\…`). Those files can't be published, so this generator rebuilds them.

`generate.py` (seeded and deterministic) builds one fictitious construction ERP in memory and writes it out twice:

| Output | Purpose |
|---|---|
| `output/erp_seed/*.csv` → `output/erp_source.duckdb` (schema `erp`) | A clean, normalized **source system** for the new pipeline (dbt, incremental loads). |
| `output/excel/*.xlsx`, `*.xls` and `output/erp_export/*.csv` | The **messy files the original Power BI model reads**. They use the same file names, sheet names, header rows, column names and known data issues, so the original PBIP refreshes after its paths are updated. |

Both outputs come from the same records, so the Excel totals reconcile with the ERP database (see the tests).

| Dataset (seed 42) | Rows |
|---|---|
| Works + administrative cost centers | 36 + 4 |
| Partner shares | 101 |
| Companies (partners, suppliers, clients) | 44 |
| Financial entries (ERP) | 22,739 |
| Excel `BD EFETUADO` / `BD COMPROMISSADO` | 16,026 / 5,666 |
| ERP CSV extract (Oct 2025 – Jan 2026) | 2,230 |

## Run

```bash
pip install -r requirements.txt        # Python 3.10+
python generate.py                     # --seed 42 --out output
python -m unittest discover -s tests -v

python erp_db/load_erp.py              # builds output/erp_source.duckdb (no server, no password)
```

Re-running the generator with the same seed produces byte-identical seed files (this is tested).

## Source → Power BI mapping

| File / sheet | Read by (M query) | Layout reproduced |
|---|---|---|
| `Banco de Dados Gerencial - Set_2025.xlsx` / `BD EFETUADO` | `BD EFETUADO`, `BD EFETUADO (2)` → `fct_gerencial`, `dim_socio` | Blank column A; 13 rows above the header; 73 columns, with blank Column20 and Column57–73; extra calculation columns removed by M |
| same / `BD COMPROMISSADO` | `BD COMPROMISSADO`, `BD COMPROMISSADO (2)` | Blank column A; 8 rows above the header; `FORNECEDOR` / `DESCRIÇÃO DA EMPRESA` renamed by M; total row at the bottom |
| `Classificação das Obras.xlsx` / `Classif. Obras` | `CLASSIFICAÇÃO DAS OBRAS` | 2 title rows, a header row, 1 sub-header row; 91 columns (24 partner slots × description / % share / % TAC) |
| `Classificação das Obras 2.0.xlsx` / `Aurora` | `Gerencia` | Header in row 1; partner slot 1 only |
| `Lista Plano de Contas .xls` / `Planilha1` | `Lista de Plano de Contas` | Legacy `.xls`; integer account codes; 3 stray blank columns |
| `erp_export/_SELECT_RZ_…_dados.csv` | `_SELECT_RZ_…` | 79 `RZANALCONSOL_*` columns, comma-delimited, unquoted |

Rules from the original requirements that the data follows: works have 4-digit numbers; `valor_compromissado` (TOTCOMP) holds only the amount still to receive or pay, so Total = Comp. + Efetuado as in the ERP report 3.29; deferred revenue and termination accruals stay committed; operations 510 (revenue received), 733 (tax transfer) and 823 (revenue transfer) exist; cost classes are MATERIAL, MÃO DE OBRA, EQUIPAMENTO, SERVIÇO TERCEIRIZADO, TAXAS E IMPOSTOS and GASTOS GERAIS.

Grain of the ERP entries table (`erp.lancamento`): **one financial document installment** for one work, one account and one counterpart. Its `updated_at` column is the watermark for incremental extraction.

## Data-issue catalog

"Observed" means the issue is evidenced by a step in the original M/DAX code. "Synthetic" means it was added as a test case.

| # | Issue | Where | Origin |
|---|---|---|---|
| 1 | Title rows above the header; blank first column | BD sheets, Classif. | Observed (`Table.Skip`, `RemoveColumns Column1`) |
| 2 | Unnamed columns (Column20, Column57–73, Column91) | BD EFETUADO, Classif. | Observed |
| 3 | Line breaks inside headers (`DT.\nMOVBANC`, `% …\n…`) | BD sheets, Classif. | Observed (`#(lf)` in M) |
| 4 | Account codes as dotted text (`2.003.01.0001`) vs integers in the lookup | BD vs Lista | Observed (`ReplaceValue "."`) |
| 5 | Total row and blank rows without a cost center | BD COMPROMISSADO | Observed (filter `CENTRO DE CUSTO <> null`) |
| 6 | Realized entries without a bank date (null or `""`) are silently dropped | BD EFETUADO | Observed filter; affected rows synthetic (~0.4%) |
| 7 | Cost center replaced by `INATIVO` for closed works | BD sheets | Observed (filter in `dim_socio`) |
| 8 | Accounts outside the 1/2 prefixes (3xxx, 4xxx) kept only in `dim_socio` | BD sheets | Observed |
| 9 | Revenue/expense decided by a hard-coded list of 21 account codes | M step | Observed |
| 10 | Misspelled manager name, fixed by a hard-coded replace | Classif. | Observed |
| 11 | Header typos: `Particiapação`, trailing space `TIPO `, double space `Sócio 1  - % TAC` | Classif., 2.0 | Observed |
| 12 | Blank partner descriptions filled with `FillDown`/`FillUp`, which can bleed names across works | Classif. | Observed step; blanks synthetic (~5%) |
| 13 | Hard-coded exclusion of numbers 1 and 100–179 (except 139, 155, 175); here 1/101/120/150 are administrative cost centers (hypothesis) | Classif. | Observed |
| 14 | Two classification files out of sync (missing works, drifting contract values) | Classif. vs 2.0 | Inferred from the two sources; values synthetic |
| 15 | Legacy `.xls`; trailing space in the file name; some accounts have no rule and drop out of the lookup | Lista | Observed |
| 16 | CSV with no quoting: commas inside `HISTORICO` shift columns | ERP CSV | Inferred from `QuoteStyle.None`; ~1% of expense rows |
| 17 | Exact duplicate rows (copy/paste) | BD EFETUADO | Synthetic (~0.5%) |
| 18 | Snapshot date taken from the file's "Date created" metadata | M step | Observed (it depends on the machine; not reproducible) |

## Limits

- Distributions such as monthly billing, expense mix, tax rates and partner shares are plausible, but they're invented. They don't reflect the original business.
- `Data da Base` comes from the file system, so it changes with each copy of the file.
- The original model still needs updated file paths and a few renamed literals before it refreshes against these files. The edit list is kept privately with the project, not in this repo.
