"""
Инструмент для шага M1.2. Считает "активных клиентов" в clients.csv по
явно заданному определению. Не задаёт определение сам — только считает
то, что ему передали флагами. Учащийся запускает готовый скрипт (умение
из M0, I2), не пишет код: написание кода — предмет модулей B (M5).

Примеры:
  python3 count_active.py clients.csv --by status
  python3 count_active.py clients.csv --by login --within 30
  python3 count_active.py clients.csv --by combo --within 60 --include-trial
"""

import argparse
import csv
from datetime import date

REFERENCE_DATE = date(2026, 7, 1)


def parse_date(s):
    return date.fromisoformat(s) if s else None


def days_since(d):
    return (REFERENCE_DATE - d).days if d else None


def within(d, window):
    n = days_since(d)
    return n is not None and n <= window


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path")
    ap.add_argument("--by", choices=["status", "login", "payment", "combo"], required=True)
    ap.add_argument("--within", type=int, default=None, help="окно в днях для login/payment/combo")
    ap.add_argument("--include-trial", action="store_true")
    ap.add_argument("--include-paused", action="store_true")
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.csv_path, encoding="utf-8")))
    count = 0
    for r in rows:
        login = parse_date(r["last_login_date"])
        payment = parse_date(r["last_payment_date"])
        status = r["plan_status"]

        if args.by == "status":
            hit = status == "active"
        elif args.by == "login":
            hit = within(login, args.within)
        elif args.by == "payment":
            hit = within(payment, args.within)
        else:  # combo
            allowed_status = {"active"}
            if args.include_trial:
                allowed_status.add("trial")
            if args.include_paused:
                allowed_status.add("paused")
            in_population = status in allowed_status
            recent = within(login, args.within) or within(payment, args.within)
            hit = in_population and recent

        if hit:
            count += 1

    # ASCII-вывод намеренно: на части Windows-терминалов консольная
    # кодовая страница (cp866/cp1251) ломает кириллицу в stdout, и
    # результат пришлось бы отлаживать вместо того, чтобы читать его.
    print(f"rows in input file: {len(rows)}")
    print(f"active by this definition: {count}")


if __name__ == "__main__":
    main()
