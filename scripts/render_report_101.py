"""
Сборка HTML-страницы отчёта по прибыли банковского сектора (форма 101,
счёт 706) из накопительной истории data/profit_history_101.json.

Использование:
    python render_report_101.py [history.json] [template.html] [out.html]
По умолчанию пути берутся относительно расположения этого файла:
    ../data/profit_history_101.json
    report_template_101.html
    ../form101/index.html
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from compute_profit_101 import load_history, build_series, BANK_ORDER, BANKS

HERE = Path(__file__).parent


def build_page_data(history: dict) -> dict:
    sector_series = build_series(history, regn=None)

    banks_out = {}
    for regn in BANK_ORDER:
        series = build_series(history, regn=regn)
        if not series:
            continue
        banks_out[str(regn)] = {"name": BANKS[regn], "series": series}

    all_labels = sorted(
        history.get("periods", {}).keys(), key=lambda p: (p[2:], int(p[:2]))
    )
    last_period = all_labels[-1] if all_labels else None

    return {
        "generated_note": "Данные обновляются автоматически по мере публикации ЦБ",
        "last_period": last_period,
        "sector": sector_series,
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
