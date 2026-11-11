"""Self-checks for the generator: layout compatibility with the Power BI M code + reconciliation.
Run: python -m unittest discover -s tests -v   (from the synthetic_data folder)
"""
import csv
import datetime as dt
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import generate as g  # noqa: E402

OUT = Path(tempfile.mkdtemp())
subprocess.run([sys.executable, str(ROOT / "generate.py"), "--out", str(OUT)], check=True, capture_output=True)
BD = openpyxl.load_workbook(OUT / "excel" / "Banco de Dados Gerencial - Set_2025.xlsx", read_only=True)


def sheet(name, skip):
    """Mimic Excel.Workbook -> RemoveColumns(Column1) -> Skip(n) -> PromoteHeaders."""
    rows = list(BD[name].iter_rows(values_only=True))[skip:]
    header = [h if h is not None else f"Column{i + 1}" for i, h in enumerate(rows[0])]
    return header, [dict(zip(header, r)) for r in rows[1:]]


def seed(name):
    with open(OUT / "erp_seed" / f"{name}.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class Layout(unittest.TestCase):
    def test_efetuado_columns_match_m_code(self):
        header, _ = sheet("BD EFETUADO", 13)
        self.assertEqual(len(header), 73)
        removed = {"Column1", "Column20"} | {f"Column{i}" for i in range(57, 74)}
        self.assertTrue(removed <= set(header), "columns removed by the M step must exist")
        self.assertEqual([h for h in header if h not in removed], g._efet_named)

    def test_compromissado_columns(self):
        header, rows = sheet("BD COMPROMISSADO", 8)
        self.assertEqual(header[0], "Column1")
        self.assertEqual(header[1:], g.COMP_COLS[1:])
        self.assertTrue(any(r["CENTRO DE CUSTO"] is None for r in rows), "total/blank rows filtered by M")

    def test_classificacao_layout(self):
        ws = openpyxl.load_workbook(OUT / "excel" / "Classificação das Obras.xlsx", read_only=True)["Classif. Obras"]
        rows = list(ws.iter_rows(values_only=True))
        self.assertEqual(len(rows[2]), 91)
        self.assertIsNone(rows[2][0])
        self.assertIsNone(rows[2][90])
        self.assertIn("Sócio 24 - % Particiapação Societária", rows[2])
        numeros = {r[3] for r in rows[4:] if r[3] is not None}
        self.assertTrue(numeros & g.EXCLUDED_NUMERO, "hard-coded exclusion list must hit some works")
        self.assertTrue({139, 155, 175} <= numeros)

    def test_erp_csv_has_79_columns_and_unquoted_commas(self):
        lines = (OUT / "erp_export").glob("*.csv").__next__().read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines[0].split(",")), 79)
        widths = [len(l.split(",")) for l in lines[1:]]
        self.assertGreater(widths.count(79) / len(widths), 0.95)
        self.assertTrue(any(w > 79 for w in widths), "known issue: commas inside HISTORICO shift columns")


class Data(unittest.TestCase):
    def test_deterministic(self):
        other = Path(tempfile.mkdtemp())
        subprocess.run([sys.executable, str(ROOT / "generate.py"), "--out", str(other)], check=True, capture_output=True)
        for f in (OUT / "erp_seed").glob("*.csv"):
            self.assertEqual(hashlib.md5(f.read_bytes()).hexdigest(),
                             hashlib.md5((other / "erp_seed" / f.name).read_bytes()).hexdigest(), f.name)

    def test_efetuado_reconciles_with_source(self):
        """Excel realized total = ERP realized total + injected duplicates; rows without bank date are the gap."""
        _, rows = sheet("BD EFETUADO", 13)
        mov = "DT.\nMOVBANC"
        kept = [r for r in rows if r[mov] not in (None, "")]
        dropped = [r for r in rows if r[mov] in (None, "")]
        dup = len(kept) + len(dropped) - len({r["NUMDOC"] for r in rows})
        self.assertGreater(dup, 0)
        self.assertGreater(len(dropped), 0)
        cut = g.EXCEL_CUT.isoformat()
        src = [e for e in seed("lancamento") if e["status"] == "REALIZADO" and e["dt_movbanc"] <= cut]
        unique = {r["NUMDOC"]: r["VALOR TOTAL EFETUADO"] for r in rows}
        self.assertAlmostEqual(sum(unique.values()), sum(float(e["valor_efetuado"]) for e in src), places=2)
        self.assertEqual(len(unique), len(src))

    def test_documented_rules(self):
        """Rules doc + ERP report 3.29: TOTCOMP holds only open amounts; ops 733/823 exist; works have 4 digits."""
        rows = seed("lancamento")
        self.assertTrue(all(float(e["valor_compromissado"]) == 0 for e in rows if e["status"] == "REALIZADO"))
        self.assertTrue(all(float(e["valor_efetuado"]) == 0 for e in rows if e["status"] == "A REALIZAR"))
        self.assertTrue({"733", "823", "510"} <= {e["op_codigo"] for e in rows})
        works = [int(o["numero"]) for o in seed("obra") if o["tipo"] != "ADMINISTRATIVO"]
        self.assertGreater(sum(n >= 9000 for n in works) / len(works), .9)

    def test_partner_shares_sum_to_one(self):
        total = {}
        for s in seed("obra_socio"):
            total[s["numero_obra"]] = total.get(s["numero_obra"], 0) + float(s["pct_participacao"])
        self.assertTrue(all(abs(v - 1) < 1e-6 for v in total.values()))

    def test_cnpj_check_digit_is_invalid(self):
        def valid(c):
            d = [int(x) for x in c if x.isdigit()]
            for n, w in ((12, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]), (13, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])):
                r = sum(a * b for a, b in zip(d[:n], w)) % 11
                if d[n] != (0 if r < 2 else 11 - r):
                    return False
            return True
        self.assertFalse(any(valid(e["cnpj"]) for e in seed("empresa")))

    def test_aporte_partner_names_match_classification(self):
        """DAX uses TREATAS(Classificação[DESCRIÇÃO] -> EMPRESA RECBTO/PAGTO): names must be shared."""
        partners = {e["razao_social"] for e in seed("empresa") if e["tipo"] == "SOCIO"}
        aportes = {e["empresa_recbto_pagto"] for e in seed("lancamento") if int(e["op_codigo"]) in g.APORTE_OPS}
        self.assertTrue(aportes and aportes <= partners)


if __name__ == "__main__":
    unittest.main()
