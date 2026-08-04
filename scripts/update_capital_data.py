"""
Обновление данных капитала/нормативов/структуры баланса (формы 101/123/135
+ прибыль из 102). Логика повторяет scripts/update_data.py (CIR):

1. По data/capital_state.json определяем следующий необработанный период.
2. Пробуем скачать архивы 101, 123, 135 за этот период (плюс 102 —
   для прибыли, тем же способом, что и в download_period.py/CIR).
3. Если период опубликован целиком — парсим, классифицируем счета,
   считаем капитал/нормативы/прибыль по каждому банку, дописываем в
   data/capital_history.json.
4. Пересобираем index.html (обе вкладки — CIR и капитал) через
   render_combined.py.

Период, отсутствующий на сайте ЦБ (404 хотя бы по одной из форм),
считается ещё не опубликованным — скрипт останавливается на нём,
это нормальная ситуация, не ошибка.
"""
import json
import shutil
from datetime import date
from pathlib import Path

from download_capital_forms import download_all_forms
from download_period import download_archive as download_102_archive, extract_archive as extract_102_archive
from dbf_parser import parse_p1
from compute_capital import build_period_entry

ROOT = Path(__file__).resolve().parent.parent
HISTORY_PATH = ROOT / "data" / "capital_history.json"
STATE_PATH = ROOT / "data" / "capital_state.json"
TMP_DIR = ROOT / "_tmp_capital_download"

MAX_PERIODS_PER_RUN = 3


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"last_period": "062026"}


def save_state(state: dict):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


def load_history() -> dict:
    if HISTORY_PATH.exists():
        return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    return {"periods": {}}


def save_history(history: dict):
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(history, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def next_period(label: str) -> str:
    mm = int(label[:2]); yyyy = int(label[2:])
    mm += 1
    if mm > 12:
        mm = 1; yyyy += 1
    return f"{mm:02d}{yyyy}"


def as_of_date_for(period_label: str) -> str:
    mm = int(period_label[:2]); yyyy = int(period_label[2:])
    mm += 1
    if mm > 12:
        mm = 1; yyyy += 1
    return f"{yyyy:04d}{mm:02d}01"


def process_one_period(period_label: str, history: dict) -> bool:
    as_of = as_of_date_for(period_label)
    dest = TMP_DIR / period_label

    files_by_form = download_all_forms(as_of, dest)
    if not files_by_form:
        return False

    # 102 (прибыль) — тем же способом, что update_data.py использует для CIR
    dest_102 = dest / "102"
    archive_102 = download_102_archive(as_of, dest_102)
    p1_data = {}
    if archive_102 is not None:
        files_102 = extract_102_archive(archive_102, dest_102)
        p1_target = next((f for f in files_102 if f.stem.upper().endswith("_P1")), None)
        if p1_target is not None:
            p1_data = parse_p1(str(p1_target))
    # прибыль не обязательна для публикации периода — если 102 ещё не вышел,
    # ROE/ROA для этого периода просто останутся пустыми до следующего запуска

    mm = int(period_label[:2]); yyyy = int(period_label[2:])
    period_entry = build_period_entry(
        files_by_form.get("101", []), files_by_form.get("123", []), files_by_form.get("135", []),
        p1_data, data_year=yyyy, data_month=mm, months_elapsed=mm,
    )
    history["periods"][period_label] = period_entry
    return True


def main():
    state = load_state()
    history = load_history()
    processed = []

    label = next_period(state["last_period"])
    for _ in range(MAX_PERIODS_PER_RUN):
        today = date.today()
        yyyy, mm = int(label[2:]), int(label[:2])
        if (yyyy, mm) > (today.year, today.month):
            break
        ok = process_one_period(label, history)
        if not ok:
            print(f"Период {label} пока не опубликован ЦБ (101/123/135) — останавливаюсь здесь.")
            break
        processed.append(label)
        state["last_period"] = label
        label = next_period(label)

    if processed:
        save_history(history)
        save_state(state)
        from render_combined import render
        out = render(ROOT / "index.html")
        print(f"Обновлены периоды (капитал): {processed}. Страница пересобрана: {out}")
    else:
        print("Новых периодов (капитал) не найдено, обновление не требуется.")

    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)


if __name__ == "__main__":
    main()
