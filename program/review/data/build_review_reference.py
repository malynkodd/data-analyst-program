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
from datetime import date, timedelta
from pathlib import Path

if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
M3_DATA = HERE.parent.parent / "M3" / "data"
M2_DATA = HERE.parent.parent / "M2" / "data"
M5_DATA = HERE.parent.parent / "M5" / "data"
M6_DATA = HERE.parent.parent / "M6" / "data"
M8_DATA = HERE.parent.parent / "M8" / "data"


def import_module_reference(path: Path, name: str):
    """Импортирует эталонный скрипт модуля, чтобы взять из него правила.

    То же основание, что у m2_slices(): правило, посчитанное здесь заново,
    разъедется с модулем молча. Всё, что можно взять из модуля, берётся из
    модуля — квантиль, разбор даты, чтение сырого файла."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


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


# Срез A6 (решение 52): две конструкции шага M3.13 в одном запросе —
# `NOT EXISTS`/`LEFT JOIN ... IS NULL` для клиентов без единого completed
# и `CASE WHEN` в агрегате для распределения остальных по вёдрам выручки.
# Ось группировки та же (город), но величины другие: `a6_task4_case_buckets`
# считает вёдра по сумме одного заказа, здесь — по сумме всех заказов
# клиента, и клиенты без заказов вынесены отдельной колонкой.
RV_A6_CITY_BUCKETS = """
SELECT c.city AS city,
       SUM(CASE WHEN t.total IS NULL THEN 1 ELSE 0 END) AS no_completed,
       SUM(CASE WHEN t.total >  0    AND t.total <  500  THEN 1 ELSE 0 END) AS small,
       SUM(CASE WHEN t.total >= 500  AND t.total < 2000  THEN 1 ELSE 0 END) AS medium,
       SUM(CASE WHEN t.total >= 2000 THEN 1 ELSE 0 END) AS large
FROM customers c
LEFT JOIN (SELECT customer_id, SUM(amount) AS total
           FROM orders WHERE status = 'completed'
           GROUP BY customer_id) t
       ON t.customer_id = c.customer_id
GROUP BY c.city
ORDER BY c.city
"""

# Ступени нормализации — те же три, что в M3.14; отличается измеритель.
# Шаг мерит лестницу числом сопоставленных строк (11 → 21 → 31), точка —
# гривнами: сумма сопоставленных счетов и остаток. Обратное направление
# («сколько контрагентов справочника получили счёт») проверено прогоном и
# отброшено: даёт 10 на всех трёх ступенях, то есть константу, а константа
# сходится и при неверном запросе — та же причина, по которой отброшен
# горизонт M3 у ретеншена.
A7_LADDER = {
    "raw": "f.counterparty_raw = p.legal_name",
    "trim": "TRIM(f.counterparty_raw) = TRIM(p.legal_name)",
    "trim_spaces": (
        "REPLACE(TRIM(f.counterparty_raw),'  ',' ') = "
        "REPLACE(TRIM(p.legal_name),'  ',' ')"
    ),
}


def a7_ladder_uah() -> None:
    """A7: та же лестница нормализации, измеренная деньгами, а не строками."""
    con = sqlite3.connect(":memory:")
    con.executescript((M3_DATA / "registry_seed.sql").read_text(encoding="utf-8"))
    invoices, total = con.execute(
        "SELECT COUNT(*), ROUND(SUM(amount), 2) FROM invoice_feed"
    ).fetchone()
    rows = []
    for method, cond in A7_LADDER.items():
        matched, amount = con.execute(
            "SELECT COUNT(*), ROUND(COALESCE(SUM(f.amount), 0), 2) "
            f"FROM invoice_feed f JOIN partner_registry p ON {cond}"
        ).fetchone()
        rows.append((method, matched, amount, round(total - amount, 2)))
    write_rows("rv_a7_ladder_uah.csv", ["method", "matched", "matched_uah", "lost_uah"], rows)
    print(f"счетов в потоке: {invoices}, на сумму {total}")


def b7_big_channel() -> None:
    """B7: агрегат по файлу, который не помещается в память, — новая ось.

    Шаг M5.09 считает по месяцам (`ref_big_month.csv`), точка — по каналам.
    Читается тем же способом, которым шаг требует читать: построчно, без
    загрузки файла целиком."""
    totals: dict[str, float] = {}
    counts: dict[str, int] = {}
    lines = 0
    with (M5_DATA / "raw" / "payouts_big.csv").open(encoding="cp1251", newline="") as fh:
        for row in csv.DictReader(fh):
            lines += 1
            if row["status"] != "PAID":
                continue
            channel = row["channel"]
            totals[channel] = totals.get(channel, 0.0) + float(row["amount"])
            counts[channel] = counts.get(channel, 0) + 1
    rows = [(c, counts[c], round(totals[c], 2)) for c in sorted(totals)]
    write_rows("rv_b7_big_channel.csv", ["channel", "payouts", "paid_uah"], rows)
    print(f"строк в payouts_big.csv: {lines}")


def f4_fee_distribution() -> None:
    """F4: те же двенадцать чисел — на колонке, которую M6.05 не описывал.

    Шаг описывает `amount` из `ledger.csv` (completed). Здесь — комиссия
    `fee_cents` из `settlement.csv`, переведённая в гривны. Квантиль,
    среднее и выборочное отклонение берутся из эталонного скрипта модуля,
    а не считаются здесь заново."""
    stats = import_module_reference(M6_DATA / "reference_m6_stats.py", "m6_stats")
    with (M6_DATA / "raw" / "settlement.csv").open(encoding="utf-8", newline="") as fh:
        fees = sorted(int(r["fee_cents"]) / 100 for r in csv.DictReader(fh))
    q1, q3 = stats.quantile(fees, 0.25), stats.quantile(fees, 0.75)
    median = stats.quantile(fees, 0.50)
    rows = [
        ("строк", len(fees)),
        ("среднее", round(stats.mean(fees), 2)),
        ("медиана", round(median, 2)),
        ("стандартное_отклонение", round(stats.stdev(fees), 2)),
        ("минимум", round(fees[0], 2)),
        ("q1", round(q1, 2)),
        ("q3", round(q3, 2)),
        ("iqr", round(q3 - q1, 2)),
        ("p90", round(stats.quantile(fees, 0.90), 2)),
        ("p95", round(stats.quantile(fees, 0.95), 2)),
        ("p99", round(stats.quantile(fees, 0.99), 2)),
        ("максимум", round(fees[-1], 2)),
    ]
    write_rows("rv_f4_fee_distribution.csv", ["показатель", "значение"], rows)
    upper = q3 + 1.5 * (q3 - q1)
    outliers = sum(1 for v in fees if v > upper)
    print(
        f"порог Q3+1.5*IQR = {round(upper, 2)}; выбросов сверху: {outliers}. "
        f"На `amount` из M6.05 то же правило даёт другое число — колонка "
        f"другая, и это весь смысл задания."
    )


def m8_slices() -> None:
    """F6, F7, F8, F1 — новые срезы датасета M8.

    Снапшот, CAC и разбор даты берутся из эталонного скрипта модуля."""
    p = import_module_reference(M8_DATA / "reference_m8_product.py", "m8_product")
    leads, revenue = p.read("leads.csv"), p.read("revenue.csv")

    # --- F6: те же метрики на базе одного полного месяца, а не всего ряда.
    month, month_end = "2026-04", date(2026, 4, 30)
    leads_to_date = [r for r in leads if p.as_date(r["signup_date"]) <= month_end]
    payers = {r["user_id"] for r in revenue if r["txn_date"].startswith(month)}
    revenue_month = sum(float(r["amount"]) for r in revenue if r["txn_date"].startswith(month))
    arppu = revenue_month / len(payers)
    conversion = len(payers) / len(leads_to_date)
    arpu = revenue_month / len(leads_to_date)
    assert abs(arpu - arppu * conversion) < 0.01, "базы не сходятся"
    write_rows("rv_f6_month_metrics.csv", ["метрика", "значение"], [
        ("лидов_на_конец_месяца", len(leads_to_date)),
        ("плательщиков_в_месяце", len(payers)),
        ("конверсия_месяца", round(conversion, 4)),
        ("выручка_месяца", round(revenue_month, 2)),
        ("ARPU_месяца", round(arpu, 2)),
        ("ARPPU_месяца", round(arppu, 2)),
    ])
    print(f"тождество ARPU = ARPPU * конверсия держится и на месячной базе: "
          f"{round(arppu * conversion, 2)}")

    # --- F7: та же ось, другие границы. Шаг делит по третям (3 балла),
    # точка — по квартилям (4 балла): 64 клетки вместо 27.
    amount: dict[str, float] = {}
    freq: dict[str, int] = {}
    last: dict[str, date] = {}
    for r in revenue:
        user, when = r["user_id"], p.as_date(r["txn_date"])
        amount[user] = amount.get(user, 0.0) + float(r["amount"])
        freq[user] = freq.get(user, 0) + 1
        if user not in last or when > last[user]:
            last[user] = when
    users = sorted(amount)
    recency = {u: (p.SNAPSHOT - last[u]).days for u in users}

    def bounds(values) -> list[float]:
        ordered = sorted(values)
        return [p.quantile(ordered, q) for q in (0.25, 0.50, 0.75)]

    rb, fb, mb = bounds(recency.values()), bounds(freq.values()), bounds(amount.values())

    def high(value: float, b: list[float]) -> int:
        return 1 if value <= b[0] else (2 if value <= b[1] else (3 if value <= b[2] else 4))

    def low(value: float, b: list[float]) -> int:
        return 4 if value <= b[0] else (3 if value <= b[1] else (2 if value <= b[2] else 1))

    segments: dict[str, list] = {}
    for u in users:
        code = f"{low(recency[u], rb)}{high(freq[u], fb)}{high(amount[u], mb)}"
        cell = segments.setdefault(code, [0, 0.0])
        cell[0] += 1
        cell[1] += amount[u]
    total_revenue = sum(amount.values())
    write_rows("rv_f7_quartile_segments.csv",
               ["сегмент", "клиентов", "выручка", "доля_выручки"],
               [(c, segments[c][0], round(segments[c][1], 2),
                 round(segments[c][1] * 100 / total_revenue, 2))
                for c in sorted(segments)])
    print(f"непустых сегментов {len(segments)} из 64; клиентов "
          f"{sum(v[0] for v in segments.values())}; границы R "
          f"{[round(x, 2) for x in rb]}, F {[round(x, 2) for x in fb]}, "
          f"M {[round(x, 2) for x in mb]}")

    # --- F8: тот же аппарат, отложена предпоследняя неделя, а не последняя.
    daily: dict[date, float] = {}
    for r in revenue:
        when = p.as_date(r["txn_date"])
        daily[when] = daily.get(when, 0.0) + float(r["amount"])
    first = min(daily)
    while first.weekday() != 0:
        first += timedelta(days=1)
    last_day = max(daily)
    while last_day.weekday() != 6:
        last_day -= timedelta(days=1)
    series, cursor = [], first
    while cursor <= last_day:
        series.append((cursor, daily.get(cursor, 0.0)))
        cursor += timedelta(days=1)
    weeks = [series[i:i + 7] for i in range(0, len(series), 7)]
    holdout, train = weeks[-2], weeks[:-2]
    day_avg = sum(v for w in train for _, v in w) / (len(train) * 7)
    base = sum(v for w in train[-4:] for _, v in w) / 28
    coefficients = []
    for weekday in range(7):
        values = [v for w in train for dt, v in w if dt.weekday() == weekday]
        coefficients.append(sum(values) / len(values) / day_avg)

    def mape(predicted) -> float:
        pairs = zip(holdout, predicted)
        return sum(abs(actual - pred) / actual for (_, actual), pred in pairs) / 7 * 100

    flat = mape([base] * 7)
    seasonal = mape([base * coefficients[dt.weekday()] for dt, _ in holdout])
    names = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
    write_rows("rv_f8_holdout_prev_week.csv", ["показатель", "значение"],
               [(f"коэффициент_{names[i]}", round(coefficients[i], 4)) for i in range(7)] + [
                   ("полных_недель", len(train)),
                   ("база_прогноза", round(base, 2)),
                   ("MAPE_с_сезонностью", round(seasonal, 2)),
                   ("MAPE_без_сезонности", round(flat, 2)),
                   ("выигрыш_сезонности_пп", round(flat - seasonal, 2)),
               ])
    print(f"отложена неделя с {holdout[0][0]}; вывод шага M8.06 (сезонность "
          f"хуже плоской базы) на другой неделе не переворачивается")

    # --- F1: тот же LTV на другом горизонте. Шаг считает D30, точка — D60,
    # и горизонт срезает когорту: зрелых клиентов меньше.
    converted = {r["user_id"]: p.as_date(r["conversion_date"])
                 for r in leads if r["user_id"] and r["conversion_date"]}
    rows = []
    for horizon in (30, 60):
        mature = {u for u, when in converted.items()
                  if when + timedelta(days=horizon) <= p.SNAPSHOT}
        total = 0.0
        for r in revenue:
            user = r["user_id"]
            if user in mature and 0 <= (p.as_date(r["txn_date"]) - converted[user]).days <= horizon:
                total += float(r["amount"])
        ltv = total / len(mature)
        rows.append((f"зрелых_клиентов_D{horizon}", len(mature)))
        rows.append((f"LTV_D{horizon}", round(ltv, 2)))
        rows.append((f"ROI_D{horizon}", round(ltv / p.CAC - 1, 4)))
    rows.append(("CAC", p.CAC))
    write_rows("rv_f1_ltv_horizons.csv", ["показатель", "значение"], rows)
    print("D30 обязан совпасть с `M8/data/ref_business_metrics.csv` "
          "(LTV_D30 = 2783.32 при n = 808) — это контроль метода, а не задание")


def write_rows(filename: str, header: list[str], rows) -> None:
    with open(HERE / filename, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)
    print(f"--- {filename}: {len(rows)} строк")
    print(",".join(header))
    for row in rows:
        print(",".join("" if v is None else str(v) for v in row))


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
    dump(con, RV_A6_CITY_BUCKETS, "rv_a6_city_buckets.csv")

    print()
    print("=== M3: лестница нормализации в гривнах (A7) ===")
    a7_ladder_uah()

    print()
    print("=== M5: агрегат по большому файлу, новая ось (B7) ===")
    b7_big_channel()

    print()
    print("=== M6: описание распределения на другой колонке (F4) ===")
    f4_fee_distribution()

    print()
    print("=== M8: месяц, квартили, другая отложенная неделя, D60 ===")
    m8_slices()

    print()
    m2_slices()


if __name__ == "__main__":
    main()
