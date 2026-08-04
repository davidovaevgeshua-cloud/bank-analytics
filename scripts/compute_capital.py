"""
Расчёт капитала, нормативов достаточности, структуры баланса и прибыли по
банкам за один отчётный период (формы 0409101, 0409123, 0409135, 0409102).

Логика классификации счетов и агрегации полностью повторяет то, что уже
проверено вручную в анализе (сверено с публичными цифрами Сбербанка/ВТБ
и с независимой оценкой Н1.0 по сектору за май 2026 — см. комментарии в
data/capital_history.json / footer дашборда).
"""
from pathlib import Path

from cbr_forms_parser import read_cbr_dbf
from classify import (classify_asset, classify_liability, ASSET_CATEGORIES,
                       LIABILITY_CATEGORIES, CREDIT_PORTFOLIO_SUB)


def _find(files, suffix_upper):
    for f in files:
        if f.name.upper().endswith(suffix_upper) and "NAMES" not in f.name.upper():
            return f
    return None


def compute_balance_breakdown(files_101):
    """files_101: список путей dbf, извлечённых из архива формы 101.
    Возвращает {regn (int): {assets: {...}, liab: {...}, credit_sub: {...}}}"""
    f = _find(files_101, "B1.DBF")
    if f is None:
        return {}
    _, records = read_cbr_dbf(f)
    out = {}
    for r in records:
        if r['PLAN'] != 'А':
            continue
        regn = r['REGN']
        if regn not in out:
            out[regn] = {
                "assets": {k: 0.0 for k in ASSET_CATEGORIES},
                "liab": {k: 0.0 for k in LIABILITY_CATEGORIES},
                "credit_sub": {k: 0.0 for k in CREDIT_PORTFOLIO_SUB},
            }
        val = r['IITG'] or 0
        if r['A_P'] == '1':
            res = classify_asset(r['NUM_SC'])
            if res is None:
                continue
            cat, subcat = res
            out[regn]["assets"][cat] += val
            if subcat is not None:
                out[regn]["credit_sub"][subcat] += val
        elif r['A_P'] == '2':
            cat = classify_liability(r['NUM_SC'])
            if cat is None:
                continue
            out[regn]["liab"][cat] += val
    return out


def compute_capital(files_123):
    f = _find(files_123, "123D.DBF")
    if f is None:
        return {}
    _, records = read_cbr_dbf(f)
    return {r['REGN']: r['C3'] for r in records if r['C1'] == '000'}


def compute_normatives(files_135):
    f = _find(files_135, "135_3.DBF")
    if f is None:
        return {}
    _, records = read_cbr_dbf(f)
    norms = {}
    for r in records:
        norms.setdefault(r['REGN'], {})[r['C1_3']] = r['C2_3']
    return norms


def compute_net_profit_ytd(p1_data):
    """p1_data: {regn (int): {code (str): value}} — результат dbf_parser.parse_p1
    для формы 102 этого же периода (символы 61101/61102, нарастающим итогом)."""
    profit = {}
    for regn, rec in p1_data.items():
        p = rec.get('61101') or 0
        m = rec.get('61102') or 0
        profit[regn] = p - m
    return profit


def build_period_entry(files_101, files_123, files_135, p1_data, data_year, data_month, months_elapsed):
    """Собирает {regn (str): entry} для всех банков, встретившихся хотя бы в
    одной из форм за период — формат совместим с data/capital_history.json."""
    bal = compute_balance_breakdown(files_101) if files_101 else {}
    capital = compute_capital(files_123) if files_123 else {}
    norms = compute_normatives(files_135) if files_135 else {}
    profit = compute_net_profit_ytd(p1_data) if p1_data else {}

    regns = set(bal) | set(capital) | set(norms) | set(profit)
    period_data = {}
    for regn in regns:
        b = bal.get(regn, {"assets": {}, "liab": {}, "credit_sub": {}})
        total_assets = sum(b["assets"].values()) if b["assets"] else None
        total_liab = sum(b["liab"].values()) if b["liab"] else None
        entry = {
            "assets_by_cat": b["assets"] if b["assets"] else None,
            "liab_by_cat": b["liab"] if b["liab"] else None,
            "credit_sub": b["credit_sub"] if b["credit_sub"] else None,
            "assets": total_assets,
            "liabilities": total_liab,
            "capital": capital.get(regn),
            "n1_0": (norms.get(regn) or {}).get('Н1.0'),
            "n1_1": (norms.get(regn) or {}).get('Н1.1'),
            "n1_2": (norms.get(regn) or {}).get('Н1.2'),
            "net_profit_ytd": profit.get(regn),
            "data_year": data_year, "data_month": data_month, "months_elapsed": months_elapsed,
        }
        period_data[str(regn)] = entry
    return period_data
