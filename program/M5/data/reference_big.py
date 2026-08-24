"""Эталон шага M5.09 «Файл, который не помещается в память» (умение B7).

Пишет `ref_big_month.csv` — выручку по месяцам среди выплат со статусом
`PAID` в `raw/payouts_big.csv` (1 800 000 строк, 352 087 679 байт).

Считается **стандартной библиотекой**, потоково: `csv.reader`, один
проход, словарь-накопитель. `pandas` здесь не импортируется — и это не
только правило двойного авторства (скилл curriculum-design, раздел 1.3),
но и вторая половина предмета шага: тот же результат получается вообще
без DataFrame, при пике памяти в единицы мегабайт.

**Определения** (решение 30): база — все строки файла со `status` ровно
`PAID`; месяц — первые 7 символов `payout_date` (`ГГГГ-ММ`); сумма
округляется один раз, в конце, до второго знака; дубли не снимаются
(`payout_id` уникален по конструкции генератора).

Запуск из корня репозитория (около 6 с на машине автора):

    .venv\\Scripts\\python.exe program\\M5\\data\\reference_big.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
SRC = HERE / "raw" / "payouts_big.csv"
OUT = HERE / "ref_big_month.csv"


def main() -> int:
    if not SRC.exists():
        print(f"нет файла {SRC} — запустите generate_big.py")
        return 1

    totals: dict[str, float] = {}
    rows = 0
    with SRC.open(encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        i_date = header.index("payout_date")
        i_amount = header.index("amount")
        i_status = header.index("status")
        for row in reader:
            rows += 1
            if row[i_status] != "PAID":
                continue
            month = row[i_date][:7]
            totals[month] = totals.get(month, 0.0) + float(row[i_amount])

    with OUT.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(["month", "paid_revenue"])
        for month in sorted(totals):
            writer.writerow([month, f"{totals[month]:.2f}"])

    print("строк прочитано:", rows)
    print("месяцев:", len(totals))
    for month in sorted(totals):
        print(f"  {month}  {totals[month]:.2f}")
    print(f"итого PAID: {sum(totals.values()):.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
