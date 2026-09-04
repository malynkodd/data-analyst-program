"""
Кросс-платформенный просмотр отфильтрованных строк clients.csv.

Замена grep/awk: этих инструментов нет в стандартной PowerShell без
WSL. Скрипт печатает то же самое, что дала бы связка grep+awk, но
работает одинаково в PowerShell, Git Bash, WSL и на macOS/Linux —
через один и тот же вызов `python3 peek_clients.py ...`.
"""

import argparse
import csv
import sys

# Кириллица в консоли не полагается на кодировку терминала
# (решение 17; симуляция 2026-09-04, дефект M9-1: без этой строки
# скрипт падал с UnicodeEncodeError, допечатав часть вывода).
sys.stdout.reconfigure(encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path")
    ap.add_argument("--status", required=True)
    ap.add_argument("--login-after", default=None, help="YYYY-MM-DD; оставить строки с login >= этой даты")
    ap.add_argument("--login-before", default=None, help="YYYY-MM-DD; оставить строки с login < этой даты")
    ap.add_argument("--limit", type=int, default=3)
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.csv_path, encoding="utf-8")))
    shown = 0
    for r in rows:
        if r["plan_status"] != args.status:
            continue
        login = r["last_login_date"]
        if args.login_after and not (login and login >= args.login_after):
            continue
        if args.login_before and not (login and login < args.login_before):
            continue
        print(",".join(r.values()))
        shown += 1
        if shown >= args.limit:
            break
    if shown == 0:
        print("(нет строк, подходящих под условие)")


if __name__ == "__main__":
    main()
