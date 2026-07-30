"""
Расчёт CIR (Cost-to-Income Ratio) и ведение накопительной истории данных.

Хранилище: data/cir_history.json — по каждому периоду (метка "MMYYYY")
сохраняются "сырые" компоненты (ЧПД, чистые комиссии, АХР, млрд руб.)
как для 13 отслеживаемых банков, так и для сектора целиком (если файл
за этот период содержит полный сектор — все банки, а не только с
универсальной лицензией). Храним именно компоненты, а не готовый CIR,
чтобы можно было пересчитать очистку от накопления (де-кумуляцию) в
любой момент, не возвращаясь к исходным dbf.

Формула: CIR = АХР (символ 48000) / (ЧПД + чистый комиссионный доход)
ЧПД = симв. 11000 - 31000
Чистый комиссионный доход = (12000+27000) - (32000+33000)
Единицы в исходных dbf — тыс. руб.; здесь everything переводится в млрд.
"""
import json
from pathlib import Path

BANKS = {
    1481: "СБЕРБАНК РОССИИ", 1000: "ВТБ", 1326: "АЛЬФА-БАНК", 354: "ГАЗПРОМБАНК",
    2673: "ТБанк", 841: "ВАЙЛДБЕРРИЗ БАНК", 963: "СОВКОМБАНК", 2312: "БАНК ДОМ.РФ",
    3292: "РАЙФФАЙЗЕНБАНК", 3349: "РОССЕЛЬХОЗБАНК", 1978: "МОСКОВСКИЙ КРЕДИТНЫЙ БАНК",
    3027: "ЯНДЕКС БАНК", 3542: "ОЗОН БАНК",
}
BANK_ORDER = list(BANKS.keys())

# Периоды, за которые в архиве публикуется полный сектор (не только банки
# с универсальной лицензией) — обычно это концы кварталов. Список
# уточняется по факту: если в конкретном файле оказалось значительно
# больше банков, чем обычно (тест >250), период трактуется как квартальный.
SECTOR_BANK_COUNT_THRESHOLD = 250


def _get(rec: dict, code: str) -> float:
    return rec.get(code, 0) or 0


def _components_billion(rec: dict):
    chpd = (_get(rec, "11000") - _get(rec, "31000")) / 1e6
    comm_net = ((_get(rec, "12000") + _get(rec, "27000"))
                - (_get(rec, "32000") + _get(rec, "33000"))) / 1e6
    opex = _get(rec, "48000") / 1e6
    return {"chpd": chpd, "comm_net": comm_net, "opex": opex}


def cir_from_components(c: dict):
    denom = c["chpd"] + c["comm_net"]
    if denom == 0:
        return None
    return c["opex"] / denom * 100


def load_history(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"banks": {}, "sector": {}}


def save_history(history: dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, ensure_ascii=False, indent=1), encoding="utf-8")


def ingest_period(history: dict, period_label: str, p1_data: dict):
    """
    period_label: например '052026' (месяц+год отчётного периода,
    как называется _P1.dbf внутри архива ЦБ).
    p1_data: {regn (int): {code (str): value}} — результат dbf_parser.parse_p1.
    Дописывает период в history (сектор — если банков в файле много,
    банки — по 13 отслеживаемым, если они есть в файле).
    """
    n_banks_in_file = len(p1_data)

    # 13 банков: пишем компоненты, если банк присутствует в этом периоде
    for regn in BANK_ORDER:
        rec = p1_data.get(regn)
        if rec is None:
            continue
        comp = _components_billion(rec)
        history["banks"].setdefault(str(regn), {})[period_label] = comp

    # Сектор целиком: только если это похоже на полный квартальный файл
    if n_banks_in_file >= SECTOR_BANK_COUNT_THRESHOLD:
        agg = {}
        for rec in p1_data.values():
            for code, val in rec.items():
                agg[code] = agg.get(code, 0) + val
        history["sector"][period_label] = _components_billion(agg)

    return history


def isolate_series(cumulative_by_period: dict, ordered_period_keys: list, year_of):
    """
    Де-кумуляция: из значений "нарастающим итогом с начала года" получает
    значения за отдельный месяц/квартал. year_of(period_label) -> год (int),
    используется для определения сброса на январь/1-й квартал.
    Возвращает {period_label: {chpd, comm_net, opex, cir}} только для
    периодов, где изоляция была возможна (нет разрыва в предыдущем периоде).
    """
    result = {}
    prev = None
    prev_year = None
    for label in ordered_period_keys:
        cur = cumulative_by_period.get(label)
        year = year_of(label)
        if cur is None:
            prev = None
            prev_year = year
            continue
        if prev is None or prev_year != year:
            # первый период года — изоляция не нужна, значение уже "чистое"
            iso = dict(cur)
        else:
            iso = {
                "chpd": cur["chpd"] - prev["chpd"],
                "comm_net": cur["comm_net"] - prev["comm_net"],
                "opex": cur["opex"] - prev["opex"],
            }
        iso["cir"] = cir_from_components(iso)
        result[label] = iso
        prev = cur
        prev_year = year
    return result
