"""Ловушки группы A — выборка, случайность, смещение (step-01.md, 10 штук).

Каждая функция считает пару чисел: наивный (неверный) ответ и правильный
— на собственном небольшом детерминированном датасете (15-30 строк/точек).
SEED фиксирован до первого обращения к random.

Запуск: python traps_a.py — печатает все десять с числами.
"""

import random
import statistics
from decimal import Decimal

SEED = 20260823
random.seed(SEED)


def trap_01_small_numbers():
    """Закон малых чисел: 5 бросков монеты дали 4 орла — монета нечестная?"""
    random.seed(SEED)
    coin = [random.random() < 0.5 for _ in range(5)]
    heads = sum(coin)
    # p(>=4 орлов из 5 при честной монете) — биномиальная, считаем прямым перебором
    from math import comb
    p_fair = sum(comb(5, k) * 0.5**5 for k in range(4, 6))
    return {
        "вопрос": "5 бросков честной монеты дали 4 орла. Монета нечестная?",
        "датасет": f"броски: {[int(x) for x in coin]}",
        "неверный_ответ": "80% орлов — явно нечестная монета",
        "правильный_ответ": f"P(>=4 орла из 5 при честной монете) = {p_fair:.3f} — почти "
                           f"каждый шестой честный эксперимент из 5 бросков даёт такой "
                           f"результат случайно, вывода о нечестности сделать нельзя",
        "число": round(p_fair, 3),
    }


def trap_02_regression_to_mean():
    """Топ-5 продавцов месяца показывают средний результат в следующем."""
    random.seed(SEED + 1)
    true_skill = [random.gauss(100, 10) for _ in range(30)]
    month1 = [s + random.gauss(0, 20) for s in true_skill]
    month2 = [s + random.gauss(0, 20) for s in true_skill]
    top5_idx = sorted(range(30), key=lambda i: -month1[i])[:5]
    top5_month1_avg = statistics.mean(month1[i] for i in top5_idx)
    top5_month2_avg = statistics.mean(month2[i] for i in top5_idx)
    overall_month2_avg = statistics.mean(month2)
    return {
        "вопрос": "Топ-5 продавцов января в феврале показали результат хуже — "
                  "они расслабились?",
        "датасет": f"30 продавцов, средний результат января топ-5: "
                   f"{top5_month1_avg:.1f}, февраля: {top5_month2_avg:.1f}, "
                   f"средний февраль по всем: {overall_month2_avg:.1f}",
        "неверный_ответ": "топ-5 расслабились после успеха, нужно их мотивировать",
        "правильный_ответ": f"регрессия к среднему: январский топ-5 отобран отчасти по "
                           f"случайной удаче, в феврале случайная компонента не "
                           f"повторяется — их результат ({top5_month2_avg:.1f}) ближе к "
                           f"общему среднему ({overall_month2_avg:.1f}), а не к своему "
                           f"январскому пику",
        "число": round(top5_month1_avg - top5_month2_avg, 1),
    }


def trap_03_survivorship():
    """Выжившие проекты показывают средний ROI выше рынка."""
    random.seed(SEED + 2)
    n = 25
    roi = [random.gauss(0.06, 0.35) for _ in range(n)]
    survived = [r for r in roi if r > -0.10]  # проекты с большой просадкой закрыты
    closed = n - len(survived)
    avg_all_intended = statistics.mean(roi)
    avg_survivors = statistics.mean(survived)
    closed_word = "фонд" if closed == 1 else ("фонда" if closed in (2, 3, 4) else "фондов")
    return {
        "вопрос": f"Средний ROI {len(survived)} ныне действующих фондов — "
                  f"{avg_survivors:.1%}. Это средняя доходность отрасли?",
        "датасет": f"25 фондов запущено, {len(survived)} дожили до отчёта "
                   f"(закрытые давали просадку глубже -10%)",
        "неверный_ответ": f"да, средняя доходность отрасли {avg_survivors:.1%}",
        "правильный_ответ": f"нет — {closed} {closed_word} с провальным ROI закрыты "
                           f"и не попали в выборку; истинная средняя по всем запущенным "
                           f"— {avg_all_intended:.1%}, выборка по выжившим завышает "
                           f"на {avg_survivors - avg_all_intended:.1%}",
        "число": round(avg_survivors - avg_all_intended, 3),
    }


def trap_04_convenience_sample():
    """Опрос в приложении показывает 90% удовлетворённость."""
    random.seed(SEED + 3)
    all_users_satisfaction = [random.random() < 0.55 for _ in range(2000)]  # реальная база
    responders = [s for s in all_users_satisfaction if s and random.random() < 0.30
                 or not s and random.random() < 0.05]  # довольные отвечают охотнее
    survey_rate = statistics.mean(responders) if responders else 0
    true_rate = statistics.mean(all_users_satisfaction)
    return {
        "вопрос": f"Опрос внутри приложения (заполнили {len(responders)} из 2000) "
                  f"даёт удовлетворённость {survey_rate:.0%}. Можно докладывать это число?",
        "датасет": f"2000 пользователей, реальная удовлетворённость {true_rate:.0%}, "
                   f"довольные отвечают на опрос в 6 раз охотнее недовольных",
        "неверный_ответ": f"да, удовлетворённость {survey_rate:.0%}",
        "правильный_ответ": f"нет — те, кто заполнил опрос добровольно, смещены в сторону "
                           f"довольных; истинная удовлетворённость по всей базе — "
                           f"{true_rate:.0%}, разница {survey_rate - true_rate:.0%}",
        "число": round(survey_rate - true_rate, 3),
    }


def trap_05_monty_hall():
    """Классическая условная вероятность — не пересчитывается, а цитируется с проверкой имитацией."""
    random.seed(SEED + 4)
    n_sim = 10000
    switch_wins = 0
    stay_wins = 0
    for _ in range(n_sim):
        car = random.randint(0, 2)
        choice = random.randint(0, 2)
        if choice == car:
            stay_wins += 1
        else:
            switch_wins += 1
    return {
        "вопрос": "Три двери, за одной приз. Выбрали дверь, ведущий открыл одну из "
                  "оставшихся пустую. Стоит ли менять выбор?",
        "датасет": f"имитация {n_sim} игр: не меняли — выигрыш {stay_wins/n_sim:.1%}, "
                   f"меняли — {switch_wins/n_sim:.1%}",
        "неверный_ответ": "не важно, осталось 2 двери — шанс 50/50",
        "правильный_ответ": f"менять выгоднее: смена выигрывает в {switch_wins/n_sim:.0%} "
                           f"случаев против {stay_wins/n_sim:.0%} — открытие ведущим пустой "
                           f"двери не случайно, он знает, где приз, и это меняет условную "
                           f"вероятность",
        "число": round(switch_wins / n_sim, 3),
    }


def trap_06_base_rate():
    """Тест на редкое событие с ложноположительными."""
    prevalence = 0.001
    sensitivity = 0.99
    fpr = 0.05
    population = 100000
    true_positive = population * prevalence * sensitivity
    false_positive = population * (1 - prevalence) * fpr
    p_disease_given_positive = true_positive / (true_positive + false_positive)
    return {
        "вопрос": "Тест точен на 99% (доля верных срабатываний), редкое явление "
                  "встречается у 0.1% популяции. Тест положительный — какова вероятность, "
                  "что явление действительно есть?",
        "датасет": f"популяция {population}: истинных случаев {population*prevalence:.0f}, "
                   f"ложноположительных при FPR 5% — {false_positive:.0f}",
        "неверный_ответ": "99%, раз тест точен на 99%",
        "правильный_ответ": f"{p_disease_given_positive:.1%} — из-за низкой базовой "
                           f"частоты (0.1%) число ложноположительных ({false_positive:.0f}) "
                           f"намного больше числа истинных случаев ({true_positive:.0f})",
        "число": round(p_disease_given_positive, 4),
    }


def trap_07_gambler_fallacy():
    """Серия проигрышей не меняет вероятность независимого события."""
    return {
        "вопрос": "Канал привлечения давал конверсию хуже среднего 6 месяцев подряд. "
                  "В седьмом месяце обязательно должно повезти?",
        "датасет": "6 независимых месяцев с конверсией ниже среднего (наблюдение, не "
                  "выборка для расчёта — сама природа независимости и есть предмет "
                  "вопроса)",
        "неверный_ответ": "да, по теории вероятностей всё выравнивается",
        "правильный_ответ": "нет, если месяцы независимы — прошлые результаты не меняют "
                           "вероятность будущих; если же зависимость есть (сезонность, "
                           "тренд), это её вопрос, а не «закона выравнивания», которого не "
                           "существует",
        "число": None,
    }


def trap_08_multiple_comparisons_subgroup():
    """Один из 10 подсегментов случайно даёт значимый эффект."""
    random.seed(SEED)
    n_segments = 10
    n_per_segment = 30
    significant = 0
    max_diff = 0
    for _ in range(n_segments):
        control = [random.gauss(100, 15) for _ in range(n_per_segment)]
        treatment = [random.gauss(100, 15) for _ in range(n_per_segment)]  # эффекта нет нигде
        diff = statistics.mean(treatment) - statistics.mean(control)
        pooled_sd = statistics.pstdev(control + treatment)
        se = pooled_sd * (2 / n_per_segment) ** 0.5
        z = diff / se if se else 0
        if abs(z) > 1.96:
            significant += 1
        max_diff = max(max_diff, abs(diff))
    return {
        "вопрос": f"Проверили эффект в 10 подсегментах по отдельности, в одном из них "
                  f"результат значим (p<0.05). Стоит внедрять именно там?",
        "датасет": f"10 подсегментов по {n_per_segment} наблюдений, эффекта нет ни в "
                   f"одном по построению; значимых найдено: {significant}",
        "неверный_ответ": "да, в этом подсегменте эффект реален",
        "правильный_ответ": f"при 10 независимых проверках с порогом 0.05 ожидаемое число "
                           f"ложных срабатываний — 0.5, а нашли {significant}; без "
                           f"поправки на множественные сравнения (Bonferroni: порог "
                           f"0.05/10=0.005) находка не отличима от случайности",
        "число": significant,
    }


def trap_09_optional_stopping():
    """Подглядывание в промежуточные результаты A/B-теста."""
    random.seed(SEED + 6)
    false_positive_fixed = 0
    false_positive_peeking = 0
    n_sim = 500

    def is_significant(a, b):
        pa, pb = statistics.mean(a), statistics.mean(b)
        se = ((pa * (1 - pa) / len(a)) + (pb * (1 - pb) / len(b))) ** 0.5
        return se > 0 and abs(pa - pb) / se > 1.96

    for _ in range(n_sim):
        # полный ряд генерируется один раз - "подглядывание" и "фиксированная
        # длительность" смотрят на одни и те же данные, иначе сравнение нечестное
        a, b = [], []
        for day in range(1, 15):
            a += [random.random() < 0.10 for _ in range(20)]
            b += [random.random() < 0.10 for _ in range(20)]  # эффекта нет нигде

        peeked_significant = False
        for day in range(2, 15, 2):
            n = day * 20
            if is_significant(a[:n], b[:n]):
                peeked_significant = True
                break
        if peeked_significant:
            false_positive_peeking += 1

        if is_significant(a, b):
            false_positive_fixed += 1
    return {
        "вопрос": "Смотрим на p-value теста каждый день и останавливаем эксперимент, "
                  "как только получили p<0.05. Это ускоряет принятие решений без вреда "
                  "для точности?",
        "датасет": f"{n_sim} симуляций теста без реального эффекта, 14 дней, проверка "
                   f"значимости каждые 2 дня против проверки только в конце",
        "неверный_ответ": "да, раньше увидели значимость — раньше приняли решение",
        "правильный_ответ": f"ложных срабатываний при ежедневном подглядывании — "
                           f"{false_positive_peeking/n_sim:.1%} от симуляций, при "
                           f"фиксированной длительности — {false_positive_fixed/n_sim:.1%}: "
                           f"многократная проверка увеличивает вероятность поймать случайный "
                           f"выброс за пределами доверительного интервала",
        "число": round(false_positive_peeking/n_sim - false_positive_fixed/n_sim, 3),
    }


def trap_10_unequal_variance():
    """Сравнение дисперсий, а не только средних, при принятии решения."""
    random.seed(SEED + 7)
    a = [random.gauss(1000, 50) for _ in range(20)]
    b = [random.gauss(1000, 400) for _ in range(20)]
    mean_a, mean_b = statistics.mean(a), statistics.mean(b)
    sd_a, sd_b = statistics.pstdev(a), statistics.pstdev(b)
    return {
        "вопрос": "Средний чек у двух вариантов почти одинаковый. Значит, варианты "
                  "равнозначны для бизнеса?",
        "датасет": f"вариант A: среднее {mean_a:.0f}, ст.откл. {sd_a:.0f}; "
                   f"вариант B: среднее {mean_b:.0f}, ст.откл. {sd_b:.0f}",
        "неверный_ответ": "да, средние почти равны — разницы нет",
        "правильный_ответ": f"средние близки, но разброс различается в {sd_b/sd_a:.1f} "
                           f"раза — вариант B даёт менее предсказуемую выручку "
                           f"(выше риск), что для бизнеса не эквивалентно варианту A даже "
                           f"при равном среднем",
        "число": round(sd_b / sd_a, 1),
    }


ALL_TRAPS = [
    trap_01_small_numbers, trap_02_regression_to_mean, trap_03_survivorship,
    trap_04_convenience_sample, trap_05_monty_hall, trap_06_base_rate,
    trap_07_gambler_fallacy, trap_08_multiple_comparisons_subgroup,
    trap_09_optional_stopping, trap_10_unequal_variance,
]


def main():
    for i, fn in enumerate(ALL_TRAPS, 1):
        r = fn()
        print(f"--- Ловушка A{i}: {fn.__name__} ---")
        for k, v in r.items():
            print(f"  {k}: {v}")
        print()


if __name__ == "__main__":
    main()
