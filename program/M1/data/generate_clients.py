"""
Генератор сквозного датасета модуля M1.

Синтетика. Спецификация встроенной неоднозначности — в
program/M1/data/README.md. Запуск детерминирован (SEED фиксирован),
поэтому файл можно перегенерировать и получить побайтово тот же
результат — это и есть эталон для M1.1-M1.3.

Дата "сегодня" для расчётов зашита как REFERENCE_DATE, а не берётся из
системных часов: иначе результат "активен за последние 30 дней" менялся
бы в зависимости от того, в какой день учащийся запустил скрипт.
"""

import csv
import random
from datetime import date, timedelta

SEED = 20260701
REFERENCE_DATE = date(2026, 7, 1)
N = 240
OUT_PATH = "clients.csv"

random.seed(SEED)


def days_before(min_days, max_days):
    d = REFERENCE_DATE - timedelta(days=random.randint(min_days, max_days))
    return d.isoformat()


def maybe_none(value, none_probability):
    return "" if random.random() < none_probability else value


def make_client(client_id):
    roll = random.random()
    if roll < 0.50:
        status = "active"
    elif roll < 0.60:
        status = "trial"
    elif roll < 0.75:
        status = "paused"
    else:
        status = "cancelled"

    registration_date = days_before(30, 730)

    if status == "active":
        last_login_date = days_before(0, 40)
        last_payment_date = days_before(0, 35)
    elif status == "trial":
        last_login_date = days_before(0, 14)
        last_payment_date = ""
    elif status == "paused":
        last_login_date = days_before(5, 150)
        last_payment_date = maybe_none(days_before(40, 200), 0.30)
    else:  # cancelled
        last_login_date = days_before(60, 500)
        last_payment_date = maybe_none(days_before(90, 600), 0.40)

    return {
        "client_id": f"C{client_id:04d}",
        "registration_date": registration_date,
        "plan_status": status,
        "last_login_date": last_login_date,
        "last_payment_date": last_payment_date,
    }


def main():
    rows = [make_client(i) for i in range(1, N + 1)]
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "client_id",
                "registration_date",
                "plan_status",
                "last_login_date",
                "last_payment_date",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"written {len(rows)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
