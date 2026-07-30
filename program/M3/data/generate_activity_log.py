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
"""
from __future__ import annotations

import random
import sqlite3
import sys

if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

SEED = 20260804
N_ROWS = 4_800_000
EVENT_TYPES = ["page_view", "page_view", "page_view", "login", "add_to_cart"]


def main() -> None:
    if len(sys.argv) != 2:
        print("Использование: python generate_activity_log.py <путь_к_m3.db>")
        raise SystemExit(1)
    db_path = sys.argv[1]

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT customer_id FROM customers")
    customer_ids = [row[0] for row in cur.fetchall()]
    if not customer_ids:
        print("Таблица customers пуста — сначала загрузите schema.sql, seed.sql, retention_seed.sql")
        raise SystemExit(1)

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
        for i in range(1, N_ROWS + 1):
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
    print(f"activity_log: {cur.fetchone()[0]} строк, без индекса на customer_id (сделано намеренно, умение A4)")
    conn.close()


if __name__ == "__main__":
    main()
