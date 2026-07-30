"""
Сборка HTML-страницы отчёта по прибыли (форма 101) в формате "сравнение
по годам" — том же стиле, что понравившаяся страница banks_profit_yoy.html
из чата: по горизонтали — месяцы (янв..дек), отдельная линия/столбец на
каждый год, карточки с сравнением год к году.

В отличие от одноразовой страницы из чата, здесь набор лет не
захардкожен, а определяется автоматически по тому, что реально есть в
data/profit_history_101.json — так страница продолжит работать и когда
появятся данные за 2027 год и далее.

Использование:
    python render_report_101.py [history.json] [template.html] [out.html]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from compute_profit_101 import (
    load_history,
    build_series,
    pivot_by_year,
    MONTH_NAMES_RU,
    BANK_ORDER,
    BANKS,
)

HERE = Path(__file__).parent


def _card_metrics(pivot: dict) -> dict:
    """
    Считает данные для карточек сверху: последний доступный месяц (и его
    же месяц год назад, если есть), YTD на последний месяц (и YTD на тот
    же месяц год назад), последний полный год (если есть Dec) и
    предыдущий полный год.
    """
    years = pivot["years"]
    if not years:
        return {}

    # последний год и последний доступный месяц в нём
    last_year = years[-1]
    last_month_idx = max(
        (i for i, v in enumerate(pivot["monthly"][last_year]) if v is not None),
        default=None,
    )
    if last_month_idx is None and len(years) > 1:
        last_year = years[-2]
        last_month_idx = max(
            (i for i, v in enumerate(pivot["monthly"][last_year]) if v is not None),
            default=None,
        )
    if last_month_idx is None:
        return {}

    prev_year = str(int(last_year) - 1)
    last_monthly = pivot["monthly"][last_year][last_month_idx]
    prev_monthly = pivot["monthly"].get(prev_year, [None] * 12)[last_month_idx]
    last_ytd = pivot["ytd"][last_year][last_month_idx]
    prev_ytd = pivot["ytd"].get(prev_year, [None] * 12)[last_month_idx]

    # последний полный год (декабрь заполнен) и предыдущий полный год
    full_years = [y for y in years if pivot["ytd"][y][11] is not None]
    last_full_year = full_years[-1] if full_years else None
    prev_full_year = str(int(last_full_year) - 1) if last_full_year else None
    last_full_val = pivot["ytd"][last_full_year][11] if last_full_year else None
    prev_full_val = (
        pivot["ytd"].get(prev_full_year, [None] * 12)[11] if prev_full_year else None
    )

    return {
        "last_year": last_year,
        "last_month_idx": last_month_idx,
        "last_month_label": MONTH_NAMES_RU[last_month_idx],
        "last_monthly": last_monthly,
        "prev_monthly": prev_monthly,
        "last_ytd": last_ytd,
        "prev_ytd": prev_ytd,
        "last_full_year": last_full_year,
        "last_full_val": last_full_val,
        "prev_full_year": prev_full_year,
        "prev_full_val": prev_full_val,
    }


def build_page_data(history: dict) -> dict:
    sector_series = build_series(history, regn=None)
    sector_pivot = pivot_by_year(sector_series)
    sector_cards = _card_metrics(sector_pivot)

    banks_out = {}
    for regn in BANK_ORDER:
        series = build_series(history, regn=regn)
        if not series:
            continue
        pivot = pivot_by_year(series)
        banks_out[str(regn)] = {
            "name": BANKS[regn],
            "years": pivot["years"],
            "monthly": pivot["monthly"],
            "ytd": pivot["ytd"],
            "cards": _card_metrics(pivot),
        }

    return {
        "month_names": MONTH_NAMES_RU,
        "sector": {
            "years": sector_pivot["years"],
            "monthly": sector_pivot["monthly"],
            "ytd": sector_pivot["ytd"],
            "cards": sector_cards,
        },
        "bank_order": BANK_ORDER,
        "banks": banks_out,
    }


def render(history_path: str | Path, template_path: str | Path, out_path: str | Path) -> Path:
    history = load_history(history_path)
    data = build_page_data(history)

    template = Path(template_path).read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False)
    html = template.replace("__PROFIT_DATA_JSON__", payload)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return out_path


if __name__ == "__main__":
    history_path = sys.argv[1] if len(sys.argv) > 1 else HERE / ".." / "data" / "profit_history_101.json"
    template_path = sys.argv[2] if len(sys.argv) > 2 else HERE / "report_template_101.html"
    out_path = sys.argv[3] if len(sys.argv) > 3 else HERE / ".." / "form101" / "index.html"
    result = render(history_path, template_path, out_path)
    print(f"Страница пересобрана: {result}")
