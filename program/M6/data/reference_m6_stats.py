"""Эталоны шага M6.05 «Описывает распределение и выбирает порог» (умение F4).

Пишет два CSV:

* `ref_distribution.csv` — двенадцать чисел, описывающих распределение
  суммы `completed`-операций леджера;
* `ref_thresholds.csv` — четыре правила отсечения выбросов на одной и той
  же колонке: сколько каждое нашло, сколько из найденного ложно и сколько
  реальных пропустило.

Считается стандартной библиотекой: ни `pandas`, ни `statistics.quantiles`
здесь не используются. Причина не в аскезе — в двойном авторстве (скилл
curriculum-design, раздел 1.3): решение учащегося пишется на `pandas`, и
если эталон посчитан тем же вызовом `Series.quantile`, критерий проверяет
совпадение вызова с самим собой, а не правильность расчёта.

**Определения, без которых числа ничего не значат** (решение 30):

* **база** — строки `raw/ledger.csv` со статусом `completed`, 2047 из
  2324; `failed` и `reversed` не входят никуда;
* **ключ** — колонка `amount`, гривны, два знака после точки;
* **пустые** — пустых `amount` в датасете нет (инвариант генератора);
* **дубли** — `txn_id` уникален, дедупликация не применяется;
* **сравнение** — квартиль считается **линейной интерполяцией** между
  соседними порядковыми значениями (метод по умолчанию
  `pandas.Series.quantile` и `numpy.percentile`). Другой метод — например
  «ближайший ранг» из `statistics.quantiles(method="inclusive")` — даёт
  другой Q3 и, следовательно, другой порог 1.5·IQR. Метод назван здесь и
  в разделе 1.5 шага именно потому, что от него зависит число найденных;
* **стандартное отклонение** — выборочное, делитель `n − 1`
  (`ddof=1`, значение по умолчанию `pandas.Series.std`).

«Эталонным» списком выбросов в `ref_thresholds.csv` считается результат
правила из `step-03.md` — «сумма больше 5 медиан своего счёта», 10 строк
`ref_outliers.csv`. Это не «истина природы», а решение модуля, принятое в
шаге 03 и обоснованное там же: выброс определяется относительно своей
группы. Три остальные строки таблицы меряются относительно него.

Запуск из корня репозитория:

    .venv\\Scripts\\python.exe program\\M6\\data\\reference_m6_stats.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"


def load_completed() -> list[dict[str, str]]:
    with (RAW / "ledger.csv").open(encoding="utf-8", newline="") as fh:
        return [row for row in csv.DictReader(fh) if row["status"] == "completed"]


def quantile(sorted_values: list[float], q: float) -> float:
    """Линейная интерполяция между соседними порядковыми значениями.

    Тот же метод, что `pandas.Series.quantile(q)` по умолчанию:
    позиция = q * (n - 1), значение = нижний сосед + дробная часть *
    (верхний − нижний).
    """
    n = len(sorted_values)
    if n == 0:
        raise ValueError("пустая выборка")
    if n == 1:
        return sorted_values[0]
    pos = q * (n - 1)
    low = int(pos)
    high = min(low + 1, n - 1)
    frac = pos - low
    return sorted_values[low] + frac * (sorted_values[high] - sorted_values[low])


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def stdev(values: list[float]) -> float:
    m = mean(values)
    return (sum((v - m) ** 2 for v in values) / (len(values) - 1)) ** 0.5


def main() -> int:
    rows = load_completed()
    amounts = sorted(float(r["amount"]) for r in rows)
    n = len(amounts)

    m = mean(amounts)
    med = quantile(amounts, 0.5)
    sd = stdev(amounts)
    q1 = quantile(amounts, 0.25)
    q3 = quantile(amounts, 0.75)
    iqr = q3 - q1

    distribution = [
        ("строк", f"{n}"),
        ("среднее", f"{m:.2f}"),
        ("медиана", f"{med:.2f}"),
        ("стандартное_отклонение", f"{sd:.2f}"),
        ("минимум", f"{amounts[0]:.2f}"),
        ("q1", f"{q1:.2f}"),
        ("q3", f"{q3:.2f}"),
        ("iqr", f"{iqr:.2f}"),
        ("p90", f"{quantile(amounts, 0.90):.2f}"),
        ("p95", f"{quantile(amounts, 0.95):.2f}"),
        ("p99", f"{quantile(amounts, 0.99):.2f}"),
        ("максимум", f"{amounts[-1]:.2f}"),
    ]

    # эталонный список выбросов: 5 медиан СВОЕГО счёта (правило шага 03)
    by_account: dict[str, list[float]] = {}
    for row in rows:
        by_account.setdefault(row["account_id"], []).append(float(row["amount"]))
    account_median = {
        acc: quantile(sorted(values), 0.5) for acc, values in by_account.items()
    }
    truth = {
        row["txn_id"]
        for row in rows
        if float(row["amount"]) > account_median[row["account_id"]] * 5
    }

    def measure(name: str, threshold: float | None, found: set[str]) -> list[str]:
        return [
            name,
            "—" if threshold is None else f"{threshold:.2f}",
            str(len(found)),
            str(len(found & truth)),
            str(len(found - truth)),
            str(len(truth - found)),
        ]

    def above(threshold: float) -> set[str]:
        return {r["txn_id"] for r in rows if float(r["amount"]) > threshold}

    t_median5 = 5 * med
    t_iqr = q3 + 1.5 * iqr
    t_sigma = m + 3 * sd

    thresholds = [
        measure("5x_общей_медианы", t_median5, above(t_median5)),
        measure("1.5_iqr", t_iqr, above(t_iqr)),
        measure("3_сигмы", t_sigma, above(t_sigma)),
        measure("5x_медианы_своего_счёта", None, truth),
    ]

    with (HERE / "ref_distribution.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(["показатель", "значение"])
        writer.writerows(distribution)

    with (HERE / "ref_thresholds.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(
            ["правило", "порог", "найдено", "совпало", "ложных", "пропущено"]
        )
        writer.writerows(thresholds)

    print("ref_distribution.csv:")
    for name, value in distribution:
        print(f"  {name:<24} {value}")
    print("ref_thresholds.csv:")
    for row in thresholds:
        print("  " + " | ".join(row))
    print()
    print("Эталонный список выбросов — правило step-03.md, строк:", len(truth))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
