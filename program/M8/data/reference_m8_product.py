"""Эталоны шагов M8.04–M8.06: продуктовые метрики, RFM, сезонность.

Пишет четыре CSV:

* `ref_product_metrics.csv` — умение F6, шаг 04: ARPU, ARPPU, конверсия,
  DAU/WAU/MAU, sticky ratio, помесячная выручка, MoM и повторная выручка;
* `ref_rfm_segments.csv` — умение F7, шаг 05: 21 непустой RFM-сегмент,
  число клиентов, выручка и её доля;
* `ref_unit_economics.csv` — умение F7, шаг 05: юнит-экономика одного
  привлечённого клиента;
* `ref_forecast.csv` — умение F8, шаг 06: коэффициенты дня недели,
  прогноз на отложенную неделю и MAPE двух моделей.

Считается стандартной библиотекой: решение учащегося пишется на `pandas`
(`groupby`, `resample`, `quantile`), и эталон, посчитанный теми же
вызовами, проверял бы вызов сам собой (правило двойного авторства,
скилл curriculum-design, раздел 1.3).

**Определения** (решение 30) — без них ни одно число ниже не факт:

* **база «пользователи»** — все 2988 лидов `leads.csv`; **база
  «плательщики»** — 955 клиентов с хотя бы одной строкой в
  `revenue.csv`. ARPU считается на первую базу, ARPPU — на вторую, и
  именно поэтому `ARPU = ARPPU × конверсия`;
* **активность** — день, в который у клиента есть хотя бы одна
  транзакция. Другого сигнала активности в датасете нет, и это
  ограничение названо в шаге вслух: DAU по транзакциям — не то же самое,
  что DAU по входам в приложение;
* **дата снапшота** — 2026-05-15, последний день данных. Recency
  считается от неё, а не от «сегодня»;
* **пустые** — лиды без `user_id` (2033) не входят в базу плательщиков и
  входят в базу пользователей;
* **дубли** — `lead_id` и пара (`user_id`, `txn_date`, `amount`)
  уникальны, дедупликация не применяется;
* **квантиль** — линейная интерполяция, метод по умолчанию
  `pandas.Series.quantile`; границы RFM — трети (1/3 и 2/3);
* **правило сравнения с границей** — `<=` относит значение к нижней
  группе. На оси F границы попадают на целые 3 и 7, и 118 клиентов с
  F = 3 целиком уходят в нижнюю треть: правило названо здесь, потому что
  при `<` состав сегментов меняется;
* **полные недели** — с понедельника по воскресенье; неполные недели по
  краям ряда отбрасываются, отложенная неделя — последняя полная.

Запуск из корня репозитория:

    .venv\\Scripts\\python.exe program\\M8\\data\\reference_m8_product.py
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"

SNAPSHOT = date(2026, 5, 15)
CAC = 368.15  # шаг 02, ref_business_metrics.csv


def read(name: str) -> list[dict[str, str]]:
    with (RAW / name).open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def as_date(text: str) -> date:
    return date(int(text[:4]), int(text[5:7]), int(text[8:10]))


def quantile(sorted_values: list[float], q: float) -> float:
    n = len(sorted_values)
    pos = q * (n - 1)
    low = int(pos)
    high = min(low + 1, n - 1)
    return sorted_values[low] + (pos - low) * (sorted_values[high] - sorted_values[low])


def score_high_is_good(value: float, bounds: tuple[float, float]) -> int:
    return 1 if value <= bounds[0] else (2 if value <= bounds[1] else 3)


def score_low_is_good(value: float, bounds: tuple[float, float]) -> int:
    return 3 if value <= bounds[0] else (2 if value <= bounds[1] else 1)


def main() -> int:
    leads = read("leads.csv")
    revenue = read("revenue.csv")

    total_revenue = sum(float(r["amount"]) for r in revenue)
    payers = {r["user_id"] for r in revenue}
    converted = sum(1 for l in leads if l["user_id"])
    arppu = total_revenue / len(payers)
    conversion = converted / len(leads)
    arpu = total_revenue / len(leads)

    by_day: dict[date, set[str]] = defaultdict(set)
    revenue_by_day: dict[date, float] = defaultdict(float)
    by_month: dict[str, set[str]] = defaultdict(set)
    revenue_by_month: dict[str, float] = defaultdict(float)
    by_week: dict[date, set[str]] = defaultdict(set)
    for row in revenue:
        day = as_date(row["txn_date"])
        amount = float(row["amount"])
        by_day[day].add(row["user_id"])
        revenue_by_day[day] += amount
        by_month[row["txn_date"][:7]].add(row["user_id"])
        revenue_by_month[row["txn_date"][:7]] += amount
        by_week[day - timedelta(days=day.weekday())].add(row["user_id"])

    dau = sum(len(v) for v in by_day.values()) / len(by_day)
    wau = sum(len(v) for v in by_week.values()) / len(by_week)
    months = sorted(by_month)
    mau_last_full = len(by_month[months[-2]])
    dau_last_full = sum(
        len(users) for day, users in by_day.items() if day.strftime("%Y-%m") == months[-2]
    ) / sum(1 for day in by_day if day.strftime("%Y-%m") == months[-2])
    sticky = dau_last_full / mau_last_full

    repeat_revenue = 0.0
    repeat_users = 0
    last, prev = months[-1], months[-2]
    both = by_month[last] & by_month[prev]
    for row in revenue:
        if row["txn_date"][:7] == last and row["user_id"] in both:
            repeat_revenue += float(row["amount"])
    repeat_users = len(both)

    mom = (revenue_by_month[months[-1]] / revenue_by_month[months[-2]] - 1) * 100

    product = [
        ("пользователей_всего", f"{len(leads)}"),
        ("плательщиков", f"{len(payers)}"),
        ("конверсия", f"{conversion:.4f}"),
        ("выручка_всего", f"{total_revenue:.2f}"),
        ("ARPU", f"{arpu:.2f}"),
        ("ARPPU", f"{arppu:.2f}"),
        ("DAU_средний", f"{dau:.2f}"),
        ("WAU_средний", f"{wau:.2f}"),
        ("MAU_последний_полный", f"{mau_last_full}"),
        ("sticky_ratio", f"{sticky:.4f}"),
        ("выручка_последний_полный_месяц", f"{revenue_by_month[months[-2]]:.2f}"),
        ("выручка_последний_месяц", f"{revenue_by_month[months[-1]]:.2f}"),
        ("MoM_процент", f"{mom:.2f}"),
        ("повторных_плательщиков", f"{repeat_users}"),
        ("повторная_выручка", f"{repeat_revenue:.2f}"),
        ("доля_повторной_выручки", f"{repeat_revenue / revenue_by_month[last]:.4f}"),
    ]

    # ---- RFM -------------------------------------------------------------
    last_txn: dict[str, date] = {}
    freq: dict[str, int] = defaultdict(int)
    money: dict[str, float] = defaultdict(float)
    for row in revenue:
        user = row["user_id"]
        day = as_date(row["txn_date"])
        last_txn[user] = max(last_txn.get(user, day), day)
        freq[user] += 1
        money[user] += float(row["amount"])

    recency = {u: (SNAPSHOT - d).days for u, d in last_txn.items()}
    bounds_r = (
        quantile(sorted(recency.values()), 1 / 3),
        quantile(sorted(recency.values()), 2 / 3),
    )
    bounds_f = (
        quantile(sorted(float(v) for v in freq.values()), 1 / 3),
        quantile(sorted(float(v) for v in freq.values()), 2 / 3),
    )
    bounds_m = (
        quantile(sorted(money.values()), 1 / 3),
        quantile(sorted(money.values()), 2 / 3),
    )

    segments: dict[str, list[float]] = defaultdict(lambda: [0, 0.0])
    for user in payers:
        code = (
            f"{score_low_is_good(recency[user], bounds_r)}"
            f"{score_high_is_good(freq[user], bounds_f)}"
            f"{score_high_is_good(money[user], bounds_m)}"
        )
        segments[code][0] += 1
        segments[code][1] += money[user]

    rfm_rows = [
        [code, str(int(count)), f"{value:.2f}", f"{value / total_revenue * 100:.2f}"]
        for code, (count, value) in sorted(segments.items())
    ]

    # ---- юнит-экономика --------------------------------------------------
    cumulative: dict[str, float] = defaultdict(float)
    paid_back: dict[str, date] = {}
    for row in sorted(revenue, key=lambda r: r["txn_date"]):
        user = row["user_id"]
        cumulative[user] += float(row["amount"])
        if user not in paid_back and cumulative[user] >= CAC:
            paid_back[user] = as_date(row["txn_date"])
    conversion_date = {
        l["user_id"]: as_date(l["conversion_date"]) for l in leads if l["user_id"]
    }
    payback_days = sorted(
        (paid_back[u] - conversion_date[u]).days for u in paid_back if u in conversion_date
    )

    unit = [
        ("CAC", f"{CAC:.2f}"),
        ("ARPPU", f"{arppu:.2f}"),
        ("вклад_на_клиента", f"{arppu - CAC:.2f}"),
        ("окупились_клиентов", f"{len(payback_days)}"),
        ("не_окупились_клиентов", f"{len(payers) - len(payback_days)}"),
        ("дней_до_окупаемости_медиана", f"{quantile(list(map(float, payback_days)), 0.5):.0f}"),
        ("дней_до_окупаемости_p90", f"{quantile(list(map(float, payback_days)), 0.9):.0f}"),
    ]

    # ---- сезонность и прогноз -------------------------------------------
    days = sorted(revenue_by_day)
    first_monday = days[0] + timedelta(days=(7 - days[0].weekday()) % 7)
    last_sunday = days[-1] - timedelta(days=(days[-1].weekday() + 1) % 7)
    series: list[tuple[date, float]] = []
    cursor = first_monday
    while cursor <= last_sunday:
        series.append((cursor, revenue_by_day.get(cursor, 0.0)))
        cursor += timedelta(days=1)

    train = series[:-7]
    test = series[-7:]
    train_mean = sum(v for _, v in train) / len(train)
    by_weekday: dict[int, list[float]] = defaultdict(list)
    for day, value in train:
        by_weekday[day.weekday()].append(value)
    factors = {
        weekday: (sum(values) / len(values)) / train_mean
        for weekday, values in by_weekday.items()
    }
    base = sum(v for _, v in train[-28:]) / 28

    seasonal = [base * factors[day.weekday()] for day, _ in test]
    flat = [base] * 7
    mape_seasonal = (
        sum(abs(f - v) / v for f, (_, v) in zip(seasonal, test)) / 7 * 100
    )
    mape_flat = sum(abs(base - v) / v for _, v in test) / 7 * 100

    forecast_rows = [
        ["коэффициент_пн", f"{factors[0]:.4f}"],
        ["коэффициент_вт", f"{factors[1]:.4f}"],
        ["коэффициент_ср", f"{factors[2]:.4f}"],
        ["коэффициент_чт", f"{factors[3]:.4f}"],
        ["коэффициент_пт", f"{factors[4]:.4f}"],
        ["коэффициент_сб", f"{factors[5]:.4f}"],
        ["коэффициент_вс", f"{factors[6]:.4f}"],
        ["полных_недель", f"{len(series) // 7}"],
        ["база_прогноза", f"{base:.2f}"],
        ["MAPE_с_сезонностью", f"{mape_seasonal:.2f}"],
        ["MAPE_без_сезонности", f"{mape_flat:.2f}"],
        ["выигрыш_сезонности_пп", f"{mape_flat - mape_seasonal:.2f}"],
        ["run_rate_последнего_месяца", f"{revenue_by_month[last] / 15 * 31:.2f}"],
    ]

    def dump(name: str, header: list[str], rows: list[list[str]]) -> None:
        with (HERE / name).open("w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh, lineterminator="\n")
            writer.writerow(header)
            writer.writerows(rows)
        print(f"{name}: {len(rows)} строк")

    dump("ref_product_metrics.csv", ["метрика", "значение"], [list(r) for r in product])
    dump("ref_rfm_segments.csv", ["сегмент", "клиентов", "выручка", "доля_выручки"], rfm_rows)
    dump("ref_unit_economics.csv", ["показатель", "значение"], [list(r) for r in unit])
    dump("ref_forecast.csv", ["показатель", "значение"], forecast_rows)

    print()
    for name, value in product:
        print(f"  {name:<32} {value}")
    print()
    print("границы RFM: R", tuple(round(b, 2) for b in bounds_r),
          "F", tuple(round(b, 2) for b in bounds_f),
          "M", tuple(round(b, 2) for b in bounds_m))
    print("непустых сегментов:", len(rfm_rows))
    top = sorted(segments.items(), key=lambda kv: -kv[1][1])[:3]
    for code, (count, value) in top:
        print(f"  {code}: клиентов {int(count)}, {value / total_revenue * 100:.2f}% выручки")
    print()
    for name, value in unit:
        print(f"  {name:<32} {value}")
    print()
    for name, value in forecast_rows:
        print(f"  {name:<32} {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
