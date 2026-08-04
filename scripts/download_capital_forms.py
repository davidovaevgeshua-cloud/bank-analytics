"""
Загрузка архивов форм 0409101, 0409123, 0409135 ЦБ РФ за один отчётный период.

Построено по образцу scripts/download_period.py (форма 102), с той же
логикой именования и той же оговоркой про дату в имени файла: архив
"{форма}-{ГГГГММ01}.rar" датирован 1-м числом месяца, СЛЕДУЮЩЕГО за
отчётным, и содержит данные ПО СОСТОЯНИЮ НА эту дату (т.е. закрытие
предыдущего месяца).

ВАЖНО: URL-шаблон для форм 101/123/135 выведен по аналогии с уже
подтверждённым шаблоном формы 102 (https://www.cbr.ru/vfs/credit/forms/
102-{as_of}.rar) и именами архивов, с которыми велась работа в анализе
(например, "123-20241101.rar" для формы 123). Это НЕ проверено вживую
из песочницы (cbr.ru заблокирован для исходящих запросов оттуда) —
первый прогон workflow в GitHub Actions должен это подтвердить. Если
403/404 будет на всех периодах подряд — сверьте точный URL вручную на
https://www.cbr.ru/banking_sector/otchetnost-kreditnykh-organizaciy/
и поправьте BASE_URL_TEMPLATE ниже.
"""
import subprocess
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BASE_URL_TEMPLATE = "https://www.cbr.ru/vfs/credit/forms/{form}-{as_of}.rar"
USER_AGENT = "Mozilla/5.0 (compatible; bank-analytics-bot/1.0)"

FORMS = ("101", "123", "135")


def url_for(form: str, as_of_date: str) -> str:
    return BASE_URL_TEMPLATE.format(form=form, as_of=as_of_date)


def download_archive(form: str, as_of_date: str, dest_dir: Path) -> Path | None:
    """
    Скачивает архив формы `form` за период as_of_date (YYYYMMDD).
    Возвращает путь к .rar либо None, если ЦБ ещё не опубликовал данные
    за этот период (404 — нормальная ситуация, не ошибка).
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    url = url_for(form, as_of_date)
    out_path = dest_dir / f"{form}-{as_of_date}.rar"
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
    """Распаковывает архив (unrar, затем 7z как запасной вариант)."""
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
    return sorted(dest_dir.glob("*.dbf")) + sorted(dest_dir.glob("*.DBF"))


def download_all_forms(as_of_date: str, dest_root: Path) -> dict:
    """
    Скачивает и распаковывает 101/123/135 за один период.
    Возвращает {form: [пути к dbf]} — только для форм, которые уже
    опубликованы. Если хотя бы одна из трёх форм не опубликована (404),
    возвращает пустой dict (период считается ещё не готовым целиком).
    """
    result = {}
    for form in FORMS:
        dest = dest_root / form
        archive = download_archive(form, as_of_date, dest)
        if archive is None:
            return {}
        result[form] = extract_archive(archive, dest)
    return result


if __name__ == "__main__":
    import sys
    as_of = sys.argv[1] if len(sys.argv) > 1 else "20260601"
    tmp = Path("./_cbr_capital_download") / as_of
    files = download_all_forms(as_of, tmp)
    if not files:
        print(f"Период {as_of} пока не опубликован полностью (101/123/135) — это нормально, ждём.")
    else:
        for form, fl in files.items():
            print(form, "->", [f.name for f in fl])
