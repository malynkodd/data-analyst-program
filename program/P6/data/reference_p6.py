"""Эталонный расчёт P6 — независимо от fetch_stat.py/fetch_nbu.py.

Три вычисляемых блока (то, что МОЖНО посчитать по вопросу заказчика):
1. Ранжирование регионов по средней YoY-динамике розничной торговли —
   отвечает на день-1 вопрос («где растёт спрос»), но по рознице
   ЦЕЛИКОМ, не по категории «обувь» — источник не даёт такого разреза.
2. Помесячный импорт обуви — данные Держстата идут накопительным
   итогом с начала года (найдено прогоном, не в описании blueprint):
   у каждого из 10 лет по 11 значений, каждое больше предыдущего, и
   резко падает в январе — это не 11 месяцев роста подряд, а сброс
   счётчика. Настоящее месячное значение — разница с предыдущим
   месяцем того же года (январь — сам по себе).
3. Средняя импортная цена пары обуви (стоимость/количество) по годам —
   это НЕ розничная цена и НЕ эластичность спроса, а себестоимость
   импорта; ближайшее, что можно посчитать в сторону вопроса «что
   будет при +15% цены».

Главный вывод — не число, а граница: ни один из трёх источников не
содержит пары «изменение цены -> изменение спроса» для одного и того
же товара. Ответить на день-3 вопрос количественно нельзя — это и есть
проектная находка, не недосмотр.
"""
from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SNAP = HERE / "snapshot"


def read_csv(name):
    with (SNAP / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> int:
    retail = read_csv("retail_turnover_by_region.csv")
    footwear = read_csv("footwear_imports.csv")
    usd = read_csv("usd_uah.csv")

    # --- 1. Регионы по средней YoY-динамике розницы (не по категории) ---
    by_region = defaultdict(list)
    for r in retail:
        if r["region_code"] == "UA00000000000000000":
            continue  # национальный итог — не регион
        by_region[r["region_name"]].append(float(r["idx_yoy_pct"]))
    avg_by_region = {name: round(statistics.mean(vals), 1) for name, vals in by_region.items()}
    ranked = sorted(avg_by_region.items(), key=lambda kv: kv[1], reverse=True)

    # --- 2. Помесячный импорт обуви: снять кумулятивный сброс по годам --
    by_year_cost = defaultdict(dict)
    by_year_qty = defaultdict(dict)
    for r in footwear:
        year, month = r["period"].split("-M")
        if r["cost_usd_thousand"]:
            by_year_cost[year][int(month)] = float(r["cost_usd_thousand"])
        if r["qty_pairs"]:
            by_year_qty[year][int(month)] = float(r["qty_pairs"])

    monthly_cost = {}   # "YYYY-M0M" -> дельта за месяц
    monthly_qty = {}
    for year, months in by_year_cost.items():
        prev = None
        for m in sorted(months):
            val = months[m]
            monthly_cost[f"{year}-M{m:02d}"] = val if prev is None else round(val - prev, 1)
            prev = val
    for year, months in by_year_qty.items():
        prev = None
        for m in sorted(months):
            val = months[m]
            monthly_qty[f"{year}-M{m:02d}"] = val if prev is None else round(val - prev, 1)
            prev = val

    # --- 3. Средняя цена импортной пары по годам (себестоимость, не розница)
    year_cost_total = {y: max(v.values()) for y, v in by_year_cost.items()}   # накопленный итог ноября
    year_qty_total = {y: max(v.values()) for y, v in by_year_qty.items()}
    avg_price_by_year = {
        y: round(year_cost_total[y] * 1000 / year_qty_total[y], 2)
        for y in sorted(set(year_cost_total) & set(year_qty_total))
    }  # $/пара (cost в тис. дол., qty в парах)

    # --- USD/UAH: месячное среднее -------------------------------------
    monthly_usd = defaultdict(list)
    for r in usd:
        d, m, y = r["date"].split(".")
        monthly_usd[f"{y}-M{m}"].append(float(r["rate"]))
    avg_usd_2024 = round(statistics.mean(
        v for k, vals in monthly_usd.items() for v in vals if k.startswith("2024")), 4)

    print("=== 1. Регионы: средний YoY-индекс розничной торговли (не по категории) ===")
    for name, avg in ranked[:5]:
        print(f"  {name}: {avg}")
    print("  ...")
    for name, avg in ranked[-3:]:
        print(f"  {name}: {avg}")
    print(f"  (n={len(ranked)} регионов, {len(retail)-len([r for r in retail if r['region_code']=='UA00000000000000000'])} наблюдений)")

    print()
    print("=== 2. Импорт обуви, помесячно (после снятия кумулятивного сброса) ===")
    print(f"  2024-M01: {monthly_qty.get('2024-M01')} пар, {monthly_cost.get('2024-M01')} тыс.$")
    print(f"  2024-M11: {monthly_qty.get('2024-M11')} пар, {monthly_cost.get('2024-M11')} тыс.$")
    print(f"  наивная (неверная) трактовка M11 как «месяц»: "
          f"{by_year_qty['2024'][11]} пар — в 30+ раз больше настоящего месячного числа")

    print()
    print("=== 3. Средняя цена импортной пары обуви, $ ===")
    for y in sorted(avg_price_by_year):
        print(f"  {y}: {avg_price_by_year[y]}")

    print()
    print(f"=== USD/UAH, среднее за 2024: {avg_usd_2024} ===")

    print()
    print("=== Главный вывод ===")
    print("Ни retail_turnover_by_region.csv (регион, БЕЗ категории), ни")
    print("footwear_imports.csv (категория, БЕЗ региона, это себестоимость")
    print("импорта, не розничная цена), ни usd_uah.csv не содержат пары")
    print("«наблюдаемое изменение цены -> наблюдаемое изменение спроса»")
    print("ни для одного товара. Ответить на вопрос про +15% количественно")
    print("нельзя ни одним источником, использованным в проекте.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
