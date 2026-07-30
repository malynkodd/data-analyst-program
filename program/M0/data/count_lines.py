"""
Считает строки данных в csv-файле (без строки заголовка) —
кросс-платформенная замена `wc -l`, которой нет в стандартной Windows
PowerShell без WSL/Git Bash. С флагом --status считает не все строки, а
только те, где колонка status равна указанному значению.

Пример:
  python3 count_lines.py orders_log.csv
  python3 count_lines.py orders_log.csv --status shipped
"""

import argparse
import csv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--status", default=None)
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.path, encoding="utf-8")))
    if args.status is None:
        count = len(rows)
    else:
        count = sum(1 for r in rows if r["status"] == args.status)

    # ASCII-вывод: M0/M1 на латинице по решению 17.
    print(f"rows in file: {len(rows)}")
    if args.status is not None:
        print(f"rows with status == {args.status}: {count}")


if __name__ == "__main__":
    main()
