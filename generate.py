"""Fictitious data generator for the construction management P&L project.

One random, seeded "ERP" is built in memory and written two ways:
  1. output/erp_seed/*.csv  -> clean, normalized source system (loaded into DuckDB by erp_db/load_erp.py)
  2. output/excel + output/erp_export -> the messy files the original Power BI model reads,
     with the same sheets, header positions, column names and known data issues.

All names, CNPJs, values and dates are invented. See README.md for the issue catalog.
Usage: python generate.py [--seed 42] [--out output]
"""
import argparse
import csv
import datetime as dt
import random
from pathlib import Path

import openpyxl
import xlwt

# --------------------------------------------------------------------------- reference data
GROUP = ("1", "GRUPO AURORA")
OWN_COMPANY = "AURORA ENGENHARIA LTDA"
PARTNERS = [OWN_COMPANY, "ORION EMPREENDIMENTOS E CONSTRUCOES LTDA", "VERTICE INFRAESTRUTURA LTDA",
            "NOVA ROTA ENGENHARIA LTDA", "PILAR CONSTRUCOES SA", "HORIZONTE OBRAS LTDA",
            "TERRA FIRME PAVIMENTACAO LTDA", "ATLAS SANEAMENTO LTDA", "MERIDIANO PROJETOS LTDA",
            "CANTEIRO FORTE LTDA", "SOLIDA ESTRUTURAS LTDA", "RIO CLARO ENGENHARIA LTDA"]
MANAGERS = ["ROBERTO", "MARINA", "CLAUDIO", "PATRICIA", "FERNANDO"]
TYPO_MANAGER = ("ROBERTOO", "ROBERTO")  # the original M code fixes one misspelled manager name
CITIES = ["VILA SERENA", "PORTO ALVORADA", "SANTA LUZIA DO NORTE", "CAMPO VERDE", "SERRA AZUL",
          "NOVA ESPERANCA", "BOA VISTA DO SUL", "LAGOA DOURADA", "MONTE ALEGRE", "RIO BONITO"]
UFS = ["SE", "BA", "AL", "PE", "SP", "MG"]
WORK_KIND = ["PAVIMENTACAO", "DRENAGEM", "ESCOLA MUNICIPAL", "UNIDADE DE SAUDE", "ORLA", "PONTE",
             "SANEAMENTO", "CONJUNTO HABITACIONAL", "CONTENCAO DE ENCOSTA", "PRACA"]
SUPPLIERS = ["CIMENTEIRA DO VALE LTDA", "ACO FORTE DISTRIBUIDORA LTDA", "LOCAMAQ EQUIPAMENTOS LTDA",
             "AREIA E BRITA SOL LTDA", "POSTO TREVO COMBUSTIVEIS LTDA", "TRANSPORTADORA ESTRADA REAL LTDA",
             "HIDRO TUBOS LTDA", "ASFALTO NORDESTE LTDA", "SEGURA EPI LTDA", "TOPOGRAFIA PRECISA LTDA",
             "ALIMENTA OBRAS LTDA", "ENGEPROJ CONSULTORIA LTDA", "MADEIREIRA BOM PINHO LTDA",
             "ELETRO CAMPOS LTDA", "LOCADORA PESADA LTDA", "LABORATORIO SOLO TESTE LTDA"]

# Chart of accounts: (code, description, rule for 'Lista Plano de Contas' or None).
# Expense codes mirror the DAX DATATABLE in dPlanoContas; 3xxx/4xxx accounts are fictitious extras.
ACCOUNTS = [
    ("1001020001", "RECEITAS DE FATURAS DE SERVIÇOS /MATERIAIS", None),
    ("1001020002", "RECEITAS DE MEDIÇÕES A FATURAR", None),
    ("1001020003", "RECEITAS DIFERIDAS DE SERVIÇOS MEDIDOS/REALIZADOS", None),
    ("1001030005", "RECUPERAÇÃO DE DESPESAS DE FINANCEIRAS", None),
    ("1001040001", "RENDIMENTOS DE APLICAÇÕES FINANCEIRAS", None),
    ("2003010001", "MATERIAIS HIDRO-MECÂNICOS", "MATERIAL"),
    ("2003010002", "MATERIAIS DE CONSTRUÇÃO", "MATERIAL"),
    ("2003010004", "MATERIAIS DE TERRAPLENAGEM E PAVIMENTAÇÃO", "MATERIAL"),
    ("2003020001", "PRESTAÇÃO DE SERVIÇOS", "SERVIÇO TERCEIRIZADO"),
    ("2003020002", "SERVIÇOS TÉCNICOS", "SERVIÇO TERCEIRIZADO"),
    ("2003020003", "FRETES CARRETOS, TRANSPORTE DE OBRAS", "SERVIÇO TERCEIRIZADO"),
    ("2003030001", "LOCAÇÃO DE EQUIPAMENTOS GRANDE PORTE", "EQUIPAMENTO"),
    ("2003030002", "LOCAÇÃO DE EQUIPAMENTOS PEQUENO PORTE", "EQUIPAMENTO"),
    ("2003040001", "COMBUSTÍVEIS", "EQUIPAMENTO"),
    ("2003040002", "MATERIAIS DE MANUTENÇÃO", "EQUIPAMENTO"),
    ("2003050001", "SALÁRIOS E ORDENADOS (OBRAS)", "MÃO DE OBRA"),
    ("2003050002", "ADIANTAMENTO DE SALÁRIOS (OBRAS)", "MÃO DE OBRA"),
    ("2003060003", "INSS (OBRAS)", "MÃO DE OBRA"),
    ("2003060006", "FGTS (OBRAS)", "MÃO DE OBRA"),
    ("2003060011", "PREVISÃO DE RESCISÃO (OBRAS)", "MÃO DE OBRA"),  # accrual: committed, never paid
    ("2003070002", "ALIMENTAÇÃO (OBRAS)", "MÃO DE OBRA"),
    ("2003070008", "UNIFORMES / EPI'S / EPC'S (OBRAS)", "MÃO DE OBRA"),
    ("2003080001", "CANTEIRO / ALOJAMENTO", "GASTOS GERAIS"),
    ("2003080006", "SEGUROS / GARANTIAS", None),  # issue: rule missing -> filtered out of the lookup
    ("2006010001", "PIS", "TAXAS E IMPOSTOS"),
    ("2006010003", "COFINS", "TAXAS E IMPOSTOS"),
    ("2006010006", "(-) ISS RETIDO SOBRE FATURAMENTO", "TAXAS E IMPOSTOS"),
    ("2006020001", "IRPJ + ADICIONAL IRPJ", "TAXAS E IMPOSTOS"),
    ("2006020002", "(-) IR RETIDO SOBRE FATURAMENTO", "TAXAS E IMPOSTOS"),
    ("2006020003", "CSLL", "TAXAS E IMPOSTOS"),
    ("2006030007", "TAC INTERNA", "TAXAS E IMPOSTOS"),
    ("2006030009", "TAC DAS OBRAS COLIGADAS", "TAXAS E IMPOSTOS"),
    ("2007010001", "TARIFAS BANCÁRIAS", "GASTOS GERAIS"),
    ("2009040003", "MÁQUINAS E EQUIPAMENTOS", "EQUIPAMENTO"),
    ("3001010001", "APORTES DE SÓCIOS", None),
    ("3001010002", "DEVOLUÇÃO DE APORTES", None),
    ("3002010001", "RECEITA RECEBIDA POR SÓCIO", None),
    ("3002010002", "TRANSFERÊNCIA DE IMPOSTOS ENTRE SÓCIOS", None),
    ("3002010003", "TRANSFERÊNCIA DE RECEITA ENTRE SÓCIOS", None),
    ("4002010002", "INSS RETIDO SOBRE FATURAMENTO", None),
]
# Revenue codes hard-coded in the original M step "Ajuste de coluna"
REVENUE_CODES = {"1001020001", "1001020002", "1001020003", "1001030004", "1001030005", "1001020004",
                 "1001020005", "1001020006", "1001030001", "1001030002", "1001030003", "1001030007",
                 "1001030008", "1001040001", "1001040002", "1001040003", "1004010001", "1002010004",
                 "1004010002", "1002010001", "1001040004"}
EXPENSE_MIX = [a[0] for a in ACCOUNTS if a[0].startswith("2003") and a[0] != "2003060011"] + ["2007010001", "2009040003"]
OPS = {510: "RECEBIMENTO DE RECEITA POR SÓCIO", 511: "RECEBIMENTO DE FATURA", 520: "PAGAMENTO A FORNECEDOR", 723: "APORTE DE SÓCIO - TED",
       735: "APORTE DE SÓCIO - DOC", 736: "APORTE DE SÓCIO - TRANSF", 748: "APORTE DE SÓCIO - CONTA CORRENTE",
       823: "TRANSFERÊNCIA DE RECEITA", 733: "TRANSFERÊNCIA DE IMPOSTOS", 610: "RECOLHIMENTO DE IMPOSTO", 615: "RETENÇÃO DE INSS"}
APORTE_OPS = [723, 735, 736, 748]
INSS_APCONTAS = ["000/0000/817", "000/0000/9026", "000/0000/9035", "000/0000/9051"]  # used by 'INSS Consumido'
# NÚMERO values the original M filter removes from 'CLASSIFICAÇÃO DAS OBRAS' (1, 100-179 except 139/155/175)
EXCLUDED_NUMERO = {1} | {n for n in range(100, 180) if n not in (139, 155, 175)}
ADMIN_CENTERS = [1, 101, 120, 150]

DATA_START = dt.date(2023, 1, 1)
EXCEL_CUT = dt.date(2025, 9, 30)      # "Banco de Dados Gerencial - Set_2025.xlsx"
ERP_EXTRACT = dt.date(2026, 1, 13)    # CSV extract timestamp 202601131620
CSV_FROM = dt.date(2025, 10, 1)


def fake_cnpj(rng):
    """Formatted like a CNPJ but with deliberately wrong check digits, so it can't match a real company."""
    base = [rng.randint(0, 9) for _ in range(8)] + [0, 0, 0, 1]
    d1 = (sum(w * n for w, n in zip([5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2], base)) % 11)
    d1 = (0 if d1 < 2 else 11 - d1 + 1) % 10  # +1 breaks the real check digit on purpose
    s = "".join(map(str, base)) + f"{d1}{rng.randint(0, 9)}"
    return f"{s[:2]}.{s[2:5]}.{s[5:8]}/{s[8:12]}-{s[12:]}"


def dotted(code):
    return f"{code[0]}.{code[1:4]}.{code[4:6]}.{code[6:]}"


def month_iter(start, end):
    y, m = start.year, start.month
    while dt.date(y, m, 1) <= end:
        yield dt.date(y, m, 1)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def add_days(d, n):
    return d + dt.timedelta(days=n)


# --------------------------------------------------------------------------- build the ERP
def build(rng):
    companies = [{"empresa_id": i + 1, "razao_social": n, "cnpj": fake_cnpj(rng), "tipo": "SOCIO"}
                 for i, n in enumerate(PARTNERS)]
    companies += [{"empresa_id": len(PARTNERS) + i + 1, "razao_social": n, "cnpj": fake_cnpj(rng), "tipo": "FORNECEDOR"}
                  for i, n in enumerate(SUPPLIERS)]
    by_name = {c["razao_social"]: c for c in companies}

    # Works use 4-digit numbers (e.g. 9032); 1/101/120/150 are administrative cost centers, which is our
    # hypothesis for why the original M filter drops NÚMERO 1 and 100-179. 139/155/175 are legacy works.
    numeros = sorted(rng.sample(range(9001, 9100), 33) + [139, 155, 175] + ADMIN_CENTERS)
    obras, socios = [], []
    for n in numeros:
        kind = "ADMINISTRATIVO" if n in ADMIN_CENTERS else rng.choice(["SCP", "SCP", "CONSÓRCIO", "PRÓPRIA"])
        city = rng.choice(CITIES)
        start = dt.date(2023, rng.randint(1, 12), 1) if rng.random() < .6 else dt.date(2024, rng.randint(1, 12), 1)
        months = rng.randint(14, 40)
        end = min(add_days(start, months * 30), dt.date(2026, 6, 30))
        inactive = end < dt.date(2025, 3, 1) and rng.random() < .5
        client_public = rng.random() < .8
        obras.append({
            "numero": n, "descricao": (f"CENTRO ADMINISTRATIVO {n:04d}" if kind == "ADMINISTRATIVO"
                                       else f"OBRA {n:04d} - {rng.choice(WORK_KIND)} {city}"),
            "tipo_cliente": "PÚBLICO" if client_public else "PRIVADO",
            "grupo": "OBRAS ENCERRADAS" if inactive else "OBRAS EM ANDAMENTO",
            "unidade_negocio": rng.choice(["INFRAESTRUTURA", "EDIFICAÇÕES", "SANEAMENTO"]),
            "controle": rng.choice(["SIM", "NÃO", None]), "gerente": rng.choice(MANAGERS),
            "uf": rng.choice(UFS),
            "cliente": f"PREFEITURA MUNICIPAL DE {city}" if client_public else f"INCORPORADORA {city} LTDA",
            "tipo": kind, "pct_empresa_parceira": round(rng.uniform(.3, 1), 2) if kind in ("SCP", "CONSÓRCIO") else 1.0,
            "valor_contrato": round(rng.uniform(2e6, 6e7), 2), "pct_fisico": round(rng.uniform(.05, 1), 4),
            "credito_inss": rng.choice(["SIM", "NÃO", None]) if kind == "SCP" else None,
            "contas_inss": rng.sample(INSS_APCONTAS, rng.randint(1, 3)) if kind == "SCP" else [],
            "dt_inicio": start, "dt_fim": end, "ativo": not inactive,
        })
        partners = [OWN_COMPANY] if kind in ("PRÓPRIA", "ADMINISTRATIVO") else [OWN_COMPANY] + rng.sample(PARTNERS[1:], rng.randint(1, 4))
        cuts = sorted(rng.sample(range(5, 95, 5), len(partners) - 1))
        shares = [(b - a) / 100 for a, b in zip([0] + cuts, cuts + [100])]
        for seq, (p, s) in enumerate(zip(partners, shares), 1):
            socios.append({"numero_obra": n, "socio_seq": seq, "empresa_id": by_name[p]["empresa_id"],
                           "pct_participacao": round(s, 4), "pct_tac": round(rng.choice([0, .02, .03, .04, .05]), 4)})

    for cli in sorted({o["cliente"] for o in obras}):
        companies.append({"empresa_id": len(companies) + 1, "razao_social": cli, "cnpj": fake_cnpj(rng), "tipo": "CLIENTE"})
        by_name[cli] = companies[-1]

    entries, seq = [], 0

    def entry(obra, account, counterpart, value, due, op, kind, empresa_rp, hist, force_open=False):
        nonlocal seq
        seq += 1
        renegotiated = rng.random() < .1
        venc = add_days(due, rng.choice([15, 30, 45])) if renegotiated else due
        doc = add_days(due, -rng.randint(5, 40))
        paid = add_days(venc, rng.randint(-3, 10))
        realized = paid <= ERP_EXTRACT and rng.random() > .03 and not force_open
        ap = "AR" if account in REVENUE_CODES or op in (510, 511, 823) or op in APORTE_OPS else "AP"
        tx = round(value * .01, 2) if obra["tipo"] != "PRÓPRIA" else 0
        entries.append({
            "lancamento_id": seq, "numero_obra": obra["numero"], "plano_conta": account,
            "contraparte_id": by_name[counterpart]["empresa_id"], "empresa": OWN_COMPANY,
            "empresa_recbto_pagto": empresa_rp, "numdoc": f"{rng.choice(['NF', 'FAT', 'REC', 'GUIA'])} {seq:06d}",
            "dt_doc": doc, "dt_venc": venc, "dt_vencorig": due,
            "dt_recto": paid if realized and ap == "AR" else None, "dt_movbanc": paid if realized else None,
            "historico": hist, "op_codigo": op, "ri": f"RI{rng.randint(1000, 9999)}" if ap == "AR" else None,
            "valor_previsto": value, "valor_compromissado": 0.0 if realized else value,
            "valor_efetuado": value if realized else 0.0,
            "tx_adm_prev": tx, "tx_adm_comp": 0.0 if realized else tx, "tx_adm_efetu": tx if realized else 0.0,
            "aprec": ap, "apstatus": ("PAGO" if realized else "ABERTO") if ap == "AP" else None,
            "apcontacdg": f"{rng.randint(1, 9)}" if ap == "AP" else None,
            "apconta": (rng.choice(obra["contas_inss"]) if kind == "inss_consumido"
                        else f"000/0000/{rng.randint(100, 999)}") if ap == "AP" else None,
            "arcontacdg": f"{rng.randint(1, 9)}" if ap == "AR" else None,
            "arconta": f"001/{rng.randint(1000, 9999)}" if ap == "AR" else None,
            "ripedidos": f"PED{rng.randint(10000, 99999)}" if ap == "AP" and rng.random() < .4 else None,
            "arrec": ("RECEBIDO" if realized else "A RECEBER") if ap == "AR" else None,
            "arstatus": ("QUITADO" if realized else "ABERTO") if ap == "AR" else None,
            "status": "REALIZADO" if realized else "A REALIZAR",
            "created_at": dt.datetime.combine(doc, dt.time(9, 0)),
            "updated_at": dt.datetime.combine(paid if realized else doc, dt.time(18, 0)),
        })

    obra_partners = {}
    for s in socios:
        obra_partners.setdefault(s["numero_obra"], []).append(s)
    name_by_id = {c["empresa_id"]: c["razao_social"] for c in companies}

    for o in obras:
        months = list(month_iter(o["dt_inicio"], o["dt_fim"]))
        monthly_rev = o["valor_contrato"] / max(len(months), 1)
        partners = obra_partners[o["numero"]]
        if o["tipo"] == "ADMINISTRATIVO":
            for m in months:
                for acc in ("2003080001", "2007010001"):
                    entry(o, acc, rng.choice(SUPPLIERS), round(rng.uniform(5e3, 6e4), 2), add_days(m, 15), 520,
                          "adm", OWN_COMPANY, f"DESPESA ADMINISTRATIVA {m:%m/%Y}")
            continue
        for m in months:
            due = add_days(m, 24)
            rev = round(monthly_rev * rng.uniform(.6, 1.3), 2)
            entry(o, "1001020001", o["cliente"], rev, due, 511, "rev",
                  OWN_COMPANY, f"MEDIÇÃO {m:%m/%Y} - {o['descricao']}")
            for p in partners:  # receipts split by partner (OP 510) -> 'Receitas Recebidas'
                entry(o, "3002010001", OWN_COMPANY, round(rev * p["pct_participacao"], 2), add_days(due, 3), 510,
                      "split", name_by_id[p["empresa_id"]], f"RECEITA SÓCIO {m:%m/%Y}")
            if rng.random() < .3:
                entry(o, "1001020003", OWN_COMPANY, round(rev * .2, 2), add_days(due, 30), 520, "rev",
                      OWN_COMPANY, "RECEITA DIFERIDA - SERVIÇOS MEDIDOS", force_open=True)  # report 3.29: Comp. only
            for _ in range(rng.randint(8, 16)):
                acc = rng.choice(EXPENSE_MIX)
                entry(o, acc, rng.choice(SUPPLIERS), round(rev * rng.uniform(.01, .08), 2),
                      add_days(m, rng.randint(1, 27)), 520, "exp", OWN_COMPANY,
                      f"PAGAMENTO NF, PARCELA 1/2 {m:%m/%Y}" if rng.random() < .01 else f"PAGAMENTO {acc} {m:%m/%Y}")
            taxes = 0.0
            for acc, rate in (("2006010001", .0065), ("2006010003", .03), ("2006010006", .03), ("2006020001", .012),
                              ("2006020002", .015), ("2006020003", .0108)):
                taxes += round(rev * rate, 2)
                entry(o, acc, OWN_COMPANY, round(rev * rate, 2), add_days(m, 50), 610, "tax", OWN_COMPANY,
                      f"IMPOSTO {acc} COMPETÊNCIA {m:%m/%Y}")
            entry(o, "2003060011", OWN_COMPANY, round(rev * .01, 2), add_days(m, 28), 520, "accrual", OWN_COMPANY,
                  f"PREVISÃO DE RESCISÃO {m:%m/%Y}", force_open=True)
            if o["tipo"] != "PRÓPRIA" and m.month in (3, 6, 9, 12):  # OP 733: partner receives its share of taxes
                for p in partners[1:]:
                    entry(o, "3002010002", name_by_id[p["empresa_id"]], round(taxes * 3 * p["pct_participacao"], 2),
                          add_days(m, 55), 733, "tax_transfer", OWN_COMPANY, "TRANSFERÊNCIA DE IMPOSTOS AO SÓCIO")
            if o["tipo"] != "PRÓPRIA" and rng.random() < .08:  # OP 823: a partner transfers revenue to the work
                p = rng.choice(partners[1:])
                entry(o, "3002010003", name_by_id[p["empresa_id"]], round(rev * .1, 2), add_days(m, 20), 823,
                      "rev_transfer", OWN_COMPANY, "TRANSFERÊNCIA DE RECEITA DO SÓCIO")
            if o["tipo"] == "SCP":
                entry(o, "4002010002", OWN_COMPANY, round(rev * .11, 2), add_days(due, 1), 615, "inss",
                      OWN_COMPANY, "INSS RETIDO NA FATURA")
                if rng.random() < .5:
                    entry(o, "2003060003", OWN_COMPANY, round(rev * .04, 2), add_days(m, 20), 520, "inss_consumido",
                          OWN_COMPANY, "INSS COMPENSADO COM CRÉDITO")
            if rng.random() < .25:  # partner contribution (aporte) and occasional return (devolução)
                p = rng.choice(partners)
                amount = round(rng.uniform(5e4, 4e5), 2)
                entry(o, "3001010001", OWN_COMPANY, amount, add_days(m, 10), rng.choice(APORTE_OPS), "aporte",
                      name_by_id[p["empresa_id"]], "APORTE DE CAPITAL NA OBRA")
                if rng.random() < .3:
                    entry(o, "3001010002", name_by_id[p["empresa_id"]], round(amount * .5, 2), add_days(m, 40),
                          rng.choice(APORTE_OPS), "devolucao", OWN_COMPANY, "DEVOLUÇÃO DE APORTE")
            if partners and m.month in (3, 6, 9, 12):
                for p in partners:
                    if p["pct_tac"]:
                        acc = "2006030007" if o["tipo"] == "PRÓPRIA" else "2006030009"
                        entry(o, acc, name_by_id[p["empresa_id"]], round(rev * 3 * p["pct_tac"], 2),
                              add_days(m, 28), 520, "tac", OWN_COMPANY, "TAC TRIMESTRAL")
    return companies, obras, socios, entries


# --------------------------------------------------------------------------- writers
def write_seed(out, companies, obras, socios, entries):
    d = out / "erp_seed"
    d.mkdir(parents=True, exist_ok=True)
    plano = [{"codigo": c, "descricao": desc, "regra_classificacao": rule,
              "natureza": "RECEITA" if c in REVENUE_CODES else "DESPESA"} for c, desc, rule in ACCOUNTS]
    ops = [{"op_codigo": k, "descricao": v} for k, v in OPS.items()]
    obras_rows = [{**{k: v for k, v in o.items() if k != "contas_inss"},
                   "contas_inss": "|".join(o["contas_inss"]) or None} for o in obras]
    for name, rows in [("empresa", companies), ("plano_contas", plano), ("operacao", ops), ("obra", obras_rows),
                       ("obra_socio", socios), ("lancamento", entries)]:
        with open(d / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


def bd_row(e, ctx):
    """One lancamento as the columns of the manual Excel export (before Power Query)."""
    o, comp = ctx["obra"][e["numero_obra"]], ctx["company"][e["contraparte_id"]]
    acc = e["plano_conta"]
    return {
        "CENTRO DE CUSTO": "INATIVO" if not o["ativo"] else o["numero"],
        "DESCRITIVO DO CENTRO DE CUSTO": o["descricao"], "CNPJ FORNECEDOR": comp["cnpj"],
        "FORNECEDOR": comp["razao_social"], "PLANO DE CONTA": dotted(acc), "PLANO DE CONTA_1": ctx["acc"][acc],
        "VALOR TOTAL EFETUADO": e["valor_efetuado"], "VALOR TOTAL PREVISTO": e["valor_previsto"],
        "VALOR TOTAL COMP.": e["valor_compromissado"], "EMPRESA": e["empresa"],
        "DESCRIÇÃO DA EMPRESA": e["empresa_recbto_pagto"], "NUMDOC": e["numdoc"], "DT. RECTO": e["dt_recto"],
        "DT. \nDOC": e["dt_doc"], "DT.\nVENC": e["dt_venc"], "DT.\nVENCORIG": e["dt_vencorig"],
        "DT.\nMOVBANC": e["dt_movbanc"], "HISTORICO": e["historico"], "OP.": e["op_codigo"],
        "OP._2": OPS[e["op_codigo"]], "RI": e["ri"], "TOTATUALTXADMPREV": e["tx_adm_prev"],
        "TOTATUALTXADMCOMP": e["tx_adm_comp"], "TOTATUALTXADMEFETU": e["tx_adm_efetu"], "APREC": e["aprec"],
        "APSTATUS": e["apstatus"], "APCONTACDG": e["apcontacdg"], "APCONTA": e["apconta"],
        "ARCONTACDG": e["arcontacdg"], "ARCONTA": e["arconta"], "RIPEDIDOS": e["ripedidos"], "ARREC": e["arrec"],
        "ARSTATUS": e["arstatus"], "EMPREGRUPO": GROUP[0], "EMPREGRUPODESC": GROUP[1],
    }


# Column order of the two sheets. None = blank header (Power Query names it ColumnN).
COMP_COLS = [None, "CENTRO DE CUSTO", "DESCRITIVO DO CENTRO DE CUSTO", "CNPJ FORNECEDOR", "FORNECEDOR",
             "PLANO DE CONTA", "PLANO DE CONTA_1", "VALOR TOTAL EFETUADO", "VALOR TOTAL PREVISTO", "VALOR TOTAL COMP.",
             "EMPRESA", "DESCRIÇÃO DA EMPRESA", "NUMDOC", "DT. RECTO", "DT. \nDOC", "DT.\nVENC", "DT.\nVENCORIG",
             "DT.\nMOVBANC", "HISTORICO", "OP.", "OP._2", "RI", "TOTATUALTXADMPREV", "TOTATUALTXADMCOMP",
             "TOTATUALTXADMEFETU", "APREC", "APSTATUS", "APCONTACDG", "APCONTA", "ARCONTACDG", "ARCONTA",
             "RIPEDIDOS", "ARREC", "ARSTATUS", "EMPREGRUPO", "EMPREGRUPODESC"]
EFET_EXTRA = ["OBSERVAÇÃO", "(+) RECEBIMENTO EM CONTA VÁLIDA", "(-) IMPOSTO RETIDO CONSIDERADO NA CONTA VÁLIDA",
              "TOTAL RECEBIDO EM CONTA INTERNA", "(+) RECEBIDO POR CONTA INTERNA A SER CONSIDERADO",
              "(+) 3.0 Suprimidos a considerar", "PAGAMENTOS", "(+) PAGOS EM CONTA VÁLIDA",
              "(-) IMPOSTO RETIDO CONSIDERADO NA CONTA VÁLIDA (OLD)", '(-) PAG. EM CONTA VÁLIDA "S/ Mov. Bancária"',
              "TOTAL PAGOS EM CONTA INTERNA", "RECEBIMENTO", "TAC INTERNA", "LOCAÇÃO DE EQUIPAMENTOS PRÓPRIOS",
              "IMPOSTOS PAGOS COM CRÉDITO (INSS/ISS)", "(+) PAGOS POR CONTA INTERNA A SER CONSIDERADO",
              "(+) 4.0 Suprimidos a considerar", "RECEITA", "DESPESA"]
_efet_named = (["CENTRO DE CUSTO", "DESCRITIVO DO CENTRO DE CUSTO", "CNPJ FORNECEDOR", "FORNECEDOR/CLIENTE",
                "PLANO DE CONTA", "PLANO DE CONTA_1", "VALOR TOTAL EFETUADO", "VALOR TOTAL PREVISTO",
                "VALOR TOTAL COMP.", "EMPRESA", "EMPRESA RECBTO/PAGTO", "NUMDOC", "DT. RECTO", "DT. \nDOC",
                "DT.\nVENC", "DT.\nVENCORIG", "DT.\nMOVBANC", "HISTORICO"]  # columns 2-19, then blank Column20
               + ["OP.", "OP._2", "RI", "TOTATUALTXADMPREV", "TOTATUALTXADMCOMP", "TOTATUALTXADMEFETU", "APREC",
                  "APSTATUS", "APCONTACDG", "APCONTA", "ARCONTACDG", "ARCONTA", "RIPEDIDOS", "ARREC", "ARSTATUS",
                  "EMPREGRUPO", "EMPREGRUPODESC"] + EFET_EXTRA)
EFET_COLS = [None] + _efet_named[:18] + [None] + _efet_named[18:] + [None] * 17  # 73 columns: Column57..73 blank
assert len(EFET_COLS) == 73 and EFET_COLS[19] is None and len(_efet_named) == 54


def write_sheet(ws, cols, rows, junk_rows, title):
    ws.cell(1, 1, title)  # anchors the used range at A1, like the original export
    ws.cell(2, 1, f"Gerado em {EXCEL_CUT:%d/%m/%Y} - DADOS FICTÍCIOS")
    ws.cell(2, len(cols), "conferência")  # stray cell keeps the trailing blank columns in the used range
    hdr = junk_rows + 1
    for j, c in enumerate(cols, 1):
        if c is not None:
            ws.cell(hdr, j, c)
    for i, r in enumerate(rows, hdr + 1):
        for j, c in enumerate(cols, 1):
            v = r.get(c) if c else r.get(f"__col{j}")
            if v is not None:
                ws.cell(i, j, v)


def write_excel(out, rng, obras, socios, entries, ctx):
    d = out / "excel"
    d.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "BD EFETUADO"

    efet, comp = [], []
    for e in entries:
        if e["dt_doc"] > add_days(EXCEL_CUT, 180):  # committed = open items + 6-month forecast at the cut date
            continue
        r = bd_row(e, ctx)
        if e["status"] == "REALIZADO" and e["dt_movbanc"] <= EXCEL_CUT:
            r["FORNECEDOR/CLIENTE"], r["EMPRESA RECBTO/PAGTO"] = r.pop("FORNECEDOR"), r.pop("DESCRIÇÃO DA EMPRESA")
            r["RECEITA" if e["aprec"] == "AR" else "DESPESA"] = e["valor_efetuado"]
            r["TAC INTERNA"] = 0
            if rng.random() < .004:  # issue: realized entry exported without bank date -> dropped by the M filter
                r["DT.\nMOVBANC"] = rng.choice([None, ""])
            if rng.random() < .03:
                r["__col20"] = "x"  # stray helper marks in the unnamed column 20
            efet.append(r)
        else:  # still open at the cut date: no payment information yet
            r.update({"VALOR TOTAL EFETUADO": 0, "TOTATUALTXADMEFETU": 0, "DT.\nMOVBANC": None, "DT. RECTO": None,
                      "VALOR TOTAL COMP.": e["valor_previsto"], "TOTATUALTXADMCOMP": e["tx_adm_prev"]})
            r.update({k: "ABERTO" for k in ("APSTATUS", "ARSTATUS") if r[k]})
            comp.append(r)
    for r in rng.sample(efet, len(efet) // 200):  # issue: copy-paste duplicates (synthetic test case)
        efet.insert(rng.randrange(len(efet)), dict(r))
    total = {"DESCRITIVO DO CENTRO DE CUSTO": "TOTAL GERAL",
             "VALOR TOTAL PREVISTO": round(sum(r["VALOR TOTAL PREVISTO"] for r in comp), 2),
             "VALOR TOTAL COMP.": round(sum(r["VALOR TOTAL COMP."] for r in comp), 2)}
    write_sheet(ws, EFET_COLS, efet, 13, "RELATÓRIO GERENCIAL - VALORES EFETUADOS")
    write_sheet(wb.create_sheet("BD COMPROMISSADO"), COMP_COLS, comp + [{}, total], 8,
                "RELATÓRIO GERENCIAL - VALORES COMPROMISSADOS")
    wb.save(d / f"Banco de Dados Gerencial - Set_{EXCEL_CUT.year}.xlsx")

    # ---- Classificação das Obras (wide: 24 partner slots x 3 attributes)
    head = ["TIPO CLIENTE", "GRUPO", "NÚMERO", "UNIDADE DE NEGÓCIO", "CENTROS DE CUSTOS", "CONTROLE", "UN/ Gerencia",
            "UF", "Cliente", "% AURORA -\nVERTICE", "TIPO ", "VALOR ATUAL DO CONTRATO", "% FÍSICO EXECUTADO",
            "CRÉDITO DE INSS", "CONTA INSS 01", "CONTA INSS 02", "CONTA INSS 03"]
    slots = [f"Sócio {i} - {a}" for i in range(1, 25) for a in ("Descrição", "% Particiapação Societária", "% TAC")]
    cols = [None] + head + slots + [None]
    assert len(cols) == 91
    by_obra = {}
    for s in socios:
        by_obra.setdefault(s["numero_obra"], []).append(s)
    rows, rows_v2 = [], []
    for k, o in enumerate(obras):
        if k and k % 12 == 0:
            rows.append({"TIPO CLIENTE": "SUBTOTAL"})  # separator row without NÚMERO
        manager = TYPO_MANAGER[0] if o["gerente"] == TYPO_MANAGER[1] and rng.random() < .5 else o["gerente"]
        base = {"TIPO CLIENTE": o["tipo_cliente"], "GRUPO": o["grupo"], "NÚMERO": o["numero"],
                "UNIDADE DE NEGÓCIO": o["unidade_negocio"], "CENTROS DE CUSTOS": o["descricao"],
                "CONTROLE": o["controle"], "UN/ Gerencia": manager, "UF": o["uf"], "Cliente": o["cliente"],
                "% AURORA -\nVERTICE": o["pct_empresa_parceira"] if rng.random() > .1 else None, "TIPO ": o["tipo"],
                "VALOR ATUAL DO CONTRATO": o["valor_contrato"], "% FÍSICO EXECUTADO": o["pct_fisico"],
                "CRÉDITO DE INSS": o["credito_inss"]}
        for i, c in enumerate(o["contas_inss"], 1):
            base[f"CONTA INSS 0{i}"] = c
        r = dict(base)
        for s in by_obra[o["numero"]]:
            name = ctx["company"][s["empresa_id"]]["razao_social"]
            # issue: description left blank in some rows (filled down/up by the M code)
            r[f"Sócio {s['socio_seq']} - Descrição"] = None if rng.random() < .05 else name
            r[f"Sócio {s['socio_seq']} - % Particiapação Societária"] = s["pct_participacao"]
            r[f"Sócio {s['socio_seq']} - % TAC"] = s["pct_tac"] or None
        rows.append(r)
        if rng.random() > .05:  # issue: the 2.0 file is out of sync (a few works missing, values drift)
            v2 = {k2: v for k2, v in base.items() if k2 != "GRUPO"}
            v2["UN/ Gerencia"] = o["gerente"]
            v2["VALOR ATUAL DO CONTRATO"] = round(o["valor_contrato"] * rng.choice([1, 1, 1, .97, 1.05]), 2)
            first = by_obra[o["numero"]][0]
            v2["Sócio 1 - Descrição"] = ctx["company"][first["empresa_id"]]["razao_social"]
            v2["Sócio 1 - % Particiapação Societária"] = first["pct_participacao"]
            v2["Sócio 1  - % TAC"] = first["pct_tac"]  # double space, as in the original header
            rows_v2.append(v2)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Classif. Obras"
    ws.cell(1, 1, "CLASSIFICAÇÃO DAS OBRAS - DADOS FICTÍCIOS")
    ws.cell(1, 91, "rev.")
    for j, c in enumerate(cols, 1):
        if c:
            ws.cell(3, j, c)
            ws.cell(4, j, "(texto)" if not c.startswith(("%", "Sócio", "VALOR")) else "(número)")
    for i, r in enumerate(rows, 5):
        for j, c in enumerate(cols, 1):
            if c and r.get(c) is not None:
                ws.cell(i, j, r[c])
    wb.save(d / "Classificação das Obras.xlsx")

    head2 = ["TIPO CLIENTE", "NÚMERO", "UNIDADE DE NEGÓCIO", "CENTROS DE CUSTOS", "CONTROLE", "UN/ Gerencia", "UF",
             "Cliente", "% AURORA -\nVERTICE", "TIPO ", "Sócio 1 - Descrição", "Sócio 1 - % Particiapação Societária",
             "Sócio 1  - % TAC", "VALOR ATUAL DO CONTRATO", "% FÍSICO EXECUTADO", "CRÉDITO DE INSS",
             "CONTA INSS 01", "CONTA INSS 02", "CONTA INSS 03"]
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Aurora"
    ws.append(head2)
    for r in rows_v2:
        ws.append([r.get(c) for c in head2])
    wb.save(d / "Classificação das Obras 2.0.xlsx")

    # ---- Lista Plano de Contas .xls (legacy format; trailing space in the file name is intentional)
    book = xlwt.Workbook(encoding="utf-8")
    sh = book.add_sheet("Planilha1")
    for j, c in enumerate(["Plano de Contas", "Desc.Plano Contas", "REGRA PARA CLASSIFICAÇÃO"]):
        sh.write(0, j, c)
    for i, (code, desc, rule) in enumerate(ACCOUNTS, 1):
        sh.write(i, 0, int(code))
        sh.write(i, 1, desc)
        if rule:
            sh.write(i, 2, rule)
        if i == 3:
            sh.write(i, 5, "ver com contabilidade")  # stray note -> Column4..6 exist
    book.save(str(d / "Lista Plano de Contas .xls"))
    return efet, comp


CSV_RENAMES = {"PLANO DE CONTA": "RZANALCONSOL_CCD", "PLANO DE CONTA.1": "RZANALCONSOL_CCDDESC",
               "CENTRO DE CUSTO": "RZANALCONSOL_EMPRD", "DESCRITIVO DO CENTRO DE CUSTO": "RZANALCONSOL_EMPRDDESC",
               "VALOR TOTAL COMP.": "RZANALCONSOL_TOTCOMP", "VALOR TOTAL PREVISTO": "RZANALCONSOL_TOTPREV",
               "VALOR TOTAL EFETUADO": "RZANALCONSOL_TOTEFETU", "DT.VENC": "RZANALCONSOL_DTVENC",
               "FORNECEDOR/CLIENTE": "RZANALCONSOL_RAZAO", "CNPJ FORNECEDOR": "RZANALCONSOL_FORNCPFCNPJ",
               "EMPRESA": "RZANALCONSOL_EMPRE", "EMPRESA RECBTO/PAGTO": "RZANALCONSOL_EMPRERZ",
               "DT.MOVBANC": "RZANALCONSOL_DTMOVBANC", "HISTORICO": "RZANALCONSOL_HISTORICO",
               "OP.": "RZANALCONSOL_OPERACAO", "OP.DESC": "RZANALCONSOL_OPERACAODESC", "RI": "RZANALCONSOL_RI",
               "APCONTA": "RZANALCONSOL_APCONTA"}
CSV_OTHER = ["RZANALCONSOL_DTINI", "RZANALCONSOL_DTFIM", "RZANALCONSOL_CCDINI", "RZANALCONSOL_CCDDESCINI",
             "RZANALCONSOL_CCDFIM", "RZANALCONSOL_CCDDESCFIM", "RZANALCONSOL_EMPRESEL", "RZANALCONSOL_EMPRERZSEL",
             "RZANALCONSOL_EMPRENOMEIMAGEMSEL", "RZANALCONSOL_BLOCO", "RZANALCONSOL_BLOCODESC", "RZANALCONSOL_CCDTIPO",
             "RZANALCONSOL_PGTOREC", "RZANALCONSOL_TOT", "RZANALCONSOL_TOTSALDOATUAL", "RZANALCONSOL_DTVENCORIG",
             "RZANALCONSOL_EMPRENOMEIMAGEM", "RZANALCONSOL_NUMDOC", "RZANALCONSOL_APREC", "RZANALCONSOL_FD",
             "RZANALCONSOL_INADIMPLENTE", "RZANALCONSOL_DTRECTO", "RZANALCONSOL_TIPOREG", "RZANALPREV_TOTRESP",
             "RZANALCONSOL_TOTATUALTXADMPREV", "RZANALCONSOL_TOTATUALTXADMCOMP", "RZANALCONSOL_TOTATUALTXADMEFETU",
             "RZANALCONSOL_DTDOC", "RZANALCONSOL_APCONTACDG", "RZANALCONSOL_ARCONTACDG", "RZANALCONSOL_ARCONTA",
             "RZANALCONSOL_RIPEDIDOS", "RZANALCONSOL_ARREC", "RZANALCONSOL_ENVIOCBRNUM", "RZANALCONSOL_ENVIOCBRDATA",
             "RZANALCONSOL_APSTATUS", "RZANALCONSOL_ARSTATUS", "RZANALCONSOL_SUPRIMEFLUXO", "RZANALCONSOL_TPMOVDESC",
             "RZANALCONSOL_CTR", "RZANALCONSOL_PARCELANOMINAL", "RZANALCONSOL_TOTJUROS", "RZANALCONSOL_TOTMULTA",
             "RZANALCONSOL_TOTDESCONTO", "RZANALCONSOL_RIDTBAIXA", "RZANALCONSOL_ESPECIE", "RZANALCONSOL_TEMPRD",
             "RZANALCONSOL_TEMPRDDESC", "RZANALCONSOL_DEBITOCCTB", "RZANALCONSOL_DTRECITEMINSUMO", "RZANALCONSOL_CCTB",
             "RZANALCONSOL_IMOBILIARIA", "RZANALCONSOL_CODCTRFINAN", "RZANALCONSOL_BLOCOS", "RZANALCONSOL_DESCBLOCOS",
             "RZANALCONSOL_UNDCDG", "RZANALCONSOL_UNDDESC", "RZANALCONSOL_EMPREGRUPO", "RZANALCONSOL_EMPREGRUPODESC",
             "RZANALCONSOL_EMPRDGRUPO", "RZANALCONSOL_EMPRDGRUPODESC"]
CSV_COLS = list(CSV_RENAMES.values()) + CSV_OTHER
assert len(CSV_COLS) == 79 and len(set(CSV_COLS)) == 79


def write_erp_csv(out, entries, ctx):
    """ERP ledger extract: comma-delimited, NOT quoted (the M code reads it with QuoteStyle.None)."""
    d = out / "erp_export"
    d.mkdir(parents=True, exist_ok=True)
    f = d / "_SELECT_RZ_SELECT_FIRST_1_LISTAEMPREGRUPO_EMPREGRUPO_FROM_S_CTB__202601131620_dados.csv"
    fmt = lambda x: "" if x is None else (x.strftime("%Y-%m-%d") if isinstance(x, dt.date) else str(x))
    n = 0
    with open(f, "w", encoding="utf-8", newline="") as fh:
        fh.write(",".join(CSV_COLS) + "\n")
        for e in entries:
            if not (e["dt_movbanc"] and CSV_FROM <= e["dt_movbanc"] <= ERP_EXTRACT):
                continue
            o, comp = ctx["obra"][e["numero_obra"]], ctx["company"][e["contraparte_id"]]
            v = {"RZANALCONSOL_CCD": e["plano_conta"], "RZANALCONSOL_CCDDESC": ctx["acc"][e["plano_conta"]],
                 "RZANALCONSOL_EMPRD": o["numero"], "RZANALCONSOL_EMPRDDESC": o["descricao"],
                 "RZANALCONSOL_TOTCOMP": e["valor_compromissado"], "RZANALCONSOL_TOTPREV": e["valor_previsto"],
                 "RZANALCONSOL_TOTEFETU": e["valor_efetuado"], "RZANALCONSOL_DTVENC": e["dt_venc"],
                 "RZANALCONSOL_RAZAO": comp["razao_social"], "RZANALCONSOL_FORNCPFCNPJ": comp["cnpj"],
                 "RZANALCONSOL_EMPRE": e["empresa"], "RZANALCONSOL_EMPRERZ": e["empresa_recbto_pagto"],
                 "RZANALCONSOL_DTMOVBANC": e["dt_movbanc"], "RZANALCONSOL_HISTORICO": e["historico"],
                 "RZANALCONSOL_OPERACAO": e["op_codigo"], "RZANALCONSOL_OPERACAODESC": OPS[e["op_codigo"]],
                 "RZANALCONSOL_RI": e["ri"], "RZANALCONSOL_APCONTA": e["apconta"],
                 "RZANALCONSOL_DTINI": CSV_FROM, "RZANALCONSOL_DTFIM": ERP_EXTRACT,
                 "RZANALCONSOL_DTVENCORIG": e["dt_vencorig"], "RZANALCONSOL_NUMDOC": e["numdoc"],
                 "RZANALCONSOL_APREC": e["aprec"], "RZANALCONSOL_DTRECTO": e["dt_recto"], "RZANALCONSOL_DTDOC": e["dt_doc"],
                 "RZANALCONSOL_EMPREGRUPO": GROUP[0], "RZANALCONSOL_EMPREGRUPODESC": GROUP[1],
                 "RZANALCONSOL_APSTATUS": e["apstatus"], "RZANALCONSOL_ARSTATUS": e["arstatus"]}
            # shortcut: values are written raw on purpose; commas inside HISTORICO shift columns (known issue)
            fh.write(",".join(fmt(v.get(c)) for c in CSV_COLS) + "\n")
            n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=str(Path(__file__).parent / "output"))
    a = ap.parse_args()
    rng = random.Random(a.seed)
    out = Path(a.out)
    companies, obras, socios, entries = build(rng)
    ctx = {"obra": {o["numero"]: o for o in obras}, "company": {c["empresa_id"]: c for c in companies},
           "acc": {c: d for c, d, _ in ACCOUNTS}}
    write_seed(out, companies, obras, socios, entries)
    efet, comp = write_excel(out, rng, obras, socios, entries, ctx)
    n_csv = write_erp_csv(out, entries, ctx)
    print(f"obras={len(obras)} socios={len(socios)} lancamentos={len(entries)} "
          f"excel_efetuado={len(efet)} excel_compromissado={len(comp)} csv_rows={n_csv} -> {out}")


if __name__ == "__main__":
    main()
