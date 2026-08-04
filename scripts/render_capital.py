"""
Строит payload для дашборда "Капитал, ROE/ROA, структура баланса" из
накопленной истории data/capital_history.json (сырые компоненты по
каждому банку за каждый период — аналог того, как compute_cir.py хранит
сырые ЧПД/комиссии/АХР для CIR, а не готовые проценты).

Логика идентична processed/aggregate_full.py, использованному при
первичном построении дашборда в этой сессии (агрегация сектора как
Σкапитал / Σ RWA_implied, ROE/ROA месячные + YTD, г/г и YTD-рост по
категориям активов/пассивов/кредитного портфеля).

Список банков (BANK_ORDER, BANKS) переиспользуется из compute_cir.py,
чтобы оба дашборда на странице показывали один и тот же набор из 13
банков.
"""
import json
from pathlib import Path

from compute_cir import BANKS, BANK_ORDER
from classify import ASSET_CATEGORIES, LIABILITY_CATEGORIES, CREDIT_PORTFOLIO_SUB

ASSET_KEYS = list(ASSET_CATEGORIES.keys())
LIAB_KEYS = list(LIABILITY_CATEGORIES.keys())
CREDIT_KEYS = list(CREDIT_PORTFOLIO_SUB.keys())


def _is_month_period(label: str) -> bool:
    return len(label) == 6 and label.isdigit()


def sector_entry_for_period(period_data: dict):
    """period_data: history['periods'][label] = {regn_str: entry}."""
    entry = {
        "assets_by_cat": {k: 0.0 for k in ASSET_KEYS},
        "liab_by_cat": {k: 0.0 for k in LIAB_KEYS},
        "credit_sub": {k: 0.0 for k in CREDIT_KEYS},
        "assets": 0.0, "liabilities": 0.0, "capital": 0.0,
        "net_profit_ytd": None,
        "rwa_implied_sum": 0.0, "cap_for_n1_0": 0.0,
        "months_elapsed": None, "data_year": None, "data_month": None,
    }
    any_assets = False
    profit_sum = None
    for regn, v in period_data.items():
        if v.get("assets_by_cat"):
            any_assets = True
            for k in ASSET_KEYS:
                entry["assets_by_cat"][k] += v["assets_by_cat"].get(k, 0) or 0
            entry["assets"] += v["assets"] or 0
        if v.get("liab_by_cat"):
            for k in LIAB_KEYS:
                entry["liab_by_cat"][k] += v["liab_by_cat"].get(k, 0) or 0
            entry["liabilities"] += v["liabilities"] or 0
        if v.get("credit_sub"):
            for k in CREDIT_KEYS:
                entry["credit_sub"][k] += v["credit_sub"].get(k, 0) or 0
        if v.get("capital"):
            entry["capital"] += v["capital"]
        if v.get("net_profit_ytd") is not None:
            profit_sum = (profit_sum or 0) + v["net_profit_ytd"]
        if v.get("n1_0") is not None and v.get("n1_0") > 0 and v.get("capital"):
            rwa_i = v["capital"] / (v["n1_0"] / 100)
            entry["rwa_implied_sum"] += rwa_i
            entry["cap_for_n1_0"] += v["capital"]
        entry["months_elapsed"] = v.get("months_elapsed")
        entry["data_year"] = v.get("data_year")
        entry["data_month"] = v.get("data_month")
    entry["net_profit_ytd"] = profit_sum
    entry["n1_0"] = (entry["cap_for_n1_0"] / entry["rwa_implied_sum"] * 100) if entry["rwa_implied_sum"] else None
    if not any_assets:
        entry["assets_by_cat"] = None
        entry["liab_by_cat"] = None
        entry["credit_sub"] = None
        entry["assets"] = None
        entry["liabilities"] = None
    return entry


def build_timeseries(periods, entity_getter):
    ts = {
        "assets": [], "liabilities": [], "capital": [], "n1_0": [],
        "assets_by_cat": {k: [] for k in ASSET_KEYS},
        "liab_by_cat": {k: [] for k in LIAB_KEYS},
        "credit_sub": {k: [] for k in CREDIT_KEYS},
        "roe_month": [], "roa_month": [], "roe_ytd": [], "roa_ytd": [],
        "assets_yoy": [], "assets_ytd_growth": [],
        "liab_yoy": [], "liab_ytd_growth": [],
        "credit_yoy": [], "credit_ytd_growth": [],
    }
    entries = [entity_getter(p) for p in periods]

    assets_raw = [e["assets"] if e else None for e in entries]
    liab_raw = [e["liabilities"] if e else None for e in entries]
    credit_raw = [(sum(e["credit_sub"].values()) if e and e.get("credit_sub") else None) for e in entries]
    capital_raw = [e["capital"] if e and e.get("capital") else None for e in entries]
    profit_raw = [e["net_profit_ytd"] if e else None for e in entries]
    year_raw = [e["data_year"] if e else None for e in entries]
    months_raw = [e["months_elapsed"] if e else None for e in entries]

    for i, e in enumerate(entries):
        ts["assets"].append(assets_raw[i] / 1e6 if assets_raw[i] else None)
        ts["liabilities"].append(liab_raw[i] / 1e6 if liab_raw[i] else None)
        ts["capital"].append(capital_raw[i] / 1e6 if capital_raw[i] else None)
        ts["n1_0"].append(e["n1_0"] if e else None)
        for k in ASSET_KEYS:
            v = e["assets_by_cat"].get(k) if e and e.get("assets_by_cat") else None
            ts["assets_by_cat"][k].append(v / 1e6 if v is not None else None)
        for k in LIAB_KEYS:
            v = e["liab_by_cat"].get(k) if e and e.get("liab_by_cat") else None
            ts["liab_by_cat"][k].append(v / 1e6 if v is not None else None)
        for k in CREDIT_KEYS:
            v = e["credit_sub"].get(k) if e and e.get("credit_sub") else None
            ts["credit_sub"][k].append(v / 1e6 if v is not None else None)

    last_ytd_in_year = {}
    for i in range(len(periods)):
        y = year_raw[i]; m = months_raw[i]; p = profit_raw[i]
        if p is None or y is None:
            ts["roe_month"].append(None); ts["roa_month"].append(None)
            continue
        prev = last_ytd_in_year.get(y)
        if prev is not None:
            _, prev_val, prev_m = prev
            period_profit = p - prev_val
            period_months = m - prev_m
        else:
            period_profit = p
            period_months = m
        last_ytd_in_year[y] = (i, p, m)
        if period_months and capital_raw[i]:
            ann = period_profit * 12 / period_months
            ts["roe_month"].append(ann / capital_raw[i] * 100)
        else:
            ts["roe_month"].append(None)
        if period_months and assets_raw[i]:
            ann = period_profit * 12 / period_months
            ts["roa_month"].append(ann / assets_raw[i] * 100)
        else:
            ts["roa_month"].append(None)

    year_caps = {}
    year_assets = {}
    for i in range(len(periods)):
        y = year_raw[i]
        if y is None:
            ts["roe_ytd"].append(None); ts["roa_ytd"].append(None)
            continue
        if capital_raw[i]:
            year_caps.setdefault(y, []).append(capital_raw[i])
        if assets_raw[i]:
            year_assets.setdefault(y, []).append(assets_raw[i])
        p = profit_raw[i]; m = months_raw[i]
        if p is None or not m:
            ts["roe_ytd"].append(None); ts["roa_ytd"].append(None)
            continue
        ann = p * 12 / m
        avg_cap = sum(year_caps.get(y, [])) / len(year_caps[y]) if year_caps.get(y) else None
        avg_ast = sum(year_assets.get(y, [])) / len(year_assets[y]) if year_assets.get(y) else None
        ts["roe_ytd"].append(ann / avg_cap * 100 if avg_cap else None)
        ts["roa_ytd"].append(ann / avg_ast * 100 if avg_ast else None)

    def yoy_and_ytd(raw):
        yoy = [None] * len(raw)
        ytdg = [None] * len(raw)
        first_idx_of_year = {}
        for i in range(len(raw)):
            y = year_raw[i]
            if y not in first_idx_of_year:
                first_idx_of_year[y] = i
            if i >= 12 and raw[i] is not None and raw[i - 12] not in (None, 0):
                yoy[i] = (raw[i] / raw[i - 12] - 1) * 100
            base_idx = first_idx_of_year[y]
            base_val = raw[base_idx]
            if raw[i] is not None and base_val not in (None, 0) and i != base_idx:
                ytdg[i] = (raw[i] / base_val - 1) * 100
        return yoy, ytdg

    ts["assets_yoy"], ts["assets_ytd_growth"] = yoy_and_ytd(assets_raw)
    ts["liab_yoy"], ts["liab_ytd_growth"] = yoy_and_ytd(liab_raw)
    ts["credit_yoy"], ts["credit_ytd_growth"] = yoy_and_ytd(credit_raw)
    return ts


def label_for(period_data):
    for v in period_data.values():
        if v.get("data_year") and v.get("data_month"):
            return f"{v['data_year']}-{v['data_month']:02d}"
    return None


def build_capital_payload(history_path: Path) -> dict:
    history = json.loads(history_path.read_text(encoding="utf-8"))
    all_periods = history.get("periods", {})
    period_labels = sorted(all_periods.keys())  # 'MMYYYY', сортируем ниже правильно
    period_labels = sorted(period_labels, key=lambda l: (int(l[2:]), int(l[:2])))

    labels = []
    kept = []
    for p in period_labels:
        lbl = label_for(all_periods[p])
        if lbl is None:
            continue
        labels.append(lbl)
        kept.append(p)

    result = {"periods": labels}
    result["sector"] = build_timeseries(kept, lambda p: sector_entry_for_period(all_periods[p]))
    result["banks"] = {}
    for regn in BANK_ORDER:
        result["banks"][str(regn)] = {
            "name": BANKS[regn],
            **build_timeseries(kept, lambda p, r=str(regn): all_periods[p].get(r)),
        }
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    payload = build_capital_payload(root / "data" / "capital_history.json")
    print("periods:", len(payload["periods"]))
    print("sector capital[-1]:", payload["sector"]["capital"][-1])
    print("sector n1_0[-1]:", payload["sector"]["n1_0"][-1])
