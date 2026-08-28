"""Эталон шага M9.01 «Аппарат, которым меряются ловушки» (умение F5).

Считает двадцать четыре величины и пишет `ref_apparatus.csv`. Всё — на
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
  исключения выбросов;
* **хи-квадрат** — Пирсона по таблице 2×2 того же A/B-теста
  (сконвертировал / не сконвертировал × A / B), без поправки Йейтса.
  Ожидаемые частоты берутся из маргиналов: `E = строка · столбец / N`.
  Порог не берётся из таблицы: при одной степени свободы χ² — это ровно
  квадрат стандартной нормальной величины, поэтому критическое значение
  равно `z_crit²` (`1.9600² = 3.8415`). Скрипт печатает обе величины
  рядом именно затем, чтобы происхождение порога было видно, а не
  заучено;
* **t-критерий** — для двух независимых средних (`means_apparatus.csv`,
  по 20 наблюдений на группу), объединённая дисперсия (pooled), df =
  n_A + n_B − 2 = 38. Критическое значение t для df = 38 при α = 0.05
  двусторонней — **2.0244**; в стандартной библиотеке функции
  распределения Стьюдента нет, поэтому порог берётся из таблицы
  квантилей и записан в эталон явно, а не вычисляется. Это единственное
  число шага, взятое не вызовом, — и потому названо здесь.

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


T_CRIT_DF38 = 2.0244  # квантиль t(38) для двустороннего α = 0.05, из таблицы


def load_means() -> tuple[list[float], list[float]]:
    with (HERE / "means_apparatus.csv").open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    return (
        [float(r["check_uah"]) for r in rows if r["variant"] == "A"],
        [float(r["check_uah"]) for r in rows if r["variant"] == "B"],
    )


def chi_square_2x2(cA: int, nA: int, cB: int, nB: int) -> float:
    """Хи-квадрат Пирсона по таблице 2×2, без поправки Йейтса."""
    observed = [
        [cA, nA - cA],
        [cB, nB - cB],
    ]
    total = nA + nB
    col_conv = cA + cB
    col_not = total - col_conv
    expected = [
        [nA * col_conv / total, nA * col_not / total],
        [nB * col_conv / total, nB * col_not / total],
    ]
    return sum(
        (observed[i][j] - expected[i][j]) ** 2 / expected[i][j]
        for i in range(2)
        for j in range(2)
    )


def t_two_means(a: list[float], b: list[float]) -> tuple[float, int, float, float]:
    """t на объединённой дисперсии, df, средние двух групп."""
    na, nb = len(a), len(b)
    ma, mb = sum(a) / na, sum(b) / nb
    ssa = sum((x - ma) ** 2 for x in a)
    ssb = sum((x - mb) ** 2 for x in b)
    df = na + nb - 2
    s_pooled_sq = (ssa + ssb) / df
    se = (s_pooled_sq * (1 / na + 1 / nb)) ** 0.5
    return (mb - ma) / se, df, ma, mb


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

    chi2 = chi_square_2x2(cA, nA, cB, nB)
    chi2_crit = z_crit ** 2

    checks_a, checks_b = load_means()
    t_stat, df, mean_a, mean_b = t_two_means(checks_a, checks_b)

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
        ("хи_квадрат", f"{chi2:.4f}"),
        ("хи_квадрат_порог_df1", f"{chi2_crit:.4f}"),
        ("хи_квадрат_равен_z_в_квадрате", f"{z ** 2:.4f}"),
        ("средний_чек_A", f"{mean_a:.2f}"),
        ("средний_чек_B", f"{mean_b:.2f}"),
        ("t_статистика", f"{t_stat:.4f}"),
        ("t_степеней_свободы", f"{df}"),
        ("t_порог_двусторонний", f"{T_CRIT_DF38:.4f}"),
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
