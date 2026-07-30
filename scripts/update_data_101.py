"""
Главный скрипт обновления отчёта по прибыли (форма 101).

Что делает:
  1. Смотрит data/state_101.json — какой период обработан последним.
  2. Пробует скачать с сайта ЦБ следующие периоды один за другим (пока
     ЦБ не ответит 404 — значит, дальше данных пока нет, это нормально).
  3. Для каждого нового периода: распаковывает архив, парсит B1/N1,
     дописывает "сырые" компоненты счёта 706 в data/profit_history_101.json.
  4. Пересобирает form101/index.html из обновлённой истории.
  5. Сохраняет новое состояние (последний обработанный период).

Запуск вручную: python scripts/update_data_101.py
Этот же скрипт запускает .github/workflows/update_101.yml по расписанию.
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from download_period_101 import download_archive, extract_archive
from compute_profit_101 import load_history, save_history, add_period
from render_report_101 import render

ROOT = Path(__file__).parent.parent
HISTORY_PATH = ROOT / "data" / "profit_history_101.json"
STATE_PATH = ROOT / "data" / "state_101.json"
TEMPLATE_PATH = ROOT / "scripts" / "report_template_101.html"
OUT_HTML = ROOT / "form101" / "index.html"
TMP_DIR = ROOT / "_cbr_tmp_101"


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"last_period": None}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


def next_period(label: str) -> str:
    """'052026' -> '062026'; '122026' -> '012027'."""
    mm, yyyy = int(label[:2]), int(label[2:])
    if mm == 12:
        return f"01{yyyy + 1}"
    return f"{mm + 1:02d}{yyyy}"


def period_to_archive_date(label: str) -> str:
    """'052026' (май 2026) -> '20260601' — архив датируется 1-м числом
    месяца, СЛЕДУЮЩЕГО за отчётным."""
    mm, yyyy = int(label[:2]), int(label[2:])
    if mm == 12:
        return f"{yyyy + 1}0101"
    return f"{yyyy}{mm + 1:02d}01"


def main() -> None:
    history = load_history(HISTORY_PATH)
    state = load_state()

    if state.get("last_period"):
        label = next_period(state["last_period"])
    else:
        # если история пустая и state не задан — начинаем с текущего месяца
        today = date.today()
        label = f"{today.month:02d}{today.year}"

    processed = []
    max_iterations = 24  # защита от бесконечного цикла
    for _ in range(max_iterations):
        archive_date = period_to_archive_date(label)
        tmp = TMP_DIR / label
        archive = download_archive(archive_date, tmp)
        if archive is None:
            break  # ЦБ ещё не опубликовал этот период — нормальная остановка

        files = extract_archive(archive, tmp)
        b1 = next((f for f in files if f.name.upper().endswith("B1.DBF")), None)
        n1 = next((f for f in files if f.name.upper().endswith("N1.DBF")), None)
        if not b1 or not n1:
            print(f"Период {label}: в архиве не нашлись B1/N1 файлы, пропускаю.")
            break

        add_period(history, label, b1, n1)
        processed.append(label)
        state["last_period"] = label
        label = next_period(label)

    if processed:
        save_history(history, HISTORY_PATH)
        save_state(state)
        out = render(HISTORY_PATH, TEMPLATE_PATH, OUT_HTML)
        print(f"Обновлены периоды: {processed}. Страница пересобрана: {out}")
    else:
        print("Новых периодов не найдено, обновление не требуется.")

    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)


if __name__ == "__main__":
    main()
