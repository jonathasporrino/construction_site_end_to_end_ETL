"""Builds the fictitious ERP as a DuckDB file from the generated seed CSVs.

Usage: python erp_db/load_erp.py [--seed-dir output/erp_seed] [--db output/erp_source.duckdb]
The file is recreated from scratch on every run (the CSVs are the source of truth).
"""
import argparse
from pathlib import Path

import duckdb

HERE = Path(__file__).resolve().parent
TABLES = ["empresa", "plano_contas", "operacao", "obra", "obra_socio", "lancamento"]  # foreign-key order


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed-dir", default=str(HERE.parent / "output" / "erp_seed"))
    ap.add_argument("--db", default=str(HERE.parent / "output" / "erp_source.duckdb"))
    a = ap.parse_args()
    db = Path(a.db)
    db.unlink(missing_ok=True)
    con = duckdb.connect(str(db))
    con.execute((HERE / "schema.sql").read_text(encoding="utf-8"))
    for t in TABLES:
        con.execute(f"COPY erp.{t} FROM '{(Path(a.seed_dir) / f'{t}.csv').as_posix()}' (HEADER)")
        print(f"erp.{t}: {con.execute(f'select count(*) from erp.{t}').fetchone()[0]} rows")
    con.close()


if __name__ == "__main__":
    main()
