"""Закрытый выходной набор F2 — 10 вопросов, не совпадающих с 40
ловушками шагов 01-04 (другие числа, где повторяется механизм — другой
сценарий). Эталон для самопроверки step-05.md, часть F2.

SEED фиксирован до первого обращения к random."""

import random
import statistics
from math import sqrt, comb

SEED = 20260827


def q1_small_numbers():
    random.seed(SEED)
    p = sum(comb(8, k) * 0.5**8 for k in range(6, 9))
    return {
        "вопрос": "8 показов рекламного креатива дали 6 кликов из ожидаемых 50%. "
                  "Креатив работает значимо лучше среднего?",
        "правильный_ответ": f"нет — P(>=6 из 8 при истинных 50%) = {p:.3f}, "
                           f"почти каждый шестой такой эксперимент даёт результат "
                           f"случайно на выборке 8",
        "число": round(p, 3),
    }


def q2_survivorship():
    random.seed(SEED + 1)
    n = 20
    roi = [random.gauss(0.05, 0.30) for _ in range(n)]
    survived = [r for r in roi if r > -0.12]
    return {
        "вопрос": f"Средний ROI {len(survived)} действующих стартапов акселератора — "
                  f"{statistics.mean(survived):.1%}. Это средняя доходность когорты акселератора?",
        "правильный_ответ": f"нет — {n-len(survived)} закрытых стартапов не попали в "
                           f"выборку; истинное среднее по всем {n} — "
                           f"{statistics.mean(roi):.1%}",
        "число": round(statistics.mean(survived) - statistics.mean(roi), 3),
    }


def q3_base_rate():
    prevalence = 0.005
    sensitivity = 0.95
    fpr = 0.10
    pop = 50000
    tp = pop * prevalence * sensitivity
    fp = pop * (1 - prevalence) * fpr
    p = tp / (tp + fp)
    return {
        "вопрос": "Скоринговая модель ловит 95% реальных мошенников, но ложно "
                  "помечает 10% честных клиентов. Мошенники — 0.5% клиентской базы. "
                  "Клиент помечен моделью — какова вероятность, что он реально мошенник?",
        "правильный_ответ": f"{p:.1%} — ложноположительных ({fp:.0f}) намного больше "
                           f"истинных случаев ({tp:.0f}) из-за низкой базовой частоты",
        "число": round(p, 4),
    }


def q4_multiple_comparisons():
    random.seed(SEED + 2)
    sig = 0
    for _ in range(15):
        a = [random.gauss(50, 10) for _ in range(25)]
        b = [random.gauss(50, 10) for _ in range(25)]
        diff = statistics.mean(b) - statistics.mean(a)
        se = sqrt(statistics.variance(a)/25 + statistics.variance(b)/25)
        if abs(diff/se) > 1.96:
            sig += 1
    return {
        "вопрос": f"Проверили 15 независимых сегментов без реального эффекта ни в "
                  f"одном. Сколько из них в среднем покажут ложную значимость на "
                  f"уровне p<0.05?",
        "правильный_ответ": f"ожидаемо ~0.75 (15*0.05); в этом прогоне сработало {sig}",
        "число": round(15*0.05, 2),
    }


def q5_confounding():
    random.seed(SEED + 3)
    n = 30
    hours_daylight = [random.uniform(9, 15) for _ in range(n)]
    ice_cream = [20 + 4*h + random.gauss(0, 8) for h in hours_daylight]
    sunscreen = [5 + 1.5*h + random.gauss(0, 4) for h in hours_daylight]
    mx, my = statistics.mean(ice_cream), statistics.mean(sunscreen)
    cov = sum((x-mx)*(y-my) for x, y in zip(ice_cream, sunscreen)) / n
    r = cov / (statistics.pstdev(ice_cream) * statistics.pstdev(sunscreen))
    return {
        "вопрос": f"Продажи мороженого коррелируют с продажами солнцезащитного крема "
                  f"(r={r:.2f}). Стоит продавать их одним комплектом ради взаимного "
                  f"продвижения, основываясь на этой связи как на причинной?",
        "правильный_ответ": f"нет прямой причинной связи — обе переменные зависят от "
                           f"общего фактора (световой день/температура), r={r:.2f} не "
                           f"доказывает, что один товар стимулирует покупку другого",
        "число": round(r, 2),
    }


def q6_denominator():
    m1 = (150, 5000)
    m2 = (160, 4000)
    r1, r2 = m1[0]/m1[1], m2[0]/m2[1]
    return {
        "вопрос": f"Доля возвратов выросла с {r1:.1%} до {r2:.1%}. Качество товара "
                  f"ухудшилось?",
        "правильный_ответ": f"не обязательно — число возвратов почти не изменилось "
                           f"({m1[0]} против {m2[0]}), а база (знаменатель) сократилась "
                           f"с {m1[1]} до {m2[1]}; рост доли может быть эффектом смены базы, "
                           f"не качества",
        "число": round(r2 - r1, 4),
    }


def q7_effect_size():
    n = 200000
    pa, pb = 0.050, 0.052
    se = sqrt(pa*(1-pa)/n + pb*(1-pb)/n)
    z = (pb-pa)/se
    return {
        "вопрос": f"На выборке {n}+{n} тест дал z={z:.1f} (значимо), разница долей "
                  f"{pb-pa:.1%}. Внедрять изменение немедленно?",
        "правильный_ответ": f"не обязательно — абсолютная разница всего {pb-pa:.1%}, "
                           f"при очень больших выборках даже ничтожный эффект "
                           f"статистически значим; решение требует сравнения размера "
                           f"эффекта со стоимостью внедрения",
        "число": round(pb-pa, 3),
    }


def q8_weighted_average():
    a = (4.5, 800)
    b = (2.9, 40)
    simple = (a[0]+b[0])/2
    weighted = (a[0]*a[1]+b[0]*b[1])/(a[1]+b[1])
    return {
        "вопрос": f"Магазин A — рейтинг {a[0]} ({a[1]} отзывов), магазин B — "
                  f"рейтинг {b[0]} ({b[1]} отзывов). Средний рейтинг сети — "
                  f"{simple:.2f}?",
        "правильный_ответ": f"нет для общей оценки сети — нужно взвесить по числу "
                           f"отзывов: {weighted:.2f}, а не простое среднее {simple:.2f}",
        "число": round(weighted, 2),
    }


def q9_peeking():
    random.seed(SEED + 4)

    def is_sig(a, b):
        pa, pb = statistics.mean(a), statistics.mean(b)
        se = sqrt(pa*(1-pa)/len(a) + pb*(1-pb)/len(b))
        return se > 0 and abs(pa-pb)/se > 1.96

    n_sim = 300
    peek_fp = fixed_fp = 0
    for _ in range(n_sim):
        a, b = [], []
        for day in range(1, 11):
            a += [random.random() < 0.08 for _ in range(25)]
            b += [random.random() < 0.08 for _ in range(25)]
        peeked = False
        for day in range(2, 11, 2):
            n = day*25
            if is_sig(a[:n], b[:n]):
                peeked = True
                break
        if peeked:
            peek_fp += 1
        if is_sig(a, b):
            fixed_fp += 1
    return {
        "вопрос": f"Тест без реального эффекта проверяется каждые 2 дня из 10, "
                  f"останавливается при первой значимости. Из {n_sim} таких симуляций, "
                  f"сколько дадут ложную значимость против проверки только в конце?",
        "правильный_ответ": f"подглядывание: {peek_fp} из {n_sim} ({peek_fp/n_sim:.1%}); "
                           f"фиксированная длительность: {fixed_fp} из {n_sim} "
                           f"({fixed_fp/n_sim:.1%}) — подглядывание завышает долю "
                           f"ложных решений",
        "число": round(peek_fp/n_sim - fixed_fp/n_sim, 3),
    }


def q10_outlier_median():
    values = [45, 52, 48, 3200, 50]
    mean_v = statistics.mean(values)
    median_v = statistics.median(values)
    return {
        "вопрос": f"Средний размер сделки отдела продаж за неделю (5 сделок) — "
                  f"{mean_v:.0f} у.е. Это типичный размер сделки отдела?",
        "правильный_ответ": f"нет — одна сделка на 3200 у.е. сдвигает среднее с "
                           f"~49 (без неё) до {mean_v:.0f}; медиана ({median_v}) "
                           f"устойчивее к этому выбросу",
        "число": round(mean_v, 0),
    }


ALL = [q1_small_numbers, q2_survivorship, q3_base_rate, q4_multiple_comparisons,
       q5_confounding, q6_denominator, q7_effect_size, q8_weighted_average,
       q9_peeking, q10_outlier_median]


def main():
    for i, fn in enumerate(ALL, 1):
        r = fn()
        print(f"--- Экзаменационный вопрос {i}: {fn.__name__} ---")
        for k, v in r.items():
            print(f"  {k}: {v}")
        print()


if __name__ == "__main__":
    main()
