"""
Собирает единый index.html из двух источников данных:
  - data/cir_history.json      -> вкладка "Расходы сектора (CIR)"
  - data/capital_history.json  -> вкладка "Капитал, ROE/ROA, структура баланса"
в шаблон scripts/report_template.html (уже содержит вёрстку и JS обеих
вкладок; на лету подставляются только сырые данные — payload'ы).

Вызывается из update_data.py (после обновления CIR) и из
update_capital_data.py (после обновления капитала) — какой бы из двух
пайплайнов ни отработал, страница пересобирается целиком из ТЕКУЩЕГО
состояния обеих историй, так что порядок вызовов не важен.
"""
import json
from pathlib import Path

from render_report import build_bank_series, build_sector_iso
from compute_cir import BANKS, BANK_ORDER
from render_capital import build_capital_payload

ROOT = Path(__file__).resolve().parent.parent


def build_cir_payload(history_path: Path) -> dict:
    history = json.loads(history_path.read_text(encoding="utf-8"))
    all_months, month_labels, cum, iso = build_bank_series(history)
    sector_iso = build_sector_iso(history)
    return {
        "sector_iso": sector_iso,
        "bank_order": BANK_ORDER,
        "names": {str(k): v for k, v in BANKS.items()},
        "month_labels": month_labels,
        "all_months": all_months,
        "cum": cum,
        "iso": iso,
    }


def render(output_path: Path,
           cir_history_path: Path = None,
           capital_history_path: Path = None,
           template_path: Path = None) -> Path:
    cir_history_path = cir_history_path or ROOT / "data" / "cir_history.json"
    capital_history_path = capital_history_path or ROOT / "data" / "capital_history.json"
    template_path = template_path or ROOT / "scripts" / "report_template.html"

    cir_payload = build_cir_payload(cir_history_path)
    capital_payload = build_capital_payload(capital_history_path)

    cir_json = json.dumps(cir_payload, ensure_ascii=False, separators=(",", ":"))
    capital_json = json.dumps(capital_payload, ensure_ascii=False, separators=(",", ":"))
    last_period = capital_payload["periods"][-1] if capital_payload["periods"] else ""

    template = template_path.read_text(encoding="utf-8")
    html = template.replace("__CIR_PAYLOAD_JSON__", cir_json)
    html = html.replace("__CAPITAL_PAYLOAD_JSON__", capital_json)
    html = html.replace("__LAST_PERIOD__", last_period)

    output_path.write_text(html, encoding="utf-8")
    return output_path


if __name__ == "__main__":
    out = render(ROOT / "index.html")
    print(f"Готово: {out}")
