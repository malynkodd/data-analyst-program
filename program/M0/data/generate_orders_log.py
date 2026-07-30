"""
Генератор сквозного датасета модуля M0.

Синтетика. Спецификация — в program/M0/data/README.md. Запуск
детерминирован (SEED фиксирован), поэтому файл можно перегенерировать и
получить побайтово тот же результат.

Датасет намеренно "чистый" (без разных форматов дат, без текстовых чисел
и так далее) — M0 учит пользоваться терминалом и скриптами, а не находить
дефекты в данных. Работа с "грязной" выгрузкой — предмет M2 (Таблицы) и
M6 (Грязные данные), не M0.

Значения полей — латиница/ASCII намеренно: часть скриптов модуля печатает
строки датасета в консоль, а кириллица в stdout ломается на части
Windows-терминалов (кодовая страница cp866/cp1251) — тот же довод, что и
в program/M1/data/count_active.py.
"""

import csv
import random
from datetime import date, timedelta

SEED = 20260801
REFERENCE_DATE = date(2026, 8, 1)
N = 500
OUT_PATH = "orders_log.csv"

CITIES = ["Kyiv", "Lviv", "Odesa", "Kharkiv", "Dnipro", "Zaporizhzhia", "Vinnytsia", "Poltava"]

random.seed(SEED)


def days_before(min_days, max_days):
    return (REFERENCE_DATE - timedelta(days=random.randint(min_days, max_days))).isoformat()


def make_order(order_id):
    roll = random.random()
    if roll < 0.60:
        status = "shipped"
        note = "packaging damaged" if random.random() < 0.15 else "delivered on time"
    elif roll < 0.85:
        status = "pending"
        note = "payment pending" if random.random() < 0.30 else "awaiting warehouse"
    else:
        status = "cancelled"
        note = "out of stock" if random.random() < 0.40 else "customer cancelled"

    return {
        "order_id": f"D{order_id:04d}",
        "order_date": days_before(0, 120),
        "city": random.choice(CITIES),
        "status": status,
        "note": note,
    }


def main():
    rows = [make_order(i) for i in range(1, N + 1)]
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["order_id", "order_date", "city", "status", "note"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"written {len(rows)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
