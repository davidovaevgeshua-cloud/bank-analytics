"""
Сборка index.html из накопленной истории data/cir_history.json.

Логика полностью повторяет то, что уже проверено вручную в аналитике:
- раздел 1: CIR сектора по кварталам, очищенный от накопления
  (изоляция кварталов друг от друга);
- раздел 2: CIR по выбранному банку помесячно, тоже очищенный от
  накопления, с текстовым выводом о драйвере динамики за последний месяц;
- раздел 3: CIR по всем 13 банкам помесячно нарастающим итогом на одном
  графике.
Комментарии-выводы (за счёт чего изменился CIR) считаются в браузере
на лету (JS в шаблоне) — здесь только готовятся сырые данные.
"""
import json
import re
from pathlib import Path

from compute_cir import BANKS, BANK_ORDER, cir_from_components

MONTHS_RU = ["янв", "фев", "мар", "апр", "май", "июн",
             "июл", "авг", "сен", "окт", "ноя", "дек"]


def _is_month_period(label: str) -> bool:
    """Отсекает служебные метки вроде '42024' (только квартал сектора)."""
    return len(label) == 6 and label.isdigit()


def _month_year(label: str):
    mm = int(label[:2])
    yyyy = int(label[2:])
    return yyyy, mm


def _period_label_ru(label: str) -> str:
    yyyy, mm = _month_year(label)
    return f"{MONTHS_RU[mm - 1]} {yyyy}"


def build_bank_series(history: dict):
    """Строит месячный ряд (only чистые 'MMYYYY' метки) — cum и iso — по 13 банкам."""
    all_labels = set()
    for regn in BANK_ORDER:
        all_labels |= {l for l in history["banks"].get(str(regn), {}) if _is_month_period(l)}
    all_months = sorted(all_labels, key=_month_year)
    month_labels = [_period_label_ru(l) for l in all_months]

    cum = {}
    iso = {}
    for regn in BANK_ORDER:
        series = history["banks"].get(str(regn), {})
        cum_regn = {}
        for m in all_months:
            v = series.get(m)
            if v is None:
                cum_regn[m] = None
            else:
                v = dict(v)
                v["cir"] = cir_from_components(v)
                cum_regn[m] = v
        cum[str(regn)] = cum_regn
        # де-кумуляция, сброс на январе
        bank_iso = {}
        prev = None
        prev_year = None
        for m in all_months:
            cur = series.get(m)
            year, _ = _month_year(m)
            if cur is None:
                prev = None
                prev_year = year
                bank_iso[m] = None
                continue
            if prev is None or prev_year != year:
                comp = dict(cur)
            else:
                comp = {
                    "chpd": cur["chpd"] - prev["chpd"],
                    "comm_net": cur["comm_net"] - prev["comm_net"],
                    "opex": cur["opex"] - prev["opex"],
                }
            comp["cir"] = cir_from_components(comp)
            bank_iso[m] = comp
            prev = cur
            prev_year = year
        iso[str(regn)] = bank_iso

    return all_months, month_labels, cum, iso


def build_sector_iso(history: dict):
    """Изолирует кварталы сектора друг от друга (сброс на первом периоде года)."""
    sector = history.get("sector", {})
    labels = sorted(
        (l for l in sector if _is_month_period(l) or (len(l) == 5 and l.isdigit())),
        key=lambda l: (int(l[-4:]), int(l[:-4]) if len(l) == 5 else int(l[:2]))
    )

    def q_label(l):
        if len(l) == 5:  # спец.-метка вида '42024' = квартал 4, год 2024
            q, y = int(l[0]), int(l[1:])
        else:
            y, mm = _month_year(l)
            q = (mm - 1) // 3 + 1
        return f"Q{q} {y}"

    def year_of(l):
        return int(l[-4:])

    result = []
    prev = None
    prev_year = None
    for l in labels:
        cur = sector[l]
        year = year_of(l)
        month_of_this = ((int(l[0]) - 1) * 3 + 1) if len(l) == 5 else _month_year(l)[1]
        is_first_quarter = month_of_this <= 3
        if prev is not None and prev_year == year:
            comp = {
                "chpd": cur["chpd"] - prev["chpd"],
                "comm_net": cur["comm_net"] - prev["comm_net"],
                "opex": cur["opex"] - prev["opex"],
            }
        elif is_first_quarter:
            comp = dict(cur)
        else:
            # квартал не первый в году, а предыдущего квартала того же года
            # нет в данных — изолировать нельзя, пропускаем период целиком
            prev = cur
            prev_year = year
            continue
        comp["cir"] = cir_from_components(comp)
        comp["label"] = q_label(l)
        result.append(comp)
        prev = cur
        prev_year = year
    return result


def render(history_path: Path, template_path: Path, output_path: Path):
    history = json.loads(history_path.read_text(encoding="utf-8"))
    all_months, month_labels, cum, iso = build_bank_series(history)
    sector_iso = build_sector_iso(history)

    payload = {
        "sector_iso": sector_iso,
        "bank_order": BANK_ORDER,
        "names": {str(k): v for k, v in BANKS.items()},
        "month_labels": month_labels,
        "all_months": all_months,
        "cum": cum,
        "iso": iso,
    }
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    template = template_path.read_text(encoding="utf-8")
    html = template.replace("__PAYLOAD_JSON__", payload_json)
    output_path.write_text(html, encoding="utf-8")
    return output_path


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    out = render(
        history_path=root / "data" / "cir_history.json",
        template_path=root / "scripts" / "report_template.html",
        output_path=root / "index.html",
    )
    print(f"Готово: {out}")
