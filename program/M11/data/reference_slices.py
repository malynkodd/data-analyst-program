"""Эталон вторых задач шагов M11.01–M11.03: те же метрики на срезах.

Восемь метрик модуля посчитаны на портфеле целиком (`reference_m11.py`).
Этот скрипт считает часть из них **в разрезе**. Разрез нужен не для
разнообразия: сводное число почти никогда не является ответом на рабочий
вопрос, и до разреза нельзя сказать, скрывает оно что-нибудь или нет.

Прогон на машине автора 2026-08-28 дал два результата, и оба важны
именно тем, какие они получились:

* **FPD по размеру займа практически не различается** — 0.2250 / 0.2099
  / 0.2236 на трёх терцилях. Разрез не нашёл ничего, и это законный
  результат, а не неудача: он снимает гипотезу «крупные займы
  просрочивают чаще», которую иначе пришлось бы носить в голове как
  правдоподобную. FPD30 слегка ниже на крупных займах (0.0478 против
  0.0591), но n = 711 на корзину — этого мало, чтобы называть разницу
  установленной.
* **Approval rate по скоринговому баллу — не плавная кривая, а
  ступенька**: 0.0000 ниже 600 баллов и 0.9955–1.0000 выше. То есть
  сводные 68% по портфелю не описывают решение модели вообще — они
  описывают состав входящих заявок. Модель здесь — порог, и «approval
  rate упал» в такой системе означает «изменился поток заявок» либо
  «сдвинули порог», а не «модель стала строже понемногу».

Срезы выбраны из того, что в датасете есть, а не из того, что красиво
звучит. Канала привлечения в `raw/` нет — вся выдача идёт одним потоком,
и `marketing_spend.csv` содержит одну строку на весь период; срок займа
у всех 2132 займов одинаков (14 дней). Остаются два настоящих среза:

* **размер займа** (`principal`) — три корзины по терцилям выданных сумм;
* **скоринговый балл** (`score`) — четыре корзины по 100 баллов, только
  для approval rate, потому что балл есть у заявки, а не у займа.

**Определения** (те же, что в `reference_m11.py`, решение 30):

* заём считается просроченным, если `resolution_days != 0`; пустое
  `resolution_days` (никогда не погашен) — худший случай, входит в
  числитель любой метрики просрочки;
* зрелость для roll rate — `due_date + 60 <= CUTOFF`, `CUTOFF =
  2026-08-01`;
* границы корзин по `principal` — терцили распределения выданных сумм,
  посчитанные линейной интерполяцией и округлённые до целых гривен вниз;
  границы напечатаны и вписаны в шаг, чтобы срез воспроизводился без
  этого скрипта.

Запуск из каталога `program\\M11\\data`:

    ..\\..\\..\\.venv\\Scripts\\python.exe reference_slices.py
"""

from __future__ import annotations

import csv
import datetime as dt
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
CUTOFF = dt.date(2026, 8, 1)


def read_loans() -> list[dict]:
    with (HERE / "raw" / "loans.csv").open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for row in rows:
        row["principal"] = float(row["principal"])
        row["due"] = dt.date.fromisoformat(row["due_date"])
        raw = row["resolution_days"]
        row["res"] = None if raw == "" else int(raw)
        row["age_days"] = (CUTOFF - row["due"]).days
    return rows


def read_applications() -> list[dict]:
    with (HERE / "raw" / "applications.csv").open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for row in rows:
        row["score"] = int(row["score"])
        row["approved"] = row["approved"] == "True"
    return rows


def quantile(sorted_values: list[float], q: float) -> float:
    """Линейная интерполяция — тот же метод, что в M6/step-05.md."""
    if not sorted_values:
        raise ValueError("пустая выборка")
    position = (len(sorted_values) - 1) * q
    low = int(position)
    high = min(low + 1, len(sorted_values) - 1)
    frac = position - low
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * frac


def is_overdue(loan: dict, days: int) -> bool:
    """Просрочен строго больше `days` дней; непогашенный — худший случай."""
    if loan["res"] is None:
        return True
    return loan["res"] > days


def main() -> int:
    loans = read_loans()
    apps = read_applications()

    principals = sorted(loan["principal"] for loan in loans)
    t1 = int(quantile(principals, 1 / 3))
    t2 = int(quantile(principals, 2 / 3))

    def bucket(loan: dict) -> str:
        if loan["principal"] <= t1:
            return f"principal_do_{t1}"
        if loan["principal"] <= t2:
            return f"principal_{t1 + 1}_{t2}"
        return f"principal_ot_{t2 + 1}"

    order = [f"principal_do_{t1}", f"principal_{t1 + 1}_{t2}", f"principal_ot_{t2 + 1}"]

    rows: list[tuple[str, str, str, str]] = []

    for name in order:
        group = [loan for loan in loans if bucket(loan) == name]
        fpd = sum(1 for loan in group if is_overdue(loan, 0)) / len(group)
        fpd30 = sum(1 for loan in group if is_overdue(loan, 29)) / len(group)
        rows.append((name, "fpd", f"{fpd:.4f}", str(len(group))))
        rows.append((name, "fpd30", f"{fpd30:.4f}", str(len(group))))

    for name in order:
        mature = [
            loan
            for loan in loans
            if bucket(loan) == name and loan["age_days"] >= 60
        ]
        in_30 = [loan for loan in mature if is_overdue(loan, 30)]
        still_60 = [loan for loan in in_30 if is_overdue(loan, 60)]
        value = f"{len(still_60) / len(in_30):.4f}" if in_30 else ""
        rows.append((name, "roll_rate_30_60", value, str(len(in_30))))

    score_edges = [(0, 499), (500, 599), (600, 699), (700, 10_000)]
    for low, high in score_edges:
        group = [a for a in apps if low <= a["score"] <= high]
        label = f"score_{low}_{high}" if high < 10_000 else f"score_{low}_plus"
        rate = sum(1 for a in group if a["approved"]) / len(group)
        rows.append((label, "approval_rate", f"{rate:.4f}", str(len(group))))

    with (HERE / "ref_slices.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(["срез", "метрика", "значение", "n"])
        writer.writerows(rows)

    print(f"Терцили principal: t1 = {t1}, t2 = {t2}")
    print(f"Строк в ref_slices.csv: {len(rows)}")
    print()
    for row in rows:
        print(f"  {row[0]:<26} {row[1]:<16} {row[2]:>8}  n={row[3]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
