"""Эталонные значения модуля M4: считаются здесь, а не в Power BI.

Запуск (из папки `program/M4/data/`, после `generate_m4.py`):

    python reference_m4.py

Пишет три эталонных CSV рядом с собой и печатает числа, на которые
ссылаются шаги модуля:

    ref_by_category.csv     — визуал 1 (шаг 04): категория × 4 меры
    ref_month_ytd.csv       — визуал 2 (шаг 04): год, месяц × 2 меры
    ref_plan_commission.csv — визуал 3 (шаг 04): тариф × комиссия

Правило двойного авторства формулы
(`.claude/skills/curriculum-design/SKILL.md`, п. 1.3): **источник истины —
этот скрипт**, а мера DAX в тексте шага — вторая, независимая реализация
той же формулы. Расхождение между ними означает ошибку в мере, а не в
эталоне.

Округление задано явно и одинаково во всех мерах: `ROUND_HALF_UP` через
`Decimal`, а не `round()` из стандартной библиотеки (у него банковское
округление — 0.5 идёт к чётному). Скрипт дополнительно проверяет, что ни
одно эталонное значение не лежит ближе 1e-6 к границе округления: если бы
лежало, Power BI и Python могли бы разойтись на единицу последнего знака
не из-за ошибки в мере, а из-за разного правила округления середины.
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent

# Режим `--next`: тот же расчёт на папке следующего месяца. Эталоны для
# умения C2 (`step-05.md`) обязаны считаться **тем же кодом**, что и
# эталоны шага 04, иначе сверка после Refresh проверяет не повторяемость
# очистки, а совпадение двух разных реализаций одной формулы.
NEXT = "--next" in sys.argv
SRC = HERE / ("csv_next" if NEXT else "csv")
PREFIX = "ref_next_" if NEXT else "ref_"

MIDPOINT_GUARD = Decimal("0.000001")


def read(name: str) -> list[dict[str, str]]:
    with (SRC / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def q(value: Decimal, places: str) -> Decimal:
    """Округление ROUND_HALF_UP с проверкой близости к границе."""
    step = Decimal(places)
    remainder = abs(value) % step
    if abs(remainder - step / 2) < MIDPOINT_GUARD:
        raise SystemExit(
            f"Значение {value} лежит на границе округления до {places}. "
            f"Эталон в таком виде публиковать нельзя: Power BI и Python "
            f"округляют середину по разным правилам. Меняется датасет, а не "
            f"правило округления."
        )
    return value.quantize(step, rounding=ROUND_HALF_UP)


def write_ref(name: str, header: list[str], rows: list[list[str]]) -> None:
    name = PREFIX + name
    with (HERE / name).open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\r\n")
        w.writerow(header)
        w.writerows(rows)
    print(f"{name}: {len(rows)} строк")


def main() -> int:
    tx = read("transactions.csv")
    cats = read("mcc_categories.csv")
    plans = read("merchant_plan.csv")
    merchants = read("merchants.csv")

    plan_by_key = {(p["merchant_ref"], p["period_ym"]): p for p in plans}
    cat_name = {c["code"]: c["category_name"] for c in cats}

    # ---- визуал 1: категория × Total Amount, Settled Amount, Tx Count, Decline Rate
    total = defaultdict(Decimal)
    settled = defaultdict(Decimal)
    count = defaultdict(int)
    declined = defaultdict(int)
    for r in tx:
        code = r["mcc"]
        amount = Decimal(r["amount_uah"])
        total[code] += amount
        count[code] += 1
        if r["status"] == "settled":
            settled[code] += amount
        elif r["status"] == "declined":
            declined[code] += 1

    by_cat = []
    for code, name in cat_name.items():
        rate = Decimal(declined[code]) / Decimal(count[code])
        by_cat.append((
            name,
            q(total[code], "0.01"),
            q(settled[code], "0.01"),
            count[code],
            q(rate, "0.0001"),
        ))
    by_cat.sort(key=lambda t: t[2], reverse=True)
    write_ref(
        "by_category.csv",
        ["category_name", "Total Amount", "Settled Amount", "Tx Count", "Decline Rate"],
        [[n, f"{t}", f"{s}", str(c), f"{d}"] for n, t, s, c, d in by_cat],
    )

    # ---- визуал городов: город × Total Amount. Заведён ради условия 3
    # критерия C2 (решение 22): файл следующего месяца содержит кириллицу,
    # которой не было в первом (город «Ужгород»). Проверяется файлом, а не
    # взглядом на экран: испорченная кодировка даёт другую строку, и сверка
    # называет её адресно.
    city_of = {m["merchant_id"]: m["city"] for m in merchants}
    by_city_sum = defaultdict(Decimal)
    for r in tx:
        by_city_sum[city_of[r["merchant_id"]]] += Decimal(r["amount_uah"])
    city_rows = sorted(((c, q(v, "0.01")) for c, v in by_city_sum.items()),
                       key=lambda t: t[1], reverse=True)
    write_ref("by_city.csv", ["city", "Total Amount"],
              [[c, f"{v}"] for c, v in city_rows])

    # ---- визуал 2: год, месяц × Settled Amount, Settled YTD (по дате операции)
    by_month = defaultdict(Decimal)
    for r in tx:
        if r["status"] == "settled":
            y, m = r["tx_date"][:4], r["tx_date"][5:7]
            by_month[(int(y), int(m))] += Decimal(r["amount_uah"])

    months = sorted(by_month)
    ytd_rows = []
    running = defaultdict(Decimal)
    for y, m in months:
        running[y] += by_month[(y, m)]
        ytd_rows.append([str(y), str(m), f"{q(by_month[(y, m)], '0.01')}",
                         f"{q(running[y], '0.01')}"])
    write_ref("month_ytd.csv",
              ["year", "month_no", "Settled Amount", "Settled YTD"], ytd_rows)

    # ---- визуал 3: тариф × Commission (составной ключ мерчант+период)
    commission = defaultdict(Decimal)
    commission_total = Decimal(0)
    for r in tx:
        if r["status"] != "settled":
            continue
        plan = plan_by_key[(r["merchant_id"], r["period_ym"])]
        value = Decimal(r["amount_uah"]) * Decimal(plan["commission_pct"])
        commission[plan["plan_code"]] += value
        commission_total += value
    plan_rows = sorted(((k, q(v, "0.01")) for k, v in commission.items()),
                       key=lambda t: t[1], reverse=True)
    write_ref("plan_commission.csv", ["plan_code", "Commission"],
              [[k, f"{v}"] for k, v in plan_rows])

    # ---- визуал итогов: шесть мер одной строкой, без разрезов
    # Заведён вместо проверки значений на карточках: карточка округляет до
    # трёх значащих и переопределяет формат меры (`Tx Count` = 6582
    # печатается как «7 тыс.»), поэтому критерий «сходится до второго
    # знака» на экране не проверяется вовсе — дефект R33,
    # `research/tools-gate.md`, 3.3. Опора критерия перенесена на файл.
    all_total = q(sum(total.values(), Decimal(0)), "0.01")
    all_settled = q(sum(settled.values(), Decimal(0)), "0.01")
    all_count = sum(count.values())
    all_declined = sum(declined.values())
    all_rate = q(Decimal(all_declined) / Decimal(all_count), "0.0001")
    last_year = months[-1][0]
    settled_ytd = q(running[last_year], "0.01")
    write_ref(
        "totals.csv",
        ["Total Amount", "Settled Amount", "Tx Count", "Decline Rate", "Commission", "Settled YTD"],
        [[f"{all_total}", f"{all_settled}", str(all_count), f"{all_rate}",
          f"{q(commission_total, '0.01')}", f"{settled_ytd}"]],
    )

    # ---- числа, на которые ссылаются тексты шагов
    print("\n--- Итоги по всему датасету ---")
    print(f"Total Amount   = {all_total}")
    print(f"Settled Amount = {all_settled}")
    print(f"Tx Count       = {all_count}")
    print(f"Decline Rate   = {q(Decimal(all_declined) / Decimal(all_count), '0.0001')}"
          f"  ({all_declined} отклонённых из {all_count})")
    print(f"Commission     = {q(commission_total, '0.01')}")

    statuses = defaultdict(int)
    for r in tx:
        statuses[r["status"]] += 1
    print("Статусы: " + ", ".join(f"{k} {v}" for k, v in sorted(statuses.items())))
    plans_by_merchant = defaultdict(set)
    for p in plans:
        plans_by_merchant[p["merchant_ref"]].add(p["plan_code"])
    changed = [m for m, s in plans_by_merchant.items() if len(s) > 1]
    print(f"Мерчантов всего: {len(plans_by_merchant)}; сменили тариф внутри периода: "
          f"{len(changed)}; строк в merchant_plan: {len(plans)}")

    # Ошибка «тариф один на всю историю»: берётся последний известный тариф
    # мерчанта и применяется ко всем месяцам.
    last_plan: dict[str, str] = {}
    for p in sorted(plans, key=lambda p: (p["merchant_ref"], p["period_ym"])):
        last_plan[p["merchant_ref"]] = p["commission_pct"]
    wrong = Decimal(0)
    for r in tx:
        if r["status"] == "settled":
            wrong += Decimal(r["amount_uah"]) * Decimal(last_plan[r["merchant_id"]])
    wrong_q = q(wrong, "0.01")
    right_q = q(commission_total, "0.01")
    diff = wrong_q - right_q
    print("\n--- Связь по одному мерчанту вместо пары (мерчант, период) ---")
    print(f"Комиссия по последнему тарифу: {wrong_q}")
    print(f"Комиссия по составному ключу:  {right_q}")
    print(f"Расхождение: {diff} ({q(abs(diff) / right_q * 100, '0.01')}%)")

    # Вторая ошибка того же класса, но с другой арифметикой: плоская
    # средняя ставка вместо помесячной. Считается отдельно, потому что
    # число от подстановки «последний тариф» к ней не относится — на этом
    # разошлись задание 8 и его критерий (дефект R36).
    settled_by_plan = defaultdict(Decimal)
    for r in tx:
        if r["status"] == "settled":
            settled_by_plan[plan_by_key[(r["merchant_id"], r["period_ym"])]["plan_code"]] += \
                Decimal(r["amount_uah"])
    eff_rate = commission_total / sum(settled_by_plan.values())
    print("\n--- Плоская средняя ставка вместо помесячной ---")
    print(f"Эффективная средняя ставка = Commission / Settled Amount = "
          f"{q(eff_rate * 100, '0.0001')}%")
    print(f"Итог при плоской ставке: {q(eff_rate * sum(settled_by_plan.values()), '0.01')} "
          f"— расхождение с {right_q} равно 0.00 по построению")
    print("Раскладка по тарифам ломается, хотя итог сходится:")
    for code in sorted(commission, key=lambda k: -commission[k]):
        flat = q(settled_by_plan[code] * eff_rate, "0.01")
        right = q(commission[code], "0.01")
        print(f"  {code:9s} правильно {right:>10} при плоской ставке {flat:>10} "
              f"расхождение {right - flat:+}")

    # Вторая колонка-кандидат: дата расчёта против даты операции.
    crossing = sum(1 for r in tx if r["tx_date"][:7] != r["settled_date"][:7])
    by_settled = defaultdict(Decimal)
    for r in tx:
        if r["status"] == "settled":
            by_settled[r["settled_date"][:7]] += Decimal(r["amount_uah"])
    by_tx = defaultdict(Decimal)
    for r in tx:
        if r["status"] == "settled":
            by_tx[r["tx_date"][:7]] += Decimal(r["amount_uah"])
    print("\n--- Дата операции против даты расчёта ---")
    print(f"Операций, у которых месяц расчёта не совпал с месяцем операции: "
          f"{crossing} из {all_count}")
    worst = max(by_tx, key=lambda p: abs(by_tx[p] - by_settled.get(p, Decimal(0))))
    print(f"Наибольшее расхождение месячной суммы — {worst}: "
          f"по дате операции {q(by_tx[worst], '0.01')}, "
          f"по дате расчёта {q(by_settled.get(worst, Decimal(0)), '0.01')}, "
          f"разница {q(by_tx[worst] - by_settled.get(worst, Decimal(0)), '0.01')}")

    # Числа, которыми критерий step-03.md проверяет связи ДО того, как
    # появятся меры: обычная сумма колонки, разложенная по измерению.
    print("\n--- Проверки step-03.md (сумма amount_uah, без мер) ---")
    by_plan_all = defaultdict(Decimal)
    for r in tx:
        plan = plan_by_key[(r["merchant_id"], r["period_ym"])]
        by_plan_all[plan["plan_code"]] += Decimal(r["amount_uah"])
    for k in sorted(by_plan_all, key=lambda k: by_plan_all[k], reverse=True):
        print(f"  по тарифу {k}: {q(by_plan_all[k], '0.01')}")
    aug_tx = sum((Decimal(r["amount_uah"]) for r in tx if r["tx_date"][:7] == "2025-08"), Decimal(0))
    aug_st = sum((Decimal(r["amount_uah"]) for r in tx if r["settled_date"][:7] == "2025-08"), Decimal(0))
    print(f"  2025-08 по дате операции: {q(aug_tx, '0.01')}; "
          f"по дате расчёта: {q(aug_st, '0.01')}; "
          f"разница {q(aug_tx - aug_st, '0.01')}")

    # Проверка требований к экспортируемым значениям (решение 22).
    texts = ([c["category_name"] for c in cats] + [p["plan_code"] for p in plans]
             + [m["merchant_name"] for m in read("merchants.csv")]
             + [m["city"] for m in read("merchants.csv")])
    bad = [t for t in texts if t[:1] in "=@+-"]
    print(f"\nТекстовых значений, начинающихся с '=', '@', '+', '-': {len(bad)}")
    commas = [m["merchant_name"] for m in read("merchants.csv") if "," in m["merchant_name"]]
    print(f"Названий мерчантов с запятой внутри значения: {len(commas)} — "
          f"{'; '.join(commas)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
