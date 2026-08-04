"""
Универсальный "сырой" парсер dbf-файлов ЦБ РФ для форм 0409101, 0409123, 0409135.

Зачем свой парсер, а не dbfread: ЦБ дополняет текстовые (C) и числовые (N)
поля справа null-байтами, а не пробелами, из-за чего dbfread падает с
ValueError при попытке привести число к типу. Здесь заголовок и записи
читаются вручную через struct, поля декодируются как cp866-текст с
обрезкой null-байтов и (для чисел) конвертируются в float/int сами.

Используется вместе с scripts/dbf_parser.py (тот — для формы 102, чей
_P1.dbf успешно читается штатным dbfread; NP1.dbf в форме 102 обрабатывается
отдельной функцией read_dbf_raw в dbf_parser.py). Этот модуль — для форм
101/123/135, у которых все нужные поля (REGN, NUM_SC, C1, C1_3 и т.д.)
текстовые и требуют именно null-padding-безопасного чтения.
"""
import struct


def read_cbr_dbf(path, encoding='cp866'):
    with open(path, 'rb') as f:
        data = f.read()
    header_len = struct.unpack('<H', data[8:10])[0]
    record_len = struct.unpack('<H', data[10:12])[0]
    n_records = struct.unpack('<I', data[4:8])[0]
    fields = []
    pos = 32
    while data[pos:pos + 1] != b'\r':
        fdesc = data[pos:pos + 32]
        name = fdesc[0:11].split(b'\x00')[0].decode('ascii')
        ftype = fdesc[11:12].decode('ascii')
        flen = fdesc[16]
        fdec = fdesc[17]
        fields.append((name, ftype, flen, fdec))
        pos += 32
    assert pos + 1 == header_len, (pos + 1, header_len)

    records = []
    for i in range(n_records):
        rec_start = header_len + i * record_len
        rec = data[rec_start:rec_start + record_len]
        if rec[0:1] == b'*':
            continue  # запись помечена как удалённая
        row = {}
        p = 1
        for name, ftype, flen, fdec in fields:
            raw = rec[p:p + flen]
            p += flen
            if ftype in ('C', 'D'):
                val = raw.split(b'\x00')[0].rstrip(b' ').decode(encoding, errors='replace')
                row[name] = val
            elif ftype == 'N':
                txt = raw.split(b'\x00')[0].strip().decode('ascii', errors='replace')
                if txt in ('', '-'):
                    row[name] = None
                else:
                    try:
                        row[name] = float(txt) if ('.' in txt or fdec > 0) else int(txt)
                    except ValueError:
                        row[name] = txt
            else:
                row[name] = raw
        records.append(row)
    return fields, records


if __name__ == "__main__":
    import sys
    fields, records = read_cbr_dbf(sys.argv[1])
    print("fields:", fields)
    print("n records:", len(records))
    for r in records[:5]:
        print(r)
