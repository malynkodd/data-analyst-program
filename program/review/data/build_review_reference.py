"""Эталоны для точек возвратного контроля (`program/review/`).

Возвратная точка не приносит нового материала — она возвращает к уже
пройденному. Но там, где заданием шага было одно число, повторить
задание слово в слово нельзя: помнить ответ и уметь его получить —
разные вещи, а критерий эти два случая не различает. Для таких мест
здесь считаются **новые срезы того же датасета**: схема и правила
очистки те же, числа другие.

Правило то же, что в `program/M2/data/build_reference.py`: ручной ввод
чисел в шаги запрещён, всё печатается этим скриптом. M3 считается
запросами к sqlite поверх `schema.sql` + `seed.sql` +
`retention_seed.sql` — это полное состояние базы, то, в котором она
остаётся после `M3/step-07.md` и до конца модуля. M2 считается теми же
функциями очистки, которые импортируются из `build_reference.py`
модуля, а не переписываются здесь заново: если правило очистки в M2
изменится, эталоны возвратной точки изменятся вместе с ним, а не
разъедутся молча.

Запуск (из корня репозитория):
    .venv\\Scripts\\python.exe program\\review\\data\\build_review_reference.py

CSV-эталоны пишутся рядом с этим файлом.
"""
from __future__ import annotations

import csv
import importlib.util
import sqlite3
import sys
from pathlib import Path

if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
M3_DATA = HERE.parent.parent / "M3" / "data"
M2_DATA = HERE.parent.parent / "M2" / "data"


def m3_connection() -> sqlite3.Connection:
    """Полное состояние базы M3: схема и оба seed-файла модуля."""
    con = sqlite3.connect(":memory:")
    for name in ("schema.sql", "seed.sql", "retention_seed.sql"):
        con.executescript((M3_DATA / name).read_text(encoding="utf-8"))
    con.commit()
    return con


def dump(con: sqlite3.Connection, sql: str, filename: str) -> None:
    cur = con.execute(sql)
    header = [d[0] for d in cur.description]
    rows = cur.fetchall()
    with open(HERE / filename, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)
    print(f"--- {filename}: {len(rows)} строк")
    print(",".join(header))
    for row in rows:
        print(",".join("" if v is None else str(v) for v in row))


RV_CITY_NO_COMPLETED = """
SELECT c.city AS city,
       COUNT(*) AS customers,
       SUM(CASE WHEN t.n IS NULL THEN 1 ELSE 0 END) AS no_completed
FROM customers c
LEFT JOIN (SELECT customer_id, COUNT(*) AS n
           FROM orders WHERE status = 'completed'
           GROUP BY customer_id) t
       ON t.customer_id = c.customer_id
GROUP BY c.city
ORDER BY c.city
"""

RV_MONTH_LAG = """
WITH m AS (
    SELECT substr(order_date, 1, 7) AS month,
           ROUND(SUM(amount), 2) AS revenue
    FROM orders
    WHERE status = 'completed' AND order_date < '2026-01-01'
    GROUP BY 1
)
SELECT month, revenue,
       ROUND(revenue - LAG(revenue) OVER (ORDER BY month), 2) AS diff_prev
FROM m
ORDER BY month
"""

RV_CITY_TOP3 = """
WITH per_customer AS (
    SELECT c.customer_id, c.city, ROUND(SUM(o.amount), 2) AS revenue
    FROM customers c
    JOIN orders o ON o.customer_id = c.customer_id AND o.status = 'completed'
    GROUP BY c.customer_id, c.city
),
ranked AS (
    SELECT city, customer_id, revenue,
           DENSE_RANK() OVER (PARTITION BY city ORDER BY revenue DESC) AS rnk
    FROM per_customer
)
SELECT city, rnk, customer_id, revenue
FROM ranked
WHERE rnk <= 3
ORDER BY city, rnk, customer_id
"""

RV_CITY_ABOVE_AVG = """
WITH city_avg AS (
    SELECT c.city AS city, COUNT(*) AS orders, ROUND(AVG(o.amount), 2) AS avg_check
    FROM customers c
    JOIN orders o ON o.customer_id = c.customer_id AND o.status = 'completed'
    GROUP BY c.city
),
overall AS (
    SELECT AVG(amount) AS avg_all FROM orders WHERE status = 'completed'
)
SELECT city, orders, avg_check
FROM city_avg, overall
WHERE avg_check > overall.avg_all
ORDER BY avg_check DESC, city
"""


# Горизонт M3 (`+3 month`) как вариант задания не годится и в репозиторий
# не попал: `generate_retention.py` возвращает клиента максимум через два
# месяца, поэтому запрос даёт 0 по всем двенадцати когортам. Эталон из
# одних нулей проходит и при неверном запросе — это не проверка. Найдено
# прогоном, а не рассуждением. Вместо горизонта берётся другая форма:
# два уже существующих горизонта в одной таблице, одним запросом.
RV_RETENTION_M1_M2 = """
WITH first_order AS (
    SELECT customer_id, MIN(order_date) AS first_date
    FROM orders WHERE customer_id > 100 GROUP BY customer_id
),
cohorts AS (
    SELECT customer_id, substr(first_date, 1, 7) AS cohort_month FROM first_order
),
cohort_size AS (
    SELECT cohort_month, COUNT(*) AS cohort_size FROM cohorts GROUP BY cohort_month
),
activity AS (
    SELECT c.cohort_month, c.customer_id,
           MAX(CASE WHEN substr(o.order_date, 1, 7) =
                    strftime('%Y-%m', c.cohort_month || '-01', '+1 month')
               THEN 1 ELSE 0 END) AS in_m1,
           MAX(CASE WHEN substr(o.order_date, 1, 7) =
                    strftime('%Y-%m', c.cohort_month || '-01', '+2 month')
               THEN 1 ELSE 0 END) AS in_m2
    FROM cohorts c
    JOIN orders o ON o.customer_id = c.customer_id
    GROUP BY c.cohort_month, c.customer_id
),
retained AS (
    SELECT cohort_month, SUM(in_m1) AS m1, SUM(in_m2) AS m2
    FROM activity GROUP BY cohort_month
)
SELECT s.cohort_month, s.cohort_size,
       COALESCE(r.m1, 0) AS retained_m1,
       ROUND(COALESCE(r.m1, 0) * 100.0 / s.cohort_size, 2) AS pct_m1,
       COALESCE(r.m2, 0) AS retained_m2,
       ROUND(COALESCE(r.m2, 0) * 100.0 / s.cohort_size, 2) AS pct_m2
FROM cohort_size s
LEFT JOIN retained r ON r.cohort_month = s.cohort_month
ORDER BY s.cohort_month
"""


def m2_slices() -> None:
    """Новые срезы M2 — теми же функциями очистки, что и эталон модуля."""
    spec = importlib.util.spec_from_file_location(
        "m2_reference", M2_DATA / "build_reference.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    with open(M2_DATA / "product_lookup.csv", encoding="utf-8") as fh:
        known = {r["product_id"] for r in csv.DictReader(fh)}
    with open(M2_DATA / "sales_extract_raw.csv", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    con = sqlite3.connect(":memory:")
    con.execute(
        "CREATE TABLE sales (order_id TEXT, order_date TEXT, quarter TEXT, "
        "category_code TEXT, product_id TEXT, product_known INTEGER, "
        "channel TEXT, quantity INTEGER, unit_price REAL, amount REAL)"
    )
    payload = []
    for r in rows:
        parsed = mod.parse_date(r["order_date_raw"])
        payload.append((
            r["order_id"],
            parsed.isoformat(),
            mod.quarter_label(parsed),
            mod.CATEGORY_CODE[mod.clean_category(r["category_raw"])],
            r["product_id"],
            1 if r["product_id"] in known else 0,
            r["channel"],
            int(r["quantity"]),
            float(r["unit_price"]),
            mod.parse_amount(r["amount_raw"]),
        ))
    con.executemany("INSERT INTO sales VALUES (?,?,?,?,?,?,?,?,?,?)", payload)
    con.commit()

    print("=== M2: новые срезы того же датасета (правила очистки — те же) ===")
    print(f"строк в выгрузке: {len(rows)}")
    for cat, quarter, channel in [
        ("phones", "2025-Q3", "retail"),
        ("appliances", "2024-Q3", None),
        ("clothing", None, "wholesale"),
    ]:
        where = ["category_code = ?"]
        args: list[object] = [cat]
        if quarter:
            where.append("quarter = ?")
            args.append(quarter)
        if channel:
            where.append("channel = ?")
            args.append(channel)
        total, cnt = con.execute(
            "SELECT ROUND(SUM(amount),2), COUNT(*) FROM sales "
            f"WHERE {' AND '.join(where)}",
            args,
        ).fetchone()
        print(
            f"category={cat} quarter={quarter or 'все'} channel={channel or 'все'} "
            f"total={total} rows={cnt}"
        )

    # Число строк с неизвестным product_id (838) напечатано в M2 девять
    # раз — как задание возвратной точки оно не годится, его можно помнить.
    # Различных таких product_id и их сумма в репозитории не публикуются
    # нигде: их и спрашивает R2.
    missing_rows, missing_ids, missing_total = con.execute(
        "SELECT COUNT(*), COUNT(DISTINCT product_id), ROUND(SUM(amount),2) "
        "FROM sales WHERE product_known = 0"
    ).fetchone()
    print("--- строки с product_id вне справочника ---")
    print(
        f"rows={missing_rows} distinct_product_id={missing_ids} "
        f"amount_total={missing_total}"
    )

    print("--- возвраты (amount < 0) по категориям ---")
    for code, total, cnt in con.execute(
        "SELECT category_code, ROUND(SUM(amount),2), COUNT(*) FROM sales "
        "WHERE amount < 0 GROUP BY category_code ORDER BY category_code"
    ):
        print(f"category={code} returns_total={total} rows={cnt}")


def main() -> None:
    con = m3_connection()
    print("=== состояние базы M3 (schema + seed + retention_seed) ===")
    for table in ("customers", "orders", "order_items", "payments", "products"):
        n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {n}")

    print()
    print("=== M3: новые срезы полной базы ===")
    dump(con, RV_CITY_NO_COMPLETED, "rv_a2_city_no_completed.csv")
    dump(con, RV_MONTH_LAG, "rv_a1_month_revenue_lag.csv")
    dump(con, RV_CITY_TOP3, "rv_a1_city_top3.csv")
    dump(con, RV_RETENTION_M1_M2, "rv_a3_cohort_retention_m1_m2.csv")
    dump(con, RV_CITY_ABOVE_AVG, "rv_a2_city_above_avg.csv")

    print()
    m2_slices()


if __name__ == "__main__":
    main()
