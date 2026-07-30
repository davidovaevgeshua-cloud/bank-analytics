"""
Универсальный парсер dbf-файлов формы 102 ЦБ РФ.

Зачем свой парсер, а не библиотека dbfread:
поле REGN в файлах NP1 (справочник банков) хранится как ASCII-текст
с null-паддингом, а не как число, из-за чего dbfread падает с ошибкой
преобразования типов. Здесь поля читаются как сырые байты и
интерпретируются вручную под каждый файл (_P1 — числовые символы
формы, NP1 — справочник REGN -> название банка).
"""
import struct


def read_dbf_raw(path):
    """Читает dbf-файл и возвращает (список полей, список сырых записей)."""
    with open(path, 'rb') as f:
        header = f.read(32)
        n_records = struct.unpack('<I', header[4:8])[0]
        header_size = struct.unpack('<H', header[8:10])[0]
        record_size = struct.unpack('<H', header[10:12])[0]
        n_fields = (header_size - 32 - 1) // 32
        fields = []
        for _ in range(n_fields):
            fdesc = f.read(32)
            name = fdesc[:11].split(b'\x00')[0].decode('cp866')
            ftype = chr(fdesc[11])
            flen = fdesc[16]
            fields.append((name, ftype, flen))
        f.seek(header_size)
        records = []
        for _ in range(n_records):
            rec = f.read(record_size)
            if not rec or rec[0:1] == b'*':  # помечена как удалённая
                continue
            row = {}
            pos = 1
            for name, ftype, flen in fields:
                row[name] = rec[pos:pos + flen]
                pos += flen
            records.append(row)
        return fields, records


def parse_p1(path):
    """
    Форма 102, файл _P1.dbf: числовые показатели по каждому банку.
    Возвращает {regn (int): {code (str): value (float)}}.
    """
    import dbfread
    table = dbfread.DBF(path, encoding='cp866', load=False)
    out = {}
    for r in table:
        regn = r['REGN']
        code = r['CODE'].strip()
        val = r['SIM_ITOGO']
        if val is None:
            continue
        out.setdefault(regn, {})[code] = val
    return out


def parse_np1(path):
    """
    Форма 102, файл NP1.dbf: справочник REGN -> название банка.
    Возвращает {regn (int): name (str)}.
    """
    fields, records = read_dbf_raw(path)
    out = {}
    for r in records:
        regn_raw = r['REGN']
        regn_str = regn_raw.split(b'\x00')[0].decode('ascii', errors='ignore').strip()
        if not regn_str:
            continue
        try:
            regn = int(regn_str)
        except ValueError:
            continue
        name_raw = r['NAME_B']
        name = name_raw.split(b'\x00')[0].decode('cp866', errors='ignore').strip()
        out[regn] = name
    return out
