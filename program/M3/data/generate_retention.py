"""Генератор дополнительных клиентов и заказов модуля M3 для умения A3
(когортный retention). Детерминирован (SEED ниже). Дополняет схему
program/M3/data/schema.sql (те же таблицы customers/orders, новые строки,
customer_id 101-340 и order_id 20001+ — не пересекаются с customer_id 1-12
и order_id 101-119 из seed.sql, использованными в step-05.md).

Запуск: python program/M3/data/generate_retention.py
Пишет program/M3/data/retention_seed.sql.
"""
from __future__ import annotations

import calendar
import random

SEED = 20260803
random.seed(SEED)

OUT_PATH = "program/M3/data/retention_seed.sql"

COHORT_MONTHS = [f"2025-{m:02d}" for m in range(1, 13)]  # 12 когорт, Jan-Dec 2025
N_PER_COHORT = 20
CITIES = ["Київ", "Львів", "Одеса", "Харків", "Дніпро"]

# retention-вероятность (заказ в месяц+1 после когортного месяца) — плавно
# снижается по году, чтобы кривая не была константой; конкретные числа
# retention считаются потом реальным запросом, не задаются здесь как факт.
RETENTION_PROB_BY_COHORT_INDEX = [
    0.45, 0.42, 0.40, 0.38, 0.36, 0.34,
    0.33, 0.31, 0.29, 0.27, 0.25, 0.23,
]

# Независимый бросок на месяц+2 (для step-07.md, 1.4 — та же механика,
# другой горизонт): часть клиентов возвращается через месяц, пропустив
# предыдущий, поэтому бросок не завязан на исход месяца+1.
M2_RETENTION_PROB_BY_COHORT_INDEX = [
    0.22, 0.20, 0.19, 0.18, 0.17, 0.16,
    0.15, 0.14, 0.13, 0.12, 0.11, 0.10,
]


def month_add(ym: str, delta: int) -> str:
    y, m = map(int, ym.split("-"))
    total = (y * 12 + (m - 1)) + delta
    y2, m2 = divmod(total, 12)
    return f"{y2:04d}-{m2 + 1:02d}"


def random_day(ym: str) -> str:
    y, m = map(int, ym.split("-"))
    last_day = calendar.monthrange(y, m)[1]
    day = random.randint(1, last_day)
    return f"{ym}-{day:02d}"


def main() -> None:
    customer_id = 100
    order_id = 20000
    customer_rows = []
    order_rows = []

    for cohort_idx, cohort_month in enumerate(COHORT_MONTHS):
        retention_prob = RETENTION_PROB_BY_COHORT_INDEX[cohort_idx]
        m2_prob = M2_RETENTION_PROB_BY_COHORT_INDEX[cohort_idx]
        for _ in range(N_PER_COHORT):
            customer_id += 1
            city = random.choice(CITIES)
            customer_rows.append((customer_id, f"Клієнт retention {customer_id}", city))

            order_id += 1
            first_order_date = random_day(cohort_month)
            order_rows.append((order_id, customer_id, first_order_date, "completed",
                                round(random.uniform(200, 1500), 2)))

            if random.random() < retention_prob:
                next_month = month_add(cohort_month, 1)
                order_id += 1
                order_rows.append((order_id, customer_id, random_day(next_month), "completed",
                                    round(random.uniform(200, 1500), 2)))

            if random.random() < m2_prob:
                month_plus_2 = month_add(cohort_month, 2)
                order_id += 1
                order_rows.append((order_id, customer_id, random_day(month_plus_2), "completed",
                                    round(random.uniform(200, 1500), 2)))

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(
            "-- Сгенерировано generate_retention.py, SEED = %d. Дополняет\n"
            "-- customers/orders program/M3/data/seed.sql для умения A3\n"
            "-- (когортный retention, 12 когорт). Не меняет существующие\n"
            "-- строки customer_id 1-12 / order_id 101-119.\n"
            "-- order_items/payments для этих клиентов не заполняются: A3\n"
            "-- проверяет только когортный retention по orders, не выручку.\n\n"
            % SEED
        )
        f.write("INSERT INTO customers (customer_id, name, city) VALUES\n")
        f.write(",\n".join(
            f"({cid}, '{name}', '{city}')" for cid, name, city in customer_rows
        ))
        f.write(";\n\n")

        f.write("INSERT INTO orders (order_id, customer_id, order_date, status, amount) VALUES\n")
        f.write(",\n".join(
            f"({oid}, {cid}, '{d}', '{status}', {amount})"
            for oid, cid, d, status, amount in order_rows
        ))
        f.write(";\n")

    print(f"customers: {len(customer_rows)}, orders: {len(order_rows)}")


if __name__ == "__main__":
    main()
