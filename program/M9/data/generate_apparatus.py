"""Генератор двух микро-датасетов шага M9.01 (умение F5).

Оба файла крошечные и лежат в git как есть — генератор нужен не для
экономии места, а для воспроизводимости: `pairs_apparatus.csv` подобран
так, чтобы коэффициент корреляции был около 0.62, то есть ровно то
число, которое в ловушке D31 (`step-05.md`) даётся готовым и объявляется
«значит, реклама работает». Здесь оно считается своими руками, и рядом
считается r² = 0.38 — доля разброса, которую связь объясняет.

* `ab_apparatus.csv` — результат A/B-теста платёжной формы: две строки,
  число пользователей и число оплативших в каждой группе. Числа выбраны
  так, что относительная разница велика (+17.8%), а статистической
  значимости нет: это и есть предмет шага.
* `pairs_apparatus.csv` — 20 месяцев: расходы на рекламу и число заявок.
* `means_apparatus.csv` — средний чек 40 оплат того же A/B-теста, по 20
  в каждой группе. Нужен для t-критерия: доли сравниваются z, средние —
  t, и это две разные проверки, а не одна с разными названиями.

Детерминирован — `SEED` фиксирован до первого обращения к `random`.

Запуск из корня репозитория:

    .venv\\Scripts\\python.exe program\\M9\\data\\generate_apparatus.py
"""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

SEED = 508
random.seed(SEED)

HERE = Path(__file__).resolve().parent

# A/B: числа зафиксированы вручную, а не разыграны — от них зависит
# каждое число раздела 1.3, и случайность здесь только помешала бы.
AB_ROWS = [
    ("A", 2400, 98),
    ("B", 2350, 113),
]


def main() -> int:
    with (HERE / "ab_apparatus.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(["variant", "users", "converted"])
        writer.writerows(AB_ROWS)

    xs = [round(random.uniform(40, 260), 1) for _ in range(20)]
    ys = [int(round(120 + 1.6 * x + random.gauss(0, 130))) for x in xs]
    with (HERE / "pairs_apparatus.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(["month", "ad_spend_kuah", "leads"])
        for index, (x, y) in enumerate(zip(xs, ys)):
            month = f"{2025 + index // 12}-{index % 12 + 1:02d}"
            writer.writerow([month, x, y])

    # Средние чеки: группа B в среднем выше на ~90 грн при разбросе ~360 —
    # эффект есть, но выборок по 20 наблюдений на него мало. Розыгрыш стоит
    # ПОСЛЕ pairs_apparatus.csv намеренно: вставленный раньше, он сдвинул бы
    # поток random и изменил r, на котором стоят числа раздела 1.3.
    checks_a = [round(random.gauss(1180, 360), 2) for _ in range(20)]
    checks_b = [round(random.gauss(1270, 360), 2) for _ in range(20)]
    with (HERE / "means_apparatus.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator='\n')
        writer.writerow(["variant", "check_uah"])
        for value in checks_a:
            writer.writerow(["A", value])
        for value in checks_b:
            writer.writerow(["B", value])

    print("SEED =", SEED)
    print("ab_apparatus.csv:", len(AB_ROWS), "строки")
    for row in AB_ROWS:
        print(f"  {row[0]}  users={row[1]}  converted={row[2]}")
    print("means_apparatus.csv:", len(checks_a) + len(checks_b), "строк")
    print("  A:", checks_a)
    print("  B:", checks_b)
    print("pairs_apparatus.csv:", len(xs), "строк")
    print("  ad_spend_kuah:", xs)
    print("  leads:", ys)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
