"""Тест `compare_csv.py`: что скрипт засчитывает и что обязан отвергнуть.

Запуск как скрипта (из `program/M3/data/`):

    python test_compare_csv.py

Печатает построчный отчёт и итог. Код возврата: 0 — все случаи прошли,
1 — хотя бы один не прошёл.

Запуск через pytest (из того же каталога):

    python -m pytest test_compare_csv.py -v

Три функции `test_space_literals`, `test_values`, `test_files` — точки
входа для pytest; каждая падает через `assert`, если хоть один случай не
сошёлся, и печатает список несошедшихся случаев в сообщении ассерта.
Общая логика проверки (какие случаи и какой исход ожидается) не
дублируется между двумя режимами — оба читают одни и те же `_run_*_cases()`.

**Кириллица в тексте ассерта под pytest на Windows.** Запуск как скрипта
сам чинит кодировку консоли (`sys.stdout.reconfigure`, решение 17); текст
диагностики `pytest` в собственный терминальный вывод об упавшем assert
идёт мимо этой перенастройки и на нестандартной кодовой странице
Windows-консоли может выйти "кракозябрами" — измерено прогоном
(`research/tools-gate.md`). Проверка при этом падает верно, портится
только читаемость сообщения. Лечится запуском с явной переменной
окружения: `PYTHONIOENCODING=utf-8 python -m pytest test_compare_csv.py -v`.

Ничего не изменяет и не оставляет файлов на диске: временные CSV
создаются в системном каталоге временных файлов и удаляются.

Зачем нужен именно **негативный** тест, а не проверка «на нормальных
данных». Правка `same_value()` по находке P9 (`research/tools-gate.md`)
сделала сравнение чисел мягче: `2480,00` и `2480.00` теперь совпадают.
Всякое смягчение сравнения опасно ровно одним — оно может начать
засчитывать то, что засчитывать нельзя, и тогда критерий готовности
перестаёт ловить ошибку учащегося, не подавая никакого признака. Поэтому
половина случаев ниже — про расхождения, которые обязаны остаться
расхождениями.

Скрипт стандартной библиотеки, без POSIX-команд (решение 13
`design/decisions.md`), кодировка везде явная (решение 17).
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from compare_csv import main, normalize_number, same_value  # noqa: E402

if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

NBSP = " "
NNBSP = " "

# (описание, got, want, ожидается ли совпадение)
VALUE_CASES: list[tuple[str, str, str, bool]] = [
    # --- P9: то, ради чего правился скрипт ---
    ("десятичная запятая Power BI против точки SQL", "2480,00", "2480.00", True),
    ("десятичная запятая в обе стороны", "8600.00", "8600,00", True),
    ("разряды неразрывным пробелом плюс запятая", f"1{NBSP}234,56", "1234.56", True),
    ("разряды узким неразрывным пробелом", f"12{NNBSP}345,00", "12345.0", True),
    ("разряды обычным пробелом", "1 234,56", "1234.56", True),
    # --- P9, обратная сторона: смягчение не должно проглотить расхождение ---
    ("запятая, но число другое", "2480,00", "2490.00", False),
    ("запятая, расхождение в сотых", "2480,01", "2480.00", False),
    ("одна запятая читается как десятичная, а не как разряды",
     "1,234", "1234", False),
    ("две запятые числом не признаются", "1,234,56", "1234.56", False),
    ("запятая и точка вместе числом не признаются", "1,234.56", "1234.56", False),
    ("пробелы не склеивают разные числа", f"1{NBSP}234,56", "1234.57", False),
    # --- то, что работало до правки и обязано работать после ---
    ("точка против точки", "1200.0", "1200.0", True),
    ("хвостовой ноль не меняет число", "1200.0", "1200", True),
    ("PostgreSQL печатает два знака, SQLite один", "35.00", "35.0", True),
    ("разные числа с точкой", "1200.0", "1200.5", False),
    ("текст сравнивается как текст", "Київ", "Київ", True),
    ("разный текст", "Київ", "Одеса", False),
    ("текст с запятой не превращается в число", "Київ, UA", "Київ. UA", False),
    ("пустое против пустого", "", "", True),
    ("пустое против нуля", "", "0", False),
]

# (описание, строки «вашего» файла, строки эталона, ожидаемый код возврата)
FILE_CASES: list[tuple[str, list[str], list[str], int]] = [
    (
        "экспорт Power BI против эталона SQL: BOM, кавычки, запятая",
        ["﻿city,Total Completed", 'Київ,"2480,00"', 'Одеса,"2465,00"'],
        ["city,Total Completed", "Київ,2480.00", "Одеса,2465.00"],
        0,
    ),
    (
        "тот же экспорт, но одно число расходится",
        ["﻿city,Total Completed", 'Київ,"2480,00"', 'Одеса,"2465,00"'],
        ["city,Total Completed", "Київ,2480.00", "Одеса,2466.00"],
        1,
    ),
    (
        "заголовок не совпал",
        ["city,Total", "Київ,2480.00"],
        ["city,Total Completed", "Київ,2480.00"],
        1,
    ),
    (
        "строк меньше, чем в эталоне",
        ["city,Total Completed", "Київ,2480.00"],
        ["city,Total Completed", "Київ,2480.00", "Одеса,2465.00"],
        1,
    ),
]


def _run_space_literal_cases() -> list[tuple[bool, str]]:
    """Три пробела в `normalize_number()` обязаны быть тремя разными
    символами. Если бы кто-то при правке заменил их на три обычных
    пробела, разделитель разрядов перестал бы сниматься молча: тест на
    значениях это ловит, но не объясняет причину, а этот — объясняет."""
    results = []
    for name, value in (("неразрывный U+00A0", NBSP), ("узкий неразрывный U+202F", NNBSP)):
        got = normalize_number(f"1{value}234,56")
        ok = got == "1234.56"
        msg = f"{name} снимается" if ok else f"{name} не снят: normalize_number дал {got!r}, ждали '1234.56'"
        results.append((ok, msg))
    return results


def _run_value_cases() -> list[tuple[bool, str]]:
    results = []
    for name, got, want, expected in VALUE_CASES:
        actual = same_value(got, want)
        ok = actual == expected
        mark = "совпадение" if expected else "расхождение"
        if ok:
            msg = f"{name}: {got!r} / {want!r} — {mark}"
        else:
            msg = (
                f"{name}: {got!r} / {want!r} — ждали {mark}, "
                f"получили {'совпадение' if actual else 'расхождение'}"
            )
        results.append((ok, msg))
    return results


def _run_file_cases() -> list[tuple[bool, str]]:
    """Сквозная проверка: не функция сравнения, а сам запуск скрипта на
    двух файлах — вместе с разбором CSV, снятием BOM и кодом возврата."""
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for i, (name, mine, ref, expected) in enumerate(FILE_CASES):
            mine_path = tmp_dir / f"mine_{i}.csv"
            ref_path = tmp_dir / f"ref_{i}.csv"
            # newline="" — чтобы \r\n из строк не удваивался (решение 13,
            # тот же механизм, что описан в docstring compare_csv.py).
            mine_path.write_text("\r\n".join(mine) + "\r\n", encoding="utf-8", newline="")
            ref_path.write_text("\r\n".join(ref) + "\r\n", encoding="utf-8", newline="")

            actual = main(["compare_csv.py", str(mine_path), str(ref_path)])
            ok = actual == expected
            msg = f"{name} (ждём код {expected}) — код возврата {actual}"
            results.append((ok, msg))
    return results


def _print_results(title: str, results: list[tuple[bool, str]]) -> tuple[int, int]:
    print(title)
    passed = failed = 0
    for ok, msg in results:
        if ok:
            print(f"  [OK]   {msg}")
            passed += 1
        else:
            print(f"  [FAIL] {msg}")
            failed += 1
    return passed, failed


def test_space_literals() -> None:
    """pytest-точка входа — собирается благодаря префиксу `test_`."""
    failed = [msg for ok, msg in _run_space_literal_cases() if not ok]
    assert not failed, "; ".join(failed)


def test_values() -> None:
    failed = [msg for ok, msg in _run_value_cases() if not ok]
    assert not failed, "; ".join(failed)


def test_files() -> None:
    failed = [msg for ok, msg in _run_file_cases() if not ok]
    assert not failed, "; ".join(failed)


def main_test() -> int:
    """Запуск как скрипта: печатает построчный отчёт, как раньше."""
    total_passed = total_failed = 0
    for title, results in (
        ("Пробелы-разделители разрядов:", _run_space_literal_cases()),
        ("Сравнение значений (same_value):", _run_value_cases()),
        ("Сквозной запуск (main на двух файлах):", _run_file_cases()),
    ):
        p, f = _print_results(title, results)
        total_passed += p
        total_failed += f
        print()

    print(f"Итого: {total_passed} прошло, {total_failed} не прошло.")
    return 1 if total_failed else 0


if __name__ == "__main__":
    sys.exit(main_test())
