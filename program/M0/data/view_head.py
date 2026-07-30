"""
Печатает первые N строк файла (по умолчанию 20) — кросс-платформенная
замена команды `head`, которой нет в стандартной Windows PowerShell без
WSL/Git Bash. Строки считаются буквально, включая строку заголовка csv.

Пример:
  python3 view_head.py orders_log.csv
  python3 view_head.py orders_log.csv --lines 5
"""

import argparse


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--lines", type=int, default=20)
    args = ap.parse_args()

    with open(args.path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= args.lines:
                break
            print(line.rstrip("\n"))


if __name__ == "__main__":
    main()
