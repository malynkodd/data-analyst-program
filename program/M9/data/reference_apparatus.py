"""Эталон шага M9.01 «Аппарат, которым меряются ловушки» (умение F5).

Считает шестнадцать величин и пишет `ref_apparatus.csv`. Всё — на
стандартной библиотеке: `statistics.NormalDist` даёт и функцию
распределения (`cdf`), и обратную к ней (`inv_cdf`), поэтому ни `scipy`,
ни `numpy` модулю не нужны и в окружение не добавляются.

Формулы записаны развёрнуто, без `statistics.correlation` и
`statistics.linear_regression`, — не из принципа, а по правилу двойного
авторства (скилл curriculum-design, раздел 1.3): решение учащегося эти
готовые функции использовать может, и тогда эталон обязан быть посчитан
не ими.

**Определения** (решение 30):

* **база A/B** — две строки `ab_apparatus.csv`; пользователь считается
  один раз, повторных визитов в данных нет;
* **доля** `p = converted / users`, стандартная ошибка доли
  `SE = sqrt(p(1−p)/n)` — формула для одной доли;
* **интервал** — двусторонний 95%, множитель `z = 1.9600` (это
  `NormalDist().inv_cdf(0.975)`, а не 2 и не 1.96 «по памяти»);
* **z для двух долей** считается на **объединённой** доле
  `p_pool = (c_A + c_B) / (n_A + n_B)`: нулевая гипотеза говорит, что
  доля одна, значит и дисперсия под ней одна. Интервал **разницы**
  считается на раздельных долях — там нулевая гипотеза уже не
  предполагается;
* **p-value** — двустороннее, `2 · (1 − Φ(|z|))`;
* **размер выборки** — на одну группу, при α = 0.05 (двусторонняя),
  мощности 0.80 и минимально различимом эффекте 1 процентный пункт от
  базовой конверсии группы A;
* **корреляция** — Пирсона, по 20 парам `pairs_apparatus.csv`, без
  исключения выбросов.

Запуск из корня репозитория:

    .venv\\Scripts\\python.exe program\\M9\\data\\reference_apparatus.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from statistics import NormalDist

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent

ALPHA = 0.05
POWER = 0.80
MDE = 0.01  # один процентный пункт


def load_ab() -> dict[str, tuple[int, int]]:
    with (HERE / "ab_apparatus.csv").open(encoding="utf-8", newline="") as fh:
        return {
            row["variant"]: (int(row["users"]), int(row["converted"]))
            for row in csv.DictReader(fh)
        }


def load_pairs() -> tuple[list[float], list[float]]:
    with (HERE / "pairs_apparatus.csv").open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    return (
        [float(r["ad_spend_kuah"]) for r in rows],
        [float(r["leads"]) for r in rows],
    )


def se_proportion(p: float, n: int) -> float:
    return (p * (1 - p) / n) ** 0.5


def pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sx = sum((x - mx) ** 2 for x in xs) ** 0.5
    sy = sum((y - my) ** 2 for y in ys) ** 0.5
    return cov / (sx * sy)


def main() -> int:
    ab = load_ab()
    nA, cA = ab["A"]
    nB, cB = ab["B"]

    normal = NormalDist()
    z_crit = normal.inv_cdf(1 - ALPHA / 2)
    z_power = normal.inv_cdf(POWER)

    pA, pB = cA / nA, cB / nB
    seA, seB = se_proportion(pA, nA), se_proportion(pB, nB)

    diff = pB - pA
    se_diff = (pA * (1 - pA) / nA + pB * (1 - pB) / nB) ** 0.5

    p_pool = (cA + cB) / (nA + nB)
    se_pool = (p_pool * (1 - p_pool) * (1 / nA + 1 / nB)) ** 0.5
    z = diff / se_pool
    p_value = 2 * (1 - normal.cdf(abs(z)))

    p1, p2 = pA, pA + MDE
    p_bar = (p1 + p2) / 2
    numerator = (
        z_crit * (2 * p_bar * (1 - p_bar)) ** 0.5
        + z_power * (p1 * (1 - p1) + p2 * (1 - p2)) ** 0.5
    ) ** 2
    n_needed = numerator / (p2 - p1) ** 2

    xs, ys = load_pairs()
    r = pearson(xs, ys)

    values = [
        ("z_для_95_процентов", f"{z_crit:.4f}"),
        ("доля_A", f"{pA:.6f}"),
        ("доля_B", f"{pB:.6f}"),
        ("se_доли_A", f"{seA:.6f}"),
        ("se_доли_B", f"{seB:.6f}"),
        ("ci95_A_низ", f"{pA - z_crit * seA:.6f}"),
        ("ci95_A_верх", f"{pA + z_crit * seA:.6f}"),
        ("ci95_B_низ", f"{pB - z_crit * seB:.6f}"),
        ("ci95_B_верх", f"{pB + z_crit * seB:.6f}"),
        ("разница_долей", f"{diff:.6f}"),
        ("se_разницы", f"{se_diff:.6f}"),
        ("ci95_разницы_низ", f"{diff - z_crit * se_diff:.6f}"),
        ("ci95_разницы_верх", f"{diff + z_crit * se_diff:.6f}"),
        ("z_статистика", f"{z:.4f}"),
        ("p_value", f"{p_value:.4f}"),
        ("нужный_размер_группы", f"{int(-(-n_needed // 1))}"),
        ("корреляция_r", f"{r:.4f}"),
        ("r_квадрат", f"{r * r:.4f}"),
    ]

    with (HERE / "ref_apparatus.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(["показатель", "значение"])
        writer.writerows(values)

    for name, value in values:
        print(f"  {name:<24} {value}")
    print()
    print(
        "Читается так: относительная разница "
        f"{(pB / pA - 1) * 100:.1f}%, p-value {p_value:.4f}, "
        "интервал разницы накрывает ноль, "
        f"нужный размер группы {int(-(-n_needed // 1))} против фактических {nA}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
