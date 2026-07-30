"""
Находит строки csv, где хотя бы одна колонка содержит заданную
подстроку — кросс-платформенная замена `grep`, которой нет в стандартной
Windows PowerShell без WSL/Git Bash. Поиск точный (регистр важен), без
регулярных выражений.

Пример:
  python3 find_row.py orders_log.csv --contains damaged
  python3 find_row.py orders_log.csv --contains cancelled --limit 3
"""

import argparse
import csv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--contains", required=True)
    ap.add_argument("--limit", type=int, default=5)
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.path, encoding="utf-8")))
    matches = [r for r in rows if any(args.contains in v for v in r.values())]

    shown = 0
    for r in matches:
        print(",".join(r.values()))
        shown += 1
        if shown >= args.limit:
            break

    print(f"total matches: {len(matches)}")


if __name__ == "__main__":
    main()
