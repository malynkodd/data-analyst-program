"""Эталоны шага M2.09 «Диаграмма под вопрос» (умение D4).

Пишет три файла:

* `ref_charts.csv` — соответствие «тип аналитического вопроса → форма
  диаграммы» для шести вопросов шага. Это эталон выбора формы, а не
  данных;
* `ref_chart_quarter.csv` — выручка по восьми кварталам (данные под
  диаграмму Q1);
* `ref_chart_channel_share.csv` — выручка и доля каждого канала внутри
  каждого квартала (данные под диаграмму Q6), 24 строки.

Правила очистки берутся из `build_reference.py` — того же скрипта, что
считает контрольные суммы всех остальных шагов M2. Второй копии правил
не заводится: она разошлась бы с первой при первой же правке.

**Определения** (решение 30): база — все 20 000 строк
`sales_extract_raw.csv`; сумма — `amount_raw`, очищенная по правилам
`step-01.md`, вместе с возвратами (отрицательными суммами), потому что
вопрос заказчика — про выручку, а не про валовые продажи; ключ квартала —
дата заказа после разбора обоих форматов; дубли не снимаются (`order_id`
уникален); доля канала считается внутри квартала и в сумме по кварталу
даёт 100.00 с точностью до второго знака.

Запуск (из каталога скрипта, как и `build_reference.py`):

    cd program\\M2\\data
    ..\\..\\..\\.venv\\Scripts\\python.exe reference_charts.py
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

from build_reference import parse_amount, parse_date, quarter_label

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent

# Эталон выбора формы. Шесть типов аналитического вопроса — по одному
# на каждый. Формы названы так же, как их называет интерфейс Excel и
# Google Sheets, чтобы ответ учащегося сверялся строкой, а не смыслом.
CHARTS = [
    (
        "Q1",
        "динамика во времени",
        "линия",
        "точек много и они упорядочены по времени; линия показывает "
        "направление, столбцы на 8 точках читаются как сравнение",
    ),
    (
        "Q2",
        "сравнение категорий",
        "столбцы",
        "три несопоставимых по времени группы; длина столбца сравнивается "
        "глазом точнее, чем угол сектора",
    ),
    (
        "Q3",
        "ранжирование",
        "горизонтальные столбцы",
        "десять подписей не помещаются под вертикальными столбцами; "
        "сортировка по убыванию делает порядок частью ответа",
    ),
    (
        "Q4",
        "распределение",
        "гистограмма",
        "вопрос про форму и разброс одной числовой колонки, а не про "
        "сравнение групп",
    ),
    (
        "Q5",
        "связь двух величин",
        "точечная",
        "две числовые величины у одного объекта; точка на объект "
        "показывает и связь, и выбросы из неё",
    ),
    (
        "Q6",
        "состав целого во времени",
        "стопка 100%",
        "вопрос про доли, а не про уровни; стопка 100% удерживает сумму "
        "постоянной и делает изменение долей видимым",
    ),
]

FORBIDDEN = ["3D", "объёмная", "круговая", "пончик", "кольцевая", "двойная ось"]


def load_rows() -> list[dict[str, str]]:
    with (HERE / "sales_extract_raw.csv").open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def main() -> int:
    rows = load_rows()

    by_quarter: dict[str, float] = defaultdict(float)
    by_quarter_channel: dict[tuple[str, str], float] = defaultdict(float)
    for row in rows:
        quarter = quarter_label(parse_date(row["order_date_raw"]))
        amount = parse_amount(row["amount_raw"])
        by_quarter[quarter] += amount
        by_quarter_channel[(quarter, row["channel"])] += amount

    with (HERE / "ref_charts.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(["id", "тип_вопроса", "форма", "почему_эта_форма"])
        writer.writerows(CHARTS)

    with (HERE / "ref_chart_quarter.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(["quarter", "revenue"])
        for quarter in sorted(by_quarter):
            writer.writerow([quarter, f"{by_quarter[quarter]:.2f}"])

    channels = sorted({channel for _, channel in by_quarter_channel})
    with (HERE / "ref_chart_channel_share.csv").open(
        "w", encoding="utf-8", newline=""
    ) as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(["quarter", "channel", "revenue", "share_pct"])
        for quarter in sorted(by_quarter):
            total = by_quarter[quarter]
            for channel in channels:
                value = by_quarter_channel[(quarter, channel)]
                writer.writerow(
                    [quarter, channel, f"{value:.2f}", f"{value / total * 100:.2f}"]
                )

    print("ref_charts.csv:", len(CHARTS), "строк")
    for row in CHARTS:
        print(f"  {row[0]}  {row[1]:<26} -> {row[2]}")
    print()
    print("ref_chart_quarter.csv:")
    for quarter in sorted(by_quarter):
        print(f"  {quarter}  {by_quarter[quarter]:>15.2f}")
    print()
    print("ref_chart_channel_share.csv (доли внутри квартала, %):")
    for quarter in sorted(by_quarter):
        total = by_quarter[quarter]
        parts = "  ".join(
            f"{channel}={by_quarter_channel[(quarter, channel)] / total * 100:.2f}"
            for channel in channels
        )
        print(f"  {quarter}  {parts}")
    print()
    print("запрещённые формы:", ", ".join(FORBIDDEN))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
