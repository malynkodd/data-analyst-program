"""Выходной набор F2 — 10 вопросов для `step-06.md`, часть 2.

Открытая половина набора: здесь только условия задач. Разобранные
ответы и ключевые числа лежат отдельно, за турникетом
(`exam_key.md.enc`, `tools/vault.py`), и открываются после того, как
ваши ответы записаны в `work\exam_answers.md`.

Вопросы не совпадают ни с одной из 40 ловушек шагов 01-04: другие
числа и другой сценарий там, где механизм повторяется.

SEED фиксирован до первого обращения к random: у вас и у ключа числа
одинаковые.
"""

import random
import statistics
import sys
from math import sqrt, comb

sys.stdout.reconfigure(encoding="utf-8")

SEED = 20260827


def q1_small_numbers():
    random.seed(SEED)
    return ("8 показов рекламного креатива дали 6 кликов из ожидаемых 50%. "
            "Креатив работает значимо лучше среднего?")


def q2_survivorship():
    random.seed(SEED + 1)
    n = 20
    roi = [random.gauss(0.05, 0.30) for _ in range(n)]
    survived = [r for r in roi if r > -0.12]
    return (f"Средний ROI {len(survived)} действующих стартапов акселератора — "
            f"{statistics.mean(survived):.1%}. Это средняя доходность когорты "
            f"акселератора?")


def q3_base_rate():
    return ("Скоринговая модель ловит 95% реальных мошенников, но ложно "
            "помечает 10% честных клиентов. Мошенники — 0.5% клиентской базы. "
            "Клиент помечен моделью — какова вероятность, что он реально "
            "мошенник?")


def q4_multiple_comparisons():
    random.seed(SEED + 2)
    for _ in range(15):
        a = [random.gauss(50, 10) for _ in range(25)]
        b = [random.gauss(50, 10) for _ in range(25)]
        statistics.mean(b) - statistics.mean(a)
    return ("Проверили 15 независимых сегментов без реального эффекта ни в "
            "одном. Сколько из них в среднем покажут ложную значимость на "
            "уровне p<0.05?")


def q5_confounding():
    random.seed(SEED + 3)
    n = 30
    hours_daylight = [random.uniform(9, 15) for _ in range(n)]
    ice_cream = [20 + 4*h + random.gauss(0, 8) for h in hours_daylight]
    sunscreen = [5 + 1.5*h + random.gauss(0, 4) for h in hours_daylight]
    mx, my = statistics.mean(ice_cream), statistics.mean(sunscreen)
    cov = sum((x-mx)*(y-my) for x, y in zip(ice_cream, sunscreen)) / n
    r = cov / (statistics.pstdev(ice_cream) * statistics.pstdev(sunscreen))
    return (f"Продажи мороженого коррелируют с продажами солнцезащитного крема "
            f"(r={r:.2f}). Стоит продавать их одним комплектом ради взаимного "
            f"продвижения, основываясь на этой связи как на причинной?")


def q6_denominator():
    m1 = (150, 5000)
    m2 = (160, 4000)
    r1, r2 = m1[0]/m1[1], m2[0]/m2[1]
    return (f"Доля возвратов выросла с {r1:.1%} до {r2:.1%}. Качество товара "
            f"ухудшилось?")


def q7_effect_size():
    n = 200000
    pa, pb = 0.050, 0.052
    se = sqrt(pa*(1-pa)/n + pb*(1-pb)/n)
    z = (pb-pa)/se
    return (f"На выборке {n}+{n} тест дал z={z:.1f} (значимо), разница долей "
            f"{pb-pa:.1%}. Внедрять изменение немедленно?")


def q8_weighted_average():
    a = (4.5, 800)
    b = (2.9, 40)
    simple = (a[0]+b[0])/2
    return (f"Магазин A — рейтинг {a[0]} ({a[1]} отзывов), магазин B — "
            f"рейтинг {b[0]} ({b[1]} отзывов). Средний рейтинг сети — "
            f"{simple:.2f}?")


def q9_peeking():
    n_sim = 300
    return (f"Тест без реального эффекта проверяется каждые 2 дня из 10, "
            f"останавливается при первой значимости. Из {n_sim} таких "
            f"симуляций, сколько дадут ложную значимость против проверки "
            f"только в конце?")


def q10_outlier_median():
    values = [45, 52, 48, 3200, 50]
    mean_v = statistics.mean(values)
    return (f"Средний размер сделки отдела продаж за неделю (5 сделок) — "
            f"{mean_v:.0f} у.е. Это типичный размер сделки отдела?")


ALL = [q1_small_numbers, q2_survivorship, q3_base_rate, q4_multiple_comparisons,
       q5_confounding, q6_denominator, q7_effect_size, q8_weighted_average,
       q9_peeking, q10_outlier_median]


def main():
    for i, fn in enumerate(ALL, 1):
        print(f"--- Экзаменационный вопрос {i}: {fn.__name__} ---")
        print(f"  вопрос: {fn()}")
        print()


if __name__ == "__main__":
    main()
