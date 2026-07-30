"""
Проверяет не файл, а терминал: показывает ли он кириллицу так, как её
видит Python, а не как "?????" или пустые квадраты. check_utf8.py
проверяет байты файла на диске (это другая вещь) — часть Windows-
терминалов (старый cmd.exe без chcp 65001) выводит на экран байты
через свою кодовую страницу (cp866/cp1251) вместо UTF-8, даже когда
файл и код Python полностью корректны (design/decisions.md, решение 17).

Пример:
  python3 check_console.py
"""

import sys

if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

REFERENCE = "Проверка кодировки: яжщч, ґєіїу, №12345"


def main():
    print(REFERENCE)


if __name__ == "__main__":
    main()
