"""Сверка вывода вашего запроса с эталонным CSV модуля M3.

Запуск:

    python compare_csv.py <ваш_вывод.csv> <эталон.csv>

Например:

    python compare_csv.py my_task1.csv a1_task1_running_total.csv

Печатает либо «СОВПАДАЕТ», либо первое расхождение с номером строки и
колонки. Код возврата: 0 при совпадении, 1 при расхождении или ошибке.
Ничего не изменяет — только читает оба файла.

Зачем нужен отдельный скрипт, а не сравнение файлов глазами или
средствами шелла (решение 13 `design/decisions.md`): консольный клиент
`sqlite3` пишет CSV не байт-в-байт так, как выглядит эталон в
репозитории, и оба расхождения безобидны по смыслу, но ломают любое
побайтовое сравнение. Проверено прогоном на клиенте 3.53.4:

1. **Кавычки.** В режиме `.mode csv` клиент берёт в двойные кавычки
   любое «непростое» значение — не только то, где есть запятая, но и
   любое с пробелом или кириллицей. `SELECT 'Київ'` даёт `"Київ"`,
   `SELECT 'has space'` даёт `"has space"`. В эталоне
   `a1_task4_city_cumulative.csv` города записаны без кавычек. Значение
   при этом одно и то же — по правилам CSV кавычки не часть значения.
2. **Перевод строки.** `.once <файл>` пишет `\r\n`. Тот же вывод,
   отправленный в файл перенаправлением (`> файл.csv`), даёт `\r\r\n`:
   клиент пишет свой `\r\n`, а стандартный вывод Windows превращает `\n`
   в `\r\n` поверх этого. Отсюда правило шага: выводить через `.once`, а
   не через перенаправление.

Скрипт сравнивает **значения**, разобранные по правилам CSV, а не байты,
поэтому оба пункта выше на результат не влияют. Числа сравниваются как
числа: `1200.0` и `1200` — совпадение, `1200.0` и `1200.5` — нет.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def read_csv(path: Path) -> list[list[str]]:
    # encoding назван явно (решение 17): utf-8-sig снимает BOM, если файл
    # его содержит, и ничего не меняет, если нет.
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [[c.strip() for c in row] for row in csv.reader(f) if row]


def same_value(got: str, want: str) -> bool:
    if got == want:
        return True
    try:
        return abs(float(got) - float(want)) < 1e-9
    except ValueError:
        return False


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Использование: python compare_csv.py <ваш_вывод.csv> <эталон.csv>")
        return 1

    mine_path, ref_path = Path(argv[1]), Path(argv[2])
    for p in (mine_path, ref_path):
        if not p.exists():
            print(f"РАСХОЖДЕНИЕ: файл {p} не найден")
            return 1

    mine, ref = read_csv(mine_path), read_csv(ref_path)

    if not mine:
        print(f"РАСХОЖДЕНИЕ: {mine_path} пуст. Если запрос выполнялся, но файл "
              f"пустой — скорее всего, не был выполнен '.headers on' или '.once'")
        return 1
    if not ref:
        print(f"РАСХОЖДЕНИЕ: эталон {ref_path} пуст")
        return 1

    if mine[0] != ref[0]:
        print(f"РАСХОЖДЕНИЕ в заголовке.")
        print(f"  у вас:  {','.join(mine[0])}")
        print(f"  эталон: {','.join(ref[0])}")
        print("Колонки должны совпадать по именам и порядку — проверьте "
              "список после SELECT и псевдонимы AS.")
        return 1

    mine_rows, ref_rows = mine[1:], ref[1:]
    if len(mine_rows) != len(ref_rows):
        print(f"РАСХОЖДЕНИЕ в числе строк: у вас {len(mine_rows)}, "
              f"в эталоне {len(ref_rows)}.")
        print("Число строк расходится до сравнения значений — причина в "
              "условии отбора или в соединении таблиц, а не в вычислениях.")
        return 1

    header = mine[0]
    for i, (got_row, want_row) in enumerate(zip(mine_rows, ref_rows), start=1):
        for j, (got, want) in enumerate(zip(got_row, want_row)):
            if not same_value(got, want):
                col = header[j] if j < len(header) else f"колонка {j + 1}"
                print(f"РАСХОЖДЕНИЕ в строке {i}, колонка '{col}': "
                      f"у вас {got!r}, в эталоне {want!r}")
                print(f"  ваша строка:   {','.join(got_row)}")
                print(f"  строка эталона: {','.join(want_row)}")
                return 1

    print(f"СОВПАДАЕТ: {len(ref_rows)} строк, {len(header)} колонок, "
          f"расхождение 0.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
