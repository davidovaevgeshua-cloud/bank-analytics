"""
Загрузка архива формы 102 ЦБ РФ за один отчётный период.

Источник и формат ссылок подтверждены на странице:
https://www.cbr.ru/banking_sector/otchetnost-kreditnykh-organizaciy/
Пример ссылки: https://www.cbr.ru/vfs/credit/forms/102-20260501.rar

Важно про дату в имени файла: ЦБ подписывает архив датой "по состоянию
на 01.ММ.ГГГГ" — это первое число месяца, СЛЕДУЮЩЕГО за отчётным,
т.е. 102-20260501.rar содержит данные нарастающим итогом за январь-апрель
2026 г. (закрытые на 30 апреля). Даты внутри архива (имена dbf-файлов)
самодостаточны и подтверждают точный период — код ориентируется на них,
а не на дату в имени архива.

Для распаковки .rar нужен установленный в системе unrar или 7z
(в GitHub Actions на ubuntu-latest их нужно поставить отдельным шагом,
см. .github/workflows/update_cir.yml).
"""
import subprocess
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BASE_URL = "https://www.cbr.ru/vfs/credit/forms/102-{as_of}.rar"
USER_AGENT = "Mozilla/5.0 (compatible; bank-analytics-bot/1.0)"


def url_for(as_of_date: str) -> str:
    """as_of_date в формате YYYYMMDD, например '20260501'."""
    return BASE_URL.format(as_of=as_of_date)


def download_archive(as_of_date: str, dest_dir: Path) -> Path | None:
    """
    Скачивает архив за период as_of_date. Возвращает путь к .rar,
    либо None, если ЦБ ещё не опубликовал данные за этот период
    (сервер отвечает 404 — это нормальная ситуация, не ошибка).
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    url = url_for(as_of_date)
    out_path = dest_dir / f"102-{as_of_date}.rar"
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=60) as resp, open(out_path, "wb") as f:
            f.write(resp.read())
    except HTTPError as e:
        if e.code == 404:
            return None
        raise
    return out_path


def extract_archive(archive_path: Path, dest_dir: Path) -> list[Path]:
    """
    Распаковывает архив, возвращает список путей к извлечённым dbf-файлам
    (_P1.dbf, NP1.dbf, SP1.dbf). Пробует unrar, затем 7z как запасной вариант.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    tried = []
    for cmd in (["unrar", "x", "-o+", str(archive_path), str(dest_dir) + "/"],
                ["7z", "x", f"-o{dest_dir}", "-y", str(archive_path)]):
        tried.append(cmd[0])
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            break
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
    else:
        raise RuntimeError(
            f"Не удалось распаковать {archive_path}: не найден ни один из {tried}. "
            "Установите unrar (apt-get install unrar) или p7zip-full."
        )
    return sorted(dest_dir.glob("*.dbf"))


if __name__ == "__main__":
    # ручная проверка: python download_period.py 20260501
    as_of = sys.argv[1] if len(sys.argv) > 1 else "20260501"
    tmp = Path("./_cbr_download") / as_of
    archive = download_archive(as_of, tmp)
    if archive is None:
        print(f"Период {as_of} пока не опубликован (404) — это нормально, ждём.")
    else:
        print(f"Скачано: {archive}")
        files = extract_archive(archive, tmp)
        print("Извлечено:", [f.name for f in files])
