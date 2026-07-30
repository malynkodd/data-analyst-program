"""
Проверяет текстовый файл, созданный учащимся: декодируется ли он как
UTF-8 без ошибок, сколько в нём непустых строк и есть ли хотя бы один
символ не из ASCII (то есть кириллица или другой не-латинский текст
сохранился, а не превратился в "кракозябры" из-за неверной кодировки
сохранения).

Печатает только статус и числа, не содержимое файла — см. довод про
ASCII-вывод в program/M1/data/count_active.py: содержимое файла может
быть кириллицей, а сам статус-вывод должен остаться читаемым в любой
консоли.

Пример:
  python3 check_utf8.py notes.md
"""

import argparse
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--min-lines", type=int, default=1)
    args = ap.parse_args()

    try:
        with open(args.path, encoding="utf-8", errors="strict") as f:
            text = f.read()
    except UnicodeDecodeError as e:
        print(f"FAIL: file is not valid UTF-8 ({e})")
        sys.exit(1)

    lines = [ln for ln in text.splitlines() if ln.strip()]
    has_non_ascii = any(ord(ch) > 127 for ch in text)

    print(f"decoded as UTF-8: yes")
    print(f"non-empty lines: {len(lines)}")
    print(f"contains non-ASCII characters: {has_non_ascii}")

    if len(lines) >= args.min_lines:
        print("OK")
    else:
        print(f"FAIL: fewer than {args.min_lines} non-empty lines")
        sys.exit(1)


if __name__ == "__main__":
    main()
