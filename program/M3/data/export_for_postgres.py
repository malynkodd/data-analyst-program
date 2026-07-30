"""Выгружает таблицы m3.db (SQLite) в CSV для загрузки в PostgreSQL.

Зачем отдельный скрипт, а не `sqlite3 m3.db .dump`: вывод `.dump` — это
SQL со SQLite-специфичным синтаксисом (`PRAGMA`, `BEGIN TRANSACTION`,
двойные кавычки вокруг идентификаторов и строк), который PostgreSQL не
принимает как есть. CSV принимают оба движка без правок, а схему для
PostgreSQL задаёт отдельный файл `schema_pg.sql` — там типы выбраны
осознанно, а не унаследованы от SQLite (см. `program/M3/step-09.md`).

Кросс-платформенность: скрипт на стандартной библиотеке Python, без
`pip install` и без POSIX-команд (решение 13 `design/decisions.md`).
Кодировка чтения и записи задана явно (решение 17).

Запуск:
    python program/M3/data/export_for_postgres.py m3.db
    python program/M3/data/export_for_postgres.py m3.db --out pg_csv
    python program/M3/data/export_for_postgres.py m3.db --with-activity-log
    python program/M3/data/export_for_postgres.py --help

`activity_log` (4 800 000 строк, около 160 МБ в CSV) выгружается только
по явному флагу `--with-activity-log` — она нужна лишь в `step-12.md`, а
до него лишний файл такого размера в рабочей папке ни к чему.

После выгрузки — загрузка в PostgreSQL, по одной команде на таблицу,
в этом порядке (внешние ключи: `customers` до `orders`, `orders` до
`order_items`/`payments`):

    psql -U postgres -d m3 -c "\\copy customers FROM 'pg_csv/customers.csv' CSV HEADER"
"""
from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from pathlib import Path

if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# Порядок словаря = порядок загрузки в PostgreSQL: родительские таблицы
# раньше дочерних, иначе внешний ключ отклонит вставку. Колонки
# перечислены явно, а не через SELECT *, чтобы порядок колонок в CSV не
# зависел от порядка объявления в схеме.
TABLES: dict[str, list[str]] = {
    "customers":   ["customer_id", "name", "city"],
    "products":    ["product_id", "name", "category"],
    "orders":      ["order_id", "customer_id", "order_date", "status", "amount"],
    "order_items": ["order_item_id", "order_id", "product_id", "quantity", "unit_price"],
    "payments":    ["payment_id", "order_id", "paid_at", "amount", "method"],
}
ACTIVITY_LOG = ("activity_log", ["log_id", "customer_id", "event_type", "event_date"])


def export_table(conn: sqlite3.Connection, out_dir: Path, table: str, cols: list[str]) -> int:
    # ORDER BY по первичному ключу: без него порядок строк, который вернёт
    # SQLite, не гарантирован спецификацией, и два прогона на одной базе
    # могли бы дать CSV, различающиеся порядком строк. Сверять такие файлы
    # между собой (и с копией автора) было бы нечем.
    rows = conn.execute(f"SELECT {', '.join(cols)} FROM {table} ORDER BY {cols[0]}")
    path = out_dir / f"{table}.csv"
    n = 0
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(cols)
        for row in rows:
            writer.writerow(row)
            n += 1
    print(f"{table}: {n} строк -> {path}")
    return n


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Выгружает таблицы m3.db в CSV для загрузки в PostgreSQL "
                    "(step-09.md, умение A2, часть 6 из 7)."
    )
    ap.add_argument("db_path", help="путь к m3.db (файл должен уже существовать)")
    ap.add_argument("--out", default="pg_csv", help="папка для CSV (по умолчанию pg_csv)")
    ap.add_argument(
        "--with-activity-log", action="store_true",
        help="выгрузить также activity_log (около 160 МБ, нужна только в step-12.md)",
    )
    args = ap.parse_args()

    db_path = Path(args.db_path)
    # Проверка ДО подключения: sqlite3.connect создаёт пустой файл по
    # несуществующему пути молча — та же причина, что в
    # generate_activity_log.py.
    if not db_path.exists():
        print(
            f"Файл базы {db_path} не найден. Сначала соберите её по "
            f"step-01.md: schema.sql -> seed.sql -> retention_seed.sql."
        )
        raise SystemExit(1)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    try:
        existing = {
            r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        missing = [t for t in TABLES if t not in existing]
        if missing:
            print(
                f"В {db_path} нет таблиц: {', '.join(missing)}. Схема загружена "
                f"не полностью — вернитесь к step-01.md и загрузите schema.sql."
            )
            raise SystemExit(1)

        total = 0
        for table, cols in TABLES.items():
            total += export_table(conn, out_dir, table, cols)

        if args.with_activity_log:
            table, cols = ACTIVITY_LOG
            if table not in existing:
                # Не падение: activity_log создаётся генератором из step-08.md
                # и до него законно отсутствует. Сообщение называет причину,
                # а не оставляет пустую папку без объяснения.
                print(
                    f"Таблица {table} в {db_path} отсутствует — её создаёт "
                    f"generate_activity_log.py (step-08.md). Остальные таблицы "
                    f"выгружены, {table} пропущена."
                )
            else:
                total += export_table(conn, out_dir, table, cols)

        print(f"Итого выгружено строк: {total}")
        print(
            "Загрузка в PostgreSQL — по порядку из этого вывода сверху вниз "
            "(родительские таблицы раньше дочерних), см. step-09.md, 1.3."
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
