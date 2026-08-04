"""
Главный скрипт обновления CIR. Логика не изменилась, поменялась только
финальная сборка страницы: раньше она вызывала render_report.render()
напрямую (только CIR), теперь — render_combined.render() (собирает
index.html из ОБОИХ источников: cir_history.json и capital_history.json),
чтобы вкладка "Капитал" на странице не затиралась, когда обновляется
только CIR.

1. По data/state.json определяем следующий период, который ещё
   не проверяли (следующий месяц после последнего, что есть в истории).
2. Пробуем скачать архив ЦБ за этот период (и, на случай если ЦБ уже
   опубликовал несколько периодов вперёд, — ещё пару следующих).
3. Если архив есть — распаковываем, парсим _P1.dbf и NP1.dbf,
   дописываем данные в data/cir_history.json.
4. Пересобираем index.html (обе вкладки).
5. Печатаем итог в stdout — это увидит лог GitHub Actions,
   а сам workflow закоммитит изменённые файлы, если они появились.

Период, отсутствующий на сайте ЦБ (404), — нормальная ситуация:
значит, отчётность за этот месяц ещё не вышла, скрипт просто
останавливается на первом таком периоде и завершается без ошибки.
"""
import json
import shutil
from datetime import date
from pathlib import Path

from dbf_parser import parse_p1
from download_period import download_archive, extract_archive
from compute_cir import load_history, save_history, ingest_period
from render_combined import render

ROOT = Path(__file__).resolve().parent.parent
HISTORY_PATH = ROOT / "data" / "cir_history.json"
STATE_PATH = ROOT / "data" / "state.json"
TMP_DIR = ROOT / "_tmp_download"

MAX_PERIODS_PER_RUN = 3  # на случай, если ЦБ выложил сразу несколько месяцев


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"last_period": "052026"}  # последний период, уже обработанный вручную


def save_state(state: dict):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


def next_period(label: str) -> str:
    """'052026' -> '062026', '122025' -> '012026'."""
    mm = int(label[:2])
    yyyy = int(label[2:])
    mm += 1
    if mm > 12:
        mm = 1
        yyyy += 1
    return f"{mm:02d}{yyyy}"


def as_of_date_for(period_label: str) -> str:
    """
    Архив ЦБ подписан датой '01' месяца, СЛЕДУЮЩЕГО за отчётным периодом
    (см. пояснение в download_period.py). period_label — MMYYYY.
    """
    mm = int(period_label[:2])
    yyyy = int(period_label[2:])
    mm += 1
    if mm > 12:
        mm = 1
        yyyy += 1
    return f"{yyyy:04d}{mm:02d}01"


def process_one_period(period_label: str, history: dict) -> bool:
    """Возвращает True, если период успешно скачан и обработан."""
    as_of = as_of_date_for(period_label)
    dest = TMP_DIR / period_label
    archive = download_archive(as_of, dest)
    if archive is None:
        return False
    files = extract_archive(archive, dest)
    p1_target = next((f for f in files if f.stem.upper().endswith("_P1")), None)
    if p1_target is None:
        raise RuntimeError(f"В архиве за {period_label} не нашёлся файл _P1.dbf: {[f.name for f in files]}")
    p1_data = parse_p1(str(p1_target))
    ingest_period(history, period_label, p1_data)
    return True


def main():
    state = load_state()
    history = load_history(HISTORY_PATH)
    processed = []

    label = next_period(state["last_period"])
    for _ in range(MAX_PERIODS_PER_RUN):
        # не пытаемся заглянуть в будущее дальше текущего календарного месяца
        today = date.today()
        yyyy, mm = int(label[2:]), int(label[:2])
        if (yyyy, mm) > (today.year, today.month):
            break
        ok = process_one_period(label, history)
        if not ok:
            print(f"Период {label} пока не опубликован ЦБ — останавливаюсь здесь.")
            break
        processed.append(label)
        state["last_period"] = label
        label = next_period(label)

    if processed:
        save_history(history, HISTORY_PATH)
        save_state(state)
        out = render(ROOT / "index.html")
        print(f"Обновлены периоды: {processed}. Страница пересобрана: {out}")
    else:
        print("Новых периодов не найдено, обновление не требуется.")

    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)


if __name__ == "__main__":
    main()
