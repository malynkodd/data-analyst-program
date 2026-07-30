"""
Кросс-платформенная проверка порядка двух файлов по времени изменения.

Замена `stat --format=%Y`: флаг `--format` есть в GNU stat (Linux), но
не в BSD stat (macOS) и не существует в PowerShell вовсе. `os.path.getmtime`
даёт то же самое одинаково на всех трёх.
"""

import os
import sys


def main():
    if len(sys.argv) != 3:
        print("usage: check_order.py <earlier_file> <later_file>")
        sys.exit(1)

    first, second = sys.argv[1], sys.argv[2]
    t1 = os.path.getmtime(first)
    t2 = os.path.getmtime(second)

    # ASCII-вывод: M0/M1 на латинице по решению 17.
    print(f"{first}: {t1}")
    print(f"{second}: {t2}")
    if t1 < t2:
        print(f"OK: {first} is older than {second}")
    else:
        print(f"FAIL: {first} is NOT older than {second}")


if __name__ == "__main__":
    main()
