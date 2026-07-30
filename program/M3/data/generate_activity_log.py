"""Генератор большой неиндексированной фактовой таблицы `activity_log`
для умения A4 (оптимизация запроса). Детерминирован (SEED ниже).

Файл-результат в репозиторий не коммитится (после генерации — десятки
мегабайт, при N=4 800 000 около 4.8 млн строк; правило I1 части 1
blueprint запрещает файлы >50 МБ в git). Скрипт создаёт таблицу внутри
уже существующей базы m3.db (той же, что `schema.sql`/`seed.sql`) —
запускается один раз, после установки схемы и обоих seed-файлов
модуля (`seed.sql`, `retention_seed.sql`).

Запуск:
    python program/M3/data/generate_activity_log.py m3.db
    python program/M3/data/generate_activity_log.py m3.db 9600000  # больше строк
    python program/M3/data/generate_activity_log.py --help

Второй аргумент (необязательный) — число строк, по умолчанию 4 800 000
(см. `step-08.md`, 1.5: если замер без индекса на вашей машине быстрее
3 с, порог не проверяет ничего — увеличьте это число, например вдвое, и
перегенерируйте). sha256 первых `CHECK_ROWS` строк не зависит от
общего числа строк — **но только пока строки пишутся одним
последовательным циклом `for i in range(1, N+1)` без перемешивания и
без вычисления чего-либо (включая `event_date`) из общего числа строк
`n_rows_target`.** Если это когда-нибудь изменится (перемешивание
порядка вставки, дата, зависящая от `N`, разбиение на батчи с
собственным состоянием ГПСЧ на батч и т.п.) — инвариант «хэш не
зависит от N» ломается молча, и это нужно проверить заново, а не
считать гарантией навсегда. При `n_rows_target < CHECK_ROWS`
контрольная точка не определена — см. поведение в `main()`.
"""
from __future__ import annotations

import argparse
import hashlib
import random
import sqlite3
import sys
from pathlib import Path

if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

SEED = 20260804
N_ROWS = 4_800_000
EVENT_TYPES = ["page_view", "page_view", "page_view", "login", "add_to_cart"]
CHECK_ROWS = 1000  # сколько первых строк хэшировать для контрольной точки


def main() -> None:
    # argparse, а не ручной разбор sys.argv: ручной разбор трактовал
    # --help как путь к базе (sqlite3.connect создаёт файл с таким именем
    # вместо того, чтобы показать справку) — реальная находка при ревью,
    # не гипотетическая. argparse даёт --help бесплатно и корректно.
    ap = argparse.ArgumentParser(
        description="Создаёт таблицу activity_log (умение A4, m3.db уже должна "
                     "содержать schema.sql + seed.sql + retention_seed.sql)."
    )
    ap.add_argument("db_path", help="путь к m3.db (файл должен уже существовать)")
    ap.add_argument(
        "n_rows", nargs="?", type=int, default=N_ROWS,
        help=f"число строк activity_log (по умолчанию {N_ROWS})",
    )
    args = ap.parse_args()

    db_path = Path(args.db_path)
    # Проверка ДО подключения: sqlite3.connect создаёт пустой файл по
    # несуществующему пути молча — на голом --help или на опечатке в
    # пути это оставляет мусорный файл вместо понятной ошибки.
    if not db_path.exists():
        print(
            f"Файл базы {db_path} не найден. Сначала создайте его и "
            f"загрузите схему: sqlite3 {db_path} \".read schema.sql\", "
            f"затем \".read seed.sql\" и \".read retention_seed.sql\"."
        )
        raise SystemExit(1)

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    # Таблицы нет вовсе (schema.sql не загружен) — не то же самое, что
    # таблица есть, но пуста (seed.sql не загружен): разные причины,
    # разное сообщение. Первое — самая частая ошибка порядка запуска.
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='customers'")
    if cur.fetchone() is None:
        print(
            f"В {db_path} нет таблицы customers — schema.sql ещё не "
            f"загружен. Сначала: sqlite3 {db_path} \".read schema.sql\"."
        )
        conn.close()
        raise SystemExit(1)

    # ORDER BY обязателен: без него порядок строк, который вернёт SQLite,
    # не гарантирован спецификацией (на практике совпадает с rowid, но
    # генератор должен быть детерминирован по определению, а не "почти
    # всегда" — random.choice(customer_ids) использует этот список по
    # порядку, и другой порядок даёт другую последовательность событий).
    cur.execute("SELECT customer_id FROM customers ORDER BY customer_id")
    customer_ids = [row[0] for row in cur.fetchall()]
    if not customer_ids:
        print(
            f"Таблица customers в {db_path} есть, но пуста — seed.sql (и, "
            f"для полного набора клиентов, retention_seed.sql) ещё не "
            f"загружены: sqlite3 {db_path} \".read seed.sql\"."
        )
        conn.close()
        raise SystemExit(1)

    n_rows_target = args.n_rows

    cur.execute("DROP TABLE IF EXISTS activity_log")
    cur.execute(
        """
        CREATE TABLE activity_log (
            log_id      INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            event_type  TEXT NOT NULL,
            event_date  TEXT NOT NULL
        )
        """
    )

    random.seed(SEED)

    def rows():
        for i in range(1, n_rows_target + 1):
            cust = random.choice(customer_ids)
            et = random.choice(EVENT_TYPES)
            day = random.randint(1, 365)
            month = 1 + ((day - 1) // 30) % 12
            dom = 1 + (day - 1) % 28
            yield (i, cust, et, f"2025-{month:02d}-{dom:02d}")

    cur.executemany(
        "INSERT INTO activity_log (log_id, customer_id, event_type, event_date) VALUES (?,?,?,?)",
        rows(),
    )
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM activity_log")
    n_rows = cur.fetchone()[0]

    print(f"activity_log: {n_rows} строк, без индекса на customer_id (сделано намеренно, умение A4)")

    # Контрольная точка (правило раздела 1.3 curriculum-design для
    # локально генерируемых, не коммитящихся датасетов): сверяется до
    # решения задач шага, а не после первого непонятного результата.
    # Граничный случай: меньше CHECK_ROWS строк в таблице — контрольная
    # точка не определена (хэш "первых 1000 строк" от неполного набора
    # был бы не тем, с чем сравнивает reference_answers.md, и тихое
    # несовпадение выглядело бы как повреждённые данные, а не как
    # маленький прогон) — явное сообщение вместо падения или обмана.
    if n_rows < CHECK_ROWS:
        print(
            f"Строк меньше {CHECK_ROWS} — контрольная точка (sha256 первых "
            f"{CHECK_ROWS} строк) не определена, сравнение с "
            f"reference_answers.md невозможно. Для step-08.md нужен объём "
            f"порядка миллионов строк — если {n_rows} строк получены "
            f"намеренно (например, для отладки самого генератора), это "
            f"ожидаемо; если нет — проверьте аргумент числа строк."
        )
    else:
        cur.execute(
            f"SELECT log_id, customer_id, event_type, event_date "
            f"FROM activity_log ORDER BY log_id LIMIT {CHECK_ROWS}"
        )
        first_rows = cur.fetchall()
        digest_input = "\n".join("|".join(str(v) for v in row) for row in first_rows)
        checksum = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()
        print(f"sha256 первых {CHECK_ROWS} строк (ORDER BY log_id): {checksum}")
        print("Сверьте оба числа с program/M3/data/reference_answers.md, раздел «A4», "
              "до того как приступать к задачам step-08.md.")
    conn.close()


if __name__ == "__main__":
    main()
