"""
Расчёт прибыли банков по форме 101 (счёт 706) и ведение накопительной
истории данных.

Хранилище: data/profit_history_101.json — по каждому периоду (метка
"MMYYYY", например "052026" = май 2026 г.) сохраняются "сырые"
компоненты счёта 706 (credit_itogo — накопленные с начала года доходы,
debit_itogo — накопленные с начала года расходы, тыс. руб.) как для 13
отслеживаемых банков, так и для сектора целиком. Храним именно
компоненты, а не готовую прибыль, чтобы можно было пересчитать
де-кумуляцию (выделение отдельного месяца) в любой момент, не
возвращаясь к исходным dbf.

Методология:
  - Счёт 706 "Финансовый результат текущего года" обнуляется 1 января.
  - Значение на дату закрытия периода — это накопленный с начала года
    итог (YTD) на эту дату.
  - Прибыль за отдельный месяц = YTD текущего периода минус YTD
    предыдущего календарного месяца (для января — само YTD-значение,
    т.к. это первый месяц года).
"""
from __future__ import annotations

import json
from pathlib import Path

from dbf_parser_101 import read_period, main_date_of
from dbfread import DBF

BANKS = {
    1481: "СБЕРБАНК РОССИИ",
    1000: "ВТБ",
    1326: "АЛЬФА-БАНК",
    354: "ГАЗПРОМБАНК",
    2673: "ТБанк",
    841: "ВАЙЛДБЕРРИЗ БАНК",
    963: "СОВКОМБАНК",
    2312: "БАНК ДОМ.РФ",
    3292: "РАЙФФАЙЗЕНБАНК",
    3349: "РОССЕЛЬХОЗБАНК",
    1978: "МОСКОВСКИЙ КРЕДИТНЫЙ БАНК",
    3027: "ЯНДЕКС БАНК",
    3542: "ОЗОН БАНК",
}
BANK_ORDER = list(BANKS.keys())


def load_history(path: str | Path) -> dict:
    path = Path(path)
    if not path.exists():
        return {"periods": {}}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_history(history: dict, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=1)


def period_label_to_date(period: str) -> str:
    """'052026' -> '2026-05' (для сортировки/отображения)."""
    mm, yyyy = period[:2], period[2:]
    return f"{yyyy}-{mm}"


def add_period(history: dict, period_label: str, b1_path: str | Path, n1_path: str | Path) -> None:
    """Разбирает один период и добавляет/обновляет запись в истории."""
    table = DBF(str(b1_path), encoding="cp866", ignore_missing_memofile=True)
    records = list(table)
    main_date = main_date_of(records) if records else None

    parsed = read_period(b1_path, n1_path)  # {regn_str: {name, credit_itogo, debit_itogo}}

    sector_credit = sum(v["credit_itogo"] for v in parsed.values())
    sector_debit = sum(v["debit_itogo"] for v in parsed.values())

    banks_out = {}
    for regn in BANK_ORDER:
        v = parsed.get(str(regn))
        if v is None:
            continue
        banks_out[str(regn)] = {
            "credit_itogo": v["credit_itogo"],
            "debit_itogo": v["debit_itogo"],
        }

    history.setdefault("periods", {})[period_label] = {
        "date": main_date,
        "n_banks": len(parsed),
        "sector": {"credit_itogo": sector_credit, "debit_itogo": sector_debit},
        "banks": banks_out,
    }


def _sorted_periods_for_year(history: dict, year: str) -> list[str]:
    periods = [p for p in history.get("periods", {}) if p[2:] == year]
    return sorted(periods, key=lambda p: int(p[:2]))


def net_ytd(component: dict) -> float:
    """credit_itogo - debit_itogo, млрд руб."""
    return (component["credit_itogo"] - component["debit_itogo"]) / 1e6


def build_series(history: dict, component_key: str | None = None, regn: int | None = None):
    """
    Строит по всей истории два ряда - YTD (накопленным итогом с начала
    года) и monthly (де-кумулированное значение за отдельный месяц) -
    для сектора (regn=None) либо для одного банка (regn=<REGN>).

    Возвращает список словарей вида:
        {"period": "052026", "label": "2026-05", "ytd": <млрд руб>, "monthly": <млрд руб или None>}
    Элементы отсортированы по календарной дате. "monthly" = None, если
    предыдущий календарный месяц отсутствует в истории (пробел в данных).
    """
    periods = history.get("periods", {})
    all_labels = sorted(periods.keys(), key=lambda p: (p[2:], int(p[:2])))

    out = []
    prev_ytd_by_year: dict[str, float | None] = {}
    prev_period_num_by_year: dict[str, int | None] = {}

    for p in all_labels:
        entry = periods[p]
        year = p[2:]
        month = int(p[:2])

        if regn is None:
            comp = entry["sector"]
        else:
            comp = entry.get("banks", {}).get(str(regn))
        if comp is None:
            continue

        ytd = net_ytd(comp)

        prev_num = prev_period_num_by_year.get(year)
        if month == 1:
            monthly = ytd
        elif prev_num == month - 1:
            monthly = ytd - prev_ytd_by_year[year]
        else:
            monthly = None  # пробел: предыдущего месяца нет в истории

        out.append(
            {
                "period": p,
                "label": period_label_to_date(p),
                "ytd": round(ytd, 3),
                "monthly": round(monthly, 3) if monthly is not None else None,
            }
        )
        prev_ytd_by_year[year] = ytd
        prev_period_num_by_year[year] = month

    return out
