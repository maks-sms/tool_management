# shared/excel/csv_io.py
"""CSV импорт/экспорт склада (таблица tools). Без UI — только данные."""
import csv
import sqlite3
from datetime import datetime
from io import StringIO
from typing import Tuple, List, Dict, Any

from shared.config import get_db_path


# ─── Экспорт ────────────────────────────────────────────────────

def get_tools_for_csv_export(only_available: bool = False
                             ) -> Tuple[List[str], List[list]]:
    """Возвращает (headers, rows) для экспорта склада в CSV."""
    conn = sqlite3.connect(get_db_path(), timeout=10)
    cur = conn.cursor()
    if only_available:
        cur.execute("""SELECT inner_code, articul, type, diameter, length,
                              brand, analog, qty_total
                       FROM tools
                       WHERE qty_total > 0
                       ORDER BY inner_code""")
    else:
        cur.execute("""SELECT inner_code, articul, type, diameter, length,
                              brand, analog, qty_total
                       FROM tools
                       ORDER BY inner_code""")
    data = cur.fetchall()
    conn.close()

    headers = ['№', 'Код', 'Артикул инструмента', 'Остаток на складе',
               'Тип инструмента', 'Диаметр режущей части',
               'Общая длина (спр.)', 'Аналоги', 'Пр-ль*']
    rows = []
    for i, r in enumerate(data, start=1):
        code, art, t, d, l, b, a, q = r
        rows.append([i, code, art, q, t or '', d or '',
                     l or '', a or '', b or ''])
    return headers, rows


def export_tools_to_csv(file_path: str, only_available: bool = False) -> int:
    """Экспортирует склад в CSV (cp1251, разделитель ';'). Возвращает кол-во строк."""
    headers, rows = get_tools_for_csv_export(only_available)
    with open(file_path, 'w', encoding='cp1251', newline='') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)
    return len(rows)


# ─── Импорт ────────────────────────────────────────────────────

SUPPORTED_ENCODINGS = ['cp1251', 'utf-8', 'utf-8-sig', 'cp866', 'windows-1251']
DELIMITERS = [';', ',', '\t']
HEADER_KEYWORDS = ['код', 'артикул', 'тип', 'диаметр', 'длина',
                   'производитель', 'бренд', 'аналог', 'остаток']


def _read_file_auto(file_path: str) -> str:
    for enc in SUPPORTED_ENCODINGS:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                content = f.read()
            if content.startswith('\ufeff'):
                content = content[1:]
            return content
        except UnicodeDecodeError:
            continue
    raise RuntimeError('Не удалось определить кодировку файла')


def _detect_delimiter(content: str) -> str:
    first_line = content.split('\n', 1)[0]
    for delim in DELIMITERS:
        if first_line.count(delim) >= 2:
            return delim
    return ';'


def _has_header(row: List[str]) -> bool:
    for cell in row:
        low = str(cell).lower()
        if any(kw in low for kw in HEADER_KEYWORDS):
            return True
    return False


def _process_row(row: List[str], cur, result: Dict[str, int]) -> None:
    if not row or all((c or '').strip() == '' for c in row):
        result['skipped_empty'] += 1
        return
    try:
        inner_code = row[1].strip() if len(row) > 1 else ''
        articul = row[2].strip() if len(row) > 2 else ''

        if not inner_code or not articul:
            result['errors'] += 1
            return

        qty_str = row[3].strip() if len(row) > 3 else '0'
        try:
            qty = int(float(qty_str.replace(',', '.'))) if qty_str else 0
        except Exception:
            qty = 0

        tool_type = row[4].strip() if len(row) > 4 else ''
        diameter = row[5].strip() if len(row) > 5 else ''
        length = row[6].strip() if len(row) > 6 else ''
        analog = row[7].strip() if len(row) > 7 else ''
        brand = row[8].strip() if len(row) > 8 else ''

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        cur.execute('SELECT id FROM tools WHERE inner_code = ?', (inner_code,))
        existing = cur.fetchone()

        if existing:
            cur.execute("""UPDATE tools
                           SET articul=?, type=?, diameter=?, length=?,
                               brand=?, analog=?, qty_total=?, updated_at=?
                           WHERE inner_code=?""",
                        (articul, tool_type, diameter, length,
                         brand, analog, qty, now, inner_code))
            result['updated'] += 1
        else:
            cur.execute("""INSERT INTO tools
                           (inner_code, articul, type, diameter, length,
                            brand, analog, qty_total, created_at, updated_at)
                           VALUES (?,?,?,?,?,?,?,?,?,?)""",
                        (inner_code, articul, tool_type, diameter, length,
                         brand, analog, qty, now, now))
            result['imported'] += 1
    except Exception as e:
        result['errors'] += 1
        print(f'[csv import] ошибка: {e}')


def import_tools_from_csv(file_path: str) -> Dict[str, Any]:
    """Импорт склада из CSV. Возвращает {'imported','updated','errors','skipped_empty'}."""
    result = {'imported': 0, 'updated': 0, 'errors': 0, 'skipped_empty': 0}

    content = _read_file_auto(file_path)
    delimiter = _detect_delimiter(content)

    reader = csv.reader(StringIO(content), delimiter=delimiter)
    first = next(reader, [])
    if _has_header(first):
        data_rows = list(reader)
    else:
        data_rows = list(csv.reader(StringIO(content), delimiter=delimiter))

    conn = sqlite3.connect(get_db_path(), timeout=20)
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        cur = conn.cursor()
        for row in data_rows:
            _process_row(row, cur, result)
        conn.commit()
    finally:
        conn.close()

    return result