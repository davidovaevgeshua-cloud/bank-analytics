"""
Парсер dbf-файлов формы 101 ЦБ РФ (оборотная ведомость по счетам бухучёта).

Два типа файлов в архиве за период:
  - MMYYYYB1.dbf — обороты и остатки по счетам (REGN, PLAN, NUM_SC, A_P,
    VITG — входящий остаток за период, IITG — исходящий остаток за период,
    DT — отчётная дата, и др.). Читается обычной библиотекой dbfread без
    проблем — поле REGN в этом файле хранится нормально.
  - MMYYYYN1.dbf — справочник банков (REGN, NAME_B, PRIZ, PRIZ_P). В этом
    файле поле REGN физически хранится как ASCII-текст с null-паддингом
    (например b'1\\x00\\x00\\x00' для рег. номера 1), а не как обычное
    число — из-за этого dbfread падает с ошибкой
    "could not convert string to float". Поэтому для N1 используется
    свой минимальный бинарный парсер (см. read_n1 ниже).

Ключевая идея расчёта прибыли: счёт 706 "Финансовый результат текущего
года" — активно-пассивный, обнуляется 1 января. Для каждого банка счёт
может быть представлен двумя строками: с признаком A_P='2' (кредитовый
остаток = накопленные доходы) и A_P='1' (дебетовый остаток = накопленные
расходы). Чистый финансовый результат нарастающим итогом с начала года =
(сумма IITG по A_P='2') - (сумма IITG по A_P='1').
"""
from __future__ import annotations

import struct
from collections import Counter, defaultdict
from pathlib import Path

try:
    from dbfread import DBF
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Нужна библиотека dbfread: pip install dbfread"
    ) from exc


def read_n1(path: str | Path) -> dict[int, str]:
    """Читает справочник банков MMYYYYN1.dbf: REGN -> название банка.

    Свой парсер, а не dbfread — см. пояснение в шапке файла.
    Формат записи (после однобайтового флага удаления в начале):
        REGN    4 байта, ASCII-текст с null-паддингом (например b'1\\x00\\x00\\x00')
        NAME_B  90 байт, текст в кодировке cp866, с null/пробел-паддингом
    """
    path = Path(path)
    with open(path, "rb") as f:
        header = f.read(32)
        numrecs = struct.unpack("<I", header[4:8])[0]
        hlen = struct.unpack("<H", header[8:10])[0]
        reclen = struct.unpack("<H", header[10:12])[0]
        f.seek(hlen)
        data = f.read(reclen * numrecs)

    banks: dict[int, str] = {}
    for i in range(numrecs):
        rec = data[i * reclen : (i + 1) * reclen]
        regn_raw = rec[1:5].split(b"\x00")[0]
        if not regn_raw:
            continue
        regn = int(regn_raw)
        name = rec[5:95].decode("cp866", errors="replace").rstrip("\x00 ").strip()
        banks[regn] = name
    return banks


def main_date_of(records) -> str:
    """Определяет основную отчётную дату файла (дата, встречающаяся чаще
    всего в поле DT). В файле формы 101 подавляющее большинство записей
    относится к одной дате закрытия периода; редкие записи с другими
    датами — банки, чья последняя отчётность относится к более раннему
    периоду (например, в связи с отзывом лицензии), их отбрасываем.
    """
    dates = Counter(r["DT"] for r in records)
    return dates.most_common(1)[0][0].isoformat()


def read_account_706(b1_path: str | Path) -> dict[int, dict[str, float]]:
    """Читает MMYYYYB1.dbf и возвращает по каждому REGN накопленные с
    начала года суммы по счёту 706:
        {regn: {"credit_itogo": <кредит, накопленный доход>,
                "debit_itogo":  <дебет, накопленный расход>}}
    Суммы в исходных единицах файла (тыс. руб.).
    """
    b1_path = Path(b1_path)
    table = DBF(str(b1_path), encoding="cp866", ignore_missing_memofile=True)
    records = list(table)
    if not records:
        return {}
    main_date = main_date_of(records)

    result: dict[int, dict[str, float]] = defaultdict(
        lambda: {"credit_itogo": 0.0, "debit_itogo": 0.0}
    )
    for r in records:
        if r["NUM_SC"] != "706" or r["DT"].isoformat() != main_date:
            continue
        regn = r["REGN"]
        iitg = r["IITG"] or 0.0
        if r["A_P"] == "2":
            result[regn]["credit_itogo"] += iitg
        else:
            result[regn]["debit_itogo"] += iitg
    return dict(result)


def read_period(b1_path: str | Path, n1_path: str | Path) -> dict:
    """Полный разбор одного периода: имена банков + счёт 706 по каждому
    REGN. Возвращает структуру, готовую для сохранения в историю:
        {
          "regn": {
             "name": ...,
             "credit_itogo": ...,  # тыс. руб., накоплено с начала года
             "debit_itogo": ...,
          }, ...
        }
    """
    names = read_n1(n1_path)
    accounts = read_account_706(b1_path)
    out = {}
    for regn, vals in accounts.items():
        out[str(regn)] = {
            "name": names.get(regn, f"REGN {regn}"),
            "credit_itogo": vals["credit_itogo"],
            "debit_itogo": vals["debit_itogo"],
        }
    return out
