"""
Классификация счетов первого порядка (форма 101, PLAN='А') по категориям
активов и пассивов. Построено на основе Плана счетов бухгалтерского учета
для кредитных организаций (Положение Банка России №579-П) и фактических
названий счетов из NAMES.dbf.
"""

ASSET_CATEGORIES = {
    "cash_liquid": "Деньги и ликвидные активы",
    "cbr_accounts": "Счета в ЦБ РФ",
    "interbank_loans": "Кредиты банкам",
    "credit_portfolio": "Кредитный портфель",
    "bonds": "Облигации",
    "shares": "Акции",
    "fixed_assets": "Основные средства и НМА",
    "other_assets": "Прочие активы",
}

LIABILITY_CATEGORIES = {
    "client_funds": "Средства клиентов",
    "bank_funds": "Средства банков",
    "cbr_loans": "Кредиты от ЦБ РФ",
    "subordinated": "Субординированные",
    "issued_securities": "Ценные бумаги",
    "other_liabilities": "Прочие обязательства",
}

CREDIT_PORTFOLIO_SUB = {
    "gov": "Гос структуры",
    "ip": "ИП",
    "overdue": "Просроченная задолженность",
    "corp_retail": "Юрлица + Физлица",  # объединено источником данных, см. примечание
}

EXCLUDE_CODES = {"303", "706", "707", "708", "ITGAP"}
EQUITY_CODES = {"102", "105", "106", "107", "108", "109", "111", "114"}  # капитал -- не пассив

def base_code(num_sc):
    """3-значный код счета первого порядка (без учёта суффикса .0/.1/.2)."""
    return num_sc.split('.')[0]

def classify_asset(num_sc):
    if num_sc in EXCLUDE_CODES:
        return None
    b = base_code(num_sc)
    if b in ("202", "203"):
        return "cash_liquid", None
    if b in ("301", "302", "304", "305", "306"):
        return "cash_liquid", None
    if b == "319":
        return "cbr_accounts", None
    if b in ("320", "321", "322", "323", "324", "325", "329"):
        return "interbank_loans", None
    # Кредитный портфель: раздел 44x-47x (кредиты/размещённые средства), включая
    # укрупнённый код "45.x" (счета 452+455, объединённые источником без разбивки
    # по типу заёмщика -- см. примечание в дашборде)
    if b in ("440", "441", "442", "443", "444", "445", "446", "447", "448", "449"):
        return "credit_portfolio", "gov"
    if b in ("450", "451", "453"):
        return "credit_portfolio", "corp_retail"
    if b == "454":
        return "credit_portfolio", "ip"
    if b in ("458", "459", "324", "325"):
        return "credit_portfolio", "overdue"
    if num_sc in ("45.0", "45.1", "45.2"):
        return "credit_portfolio", "corp_retail"
    if b in ("460", "464", "465", "466", "468", "469"):
        return "credit_portfolio", "gov"
    if b in ("470", "472", "477", "478"):
        return "credit_portfolio", "corp_retail"
    if b in ("474", "475", "476", "479"):
        return "other_assets", None
    if b in ("501", "502", "504", "505", "509", "512", "515"):
        return "bonds", None
    if b in ("506", "507"):
        return "shares", None
    if b in ("604", "608", "609", "610", "619", "620", "621"):
        return "fixed_assets", None
    return "other_assets", None

def classify_liability(num_sc):
    if num_sc in EXCLUDE_CODES or num_sc in EQUITY_CODES:
        return None
    b = base_code(num_sc)
    if b == "312":
        return "cbr_loans"
    if b in ("313", "314", "315", "316", "317", "318", "301", "302"):
        return "bank_funds"
    if num_sc in ("31.0", "31.1", "31.2"):
        return "bank_funds"
    if b in ("401", "402", "403", "404", "405", "406", "407", "408", "409"):
        return "client_funds"
    if b in ("410", "411", "412", "413", "414", "415", "416", "417", "418",
             "420", "421", "422", "423", "425", "426", "427", "428"):
        return "client_funds"
    if num_sc in ("42.0", "42.1", "42.2"):
        return "client_funds"
    if b == "496":
        return "subordinated"
    if b == "529":
        return "subordinated"
    if b in ("520", "521", "522", "523"):
        return "issued_securities"
    if b in ("324", "325", "329"):
        return "bank_funds"
    return "other_liabilities"

if __name__ == "__main__":
    from cbr_forms_parser import read_cbr_dbf
    fields, records = read_cbr_dbf("raw/101/20260601/052026B1.dbf")
    sber = [r for r in records if r['REGN'] == 1481 and r['PLAN'] == 'А']

    asset_tot = {k: 0.0 for k in ASSET_CATEGORIES}
    for r in sber:
        if r['A_P'] != '1':
            continue
        res = classify_asset(r['NUM_SC'])
        if res is None:
            continue
        cat, _ = res
        asset_tot[cat] += (r['IITG'] or 0)

    print("=== Sberbank 2026-06 assets by category (млрд руб) ===")
    total = 0
    for cat, name in ASSET_CATEGORIES.items():
        v = asset_tot[cat] / 1e6
        total += v
        print(f"{name:30s} {v:12,.1f}")
    print(f"{'ИТОГО':30s} {total:12,.1f}")

    liab_tot = {k: 0.0 for k in LIABILITY_CATEGORIES}
    for r in sber:
        if r['A_P'] != '2':
            continue
        cat = classify_liability(r['NUM_SC'])
        if cat is None:
            continue
        liab_tot[cat] += (r['IITG'] or 0)

    print()
    print("=== Sberbank 2026-06 liabilities by category (млрд руб) ===")
    totalp = 0
    for cat, name in LIABILITY_CATEGORIES.items():
        v = liab_tot[cat] / 1e6
        totalp += v
        print(f"{name:30s} {v:12,.1f}")
    print(f"{'ИТОГО':30s} {totalp:12,.1f}")

    print()
    print("Активы - Пассивы (должно ~= капитал 8724.9 млрд):", total - totalp)
