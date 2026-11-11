# Dados sintéticos: DRE gerencial de obras

[English](README.md)

> **Todos os dados são fictícios.** Empresas, pessoas, CNPJs (formatados, com dígitos verificadores propositalmente inválidos), valores e datas são gerados. Nada vem do cliente original.

## O que é

O modelo original do Power BI lia planilhas por caminhos locais fixos (`C:\Users\…\Downloads`, `G:\Meu Drive\…`). Esses arquivos não podem ser publicados, então este gerador os recria.

O `generate.py` (com semente, determinístico) monta um ERP de construtora fictício em memória e grava duas saídas:

| Saída | Para quê |
|---|---|
| `output/erp_seed/*.csv` → `output/erp_source.duckdb` (schema `erp`) | **Sistema de origem** limpo e normalizado para o novo pipeline (dbt, cargas incrementais). |
| `output/excel/*.xlsx`, `*.xls` e `output/erp_export/*.csv` | **Os arquivos "bagunçados" que o modelo original lê**. Têm os mesmos nomes de arquivo e de aba, linhas de cabeçalho, nomes de coluna e problemas conhecidos, então o PBIP original atualiza depois de ajustar os caminhos. |

As duas saídas vêm dos mesmos registros, então os totais do Excel batem com o banco do ERP (ver testes).

## Como executar

```bash
pip install -r requirements.txt        # Python 3.10+
python generate.py                     # --seed 42 --out output
python -m unittest discover -s tests -v

python erp_db/load_erp.py              # cria output/erp_source.duckdb (sem servidor, sem senha)
```

## Granularidade

`erp.lancamento`: **uma parcela de documento financeiro** por obra, conta e contraparte. A coluna `updated_at` é a marca d'água para extração incremental.

## Catálogo de problemas de dados

São 18 problemas, cada um marcado como *observado* (há um passo no M/DAX original que comprova) ou *sintético* (caso de teste). A tabela completa está no [README em inglês](README.md#data-issue-catalog). Exemplos: linhas de título acima do cabeçalho, quebras de linha nos cabeçalhos, código de conta com pontos vs inteiro, lançamentos realizados sem data bancária descartados em silêncio, lista fixa de contas de receita, `FillDown` que espalha nomes de sócios entre obras, CSV sem aspas com vírgulas no histórico e linhas duplicadas.

## Limitações

- As distribuições são plausíveis, mas inventadas.
- `Data da Base` vem do sistema de arquivos e muda a cada cópia.
- O PBIP original ainda precisa de caminhos novos e de alguns literais renomeados. A lista de ajustes fica privada no projeto, fora deste repositório.
