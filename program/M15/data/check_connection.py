"""Проверка базового подключения и связей (инфраструктура, step-01.md).

Сверяет program\\M15\\work\\connection_check.csv (две цифры, которые
учащийся переписал из простого визуала Tableau на пяти связанных
таблицах) с числами, посчитанными напрямую из program\\M4\\data\\csv\\
transactions.csv этим скриптом, а не с чужого эталона — при связях,
собранных неверно (например, связь 5 дала декартово произведение),
число строк или сумма разойдутся с исходным файлом, и это укажет на
связи, а не на дальнейшие меры (step-02.md проверяет то же самое через
шесть мер, здесь — упреждающая проверка на самом дешёвом месте).
"""
import csv
import sys
from pathlib import Path

# Кириллица в консоли не полагается на кодировку терминала
# (решение 17; симуляция 2026-09-04, дефект M9-1: без этой строки
# скрипт падал с UnicodeEncodeError, допечатав часть вывода).
sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent.parent
SOURCE = ROOT / "program" / "M4" / "data" / "csv" / "transactions.csv"
CHECK = Path(__file__).resolve().parent.parent / "work" / "connection_check.csv"

FAILED = False


def ok(msg: str) -> None:
    print(f"[OK]   {msg}")


def bad(msg: str) -> None:
    global FAILED
    print(f"[FAIL] {msg}")
    FAILED = True


def main() -> int:
    if not SOURCE.exists():
        bad(f"{SOURCE} не найден — прогоните program\\M4\\data\\generate_m4.py")
        return 1
    if not CHECK.exists():
        bad(f"{CHECK} не найден")
        return 1

    with SOURCE.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    true_rows = len(rows)
    true_sum = round(sum(float(r["amount_uah"]) for r in rows), 2)

    with CHECK.open(encoding="utf-8", newline="") as f:
        got = list(csv.DictReader(f))[0]

    try:
        got_rows = int(float(got["Tx Count"]))
        got_sum = float(got["Total Amount"])
    except (KeyError, ValueError) as exc:
        bad(f"connection_check.csv: не удалось прочитать 'Tx Count'/'Total Amount': {exc}")
        return 1

    if got_rows == true_rows:
        ok(f"строк в transactions: {got_rows}")
    else:
        bad(f"строк в transactions: {got_rows}, ожидалось {true_rows} — связь 5 "
            f"могла размножить строки (декартово произведение вместо составного ключа)")

    if abs(got_sum - true_sum) <= 0.005:
        ok(f"сумма amount_uah: {got_sum}")
    else:
        bad(f"сумма amount_uah: {got_sum}, ожидалось {true_sum}")

    print()
    if FAILED:
        print("НЕ СОШЛОСЬ. Шаг не закрыт.")
        print("код возврата: 1")
        return 1
    print("ВСЁ СОШЛОСЬ: расхождений 0.")
    print("код возврата: 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
