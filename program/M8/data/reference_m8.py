"""Эталонные числа модуля M8 (Бизнес- и продуктовые метрики).

Запуск (после `generate_m8.py`):

    python reference_m8.py

Правило двойного авторства (скилл, раздел 1.3): реализация не переиспользует
внутренние списки генератора, читает три CSV заново.

Канон модуля — восемь метрик, каждая с базой (кто считается) и окном
(за какой период):

1. CPL (cost per lead) — расход канала за весь период / число лидов
   этого канала. Только платные каналы (`google_ads`, `facebook_ads`,
   `referral`) — у `organic` расход не логируется вовсе, CPL для него не
   определён, а не равен нулю (различие — 1.2 `step-01.md`).
2. CPA (cost per acquisition) — расход канала / число КОНВЕРТИРОВАННЫХ
   лидов этого канала. Тоже только платные каналы, канальный уровень.
3. CAC (customer acquisition cost) — суммарный расход по ВСЕМ каналам
   / число конвертированных клиентов по ВСЕМ каналам (включая organic,
   у которого расход 0). Смешанная (blended) метрика бизнеса целиком, не
   канала — поэтому меньше любого канального CPA.
4. LTV_D30 — средний доход одного клиента за первые 30 дней после
   конверсии. Считается только по «зрелым» клиентам — тем, у кого прошло
   ≥30 дней от конверсии до даты выгрузки (2026-05-15); незрелые клиенты
   исключаются, а не считаются нулём.
5. ROAS — весь собранный доход за период / весь платный расход за
   период. Отношение, не разность.
6. ROMI — (весь доход за период − весь платный расход за период) / весь
   платный расход за период. Один и тот же период для дохода и
   расхода — намеренное упрощение с известной ловушкой (1.2 `step-02.md`):
   доход периода включает платежи клиентов, приведённых в ПРЕДЫДУЩИЕ
   периоды, а расход — только текущего периода.
7. ROI (LTV:CAC) — (LTV_D30 − CAC) / CAC. Экономика одного клиента за
   жизненный цикл, а не денежный поток за календарный период — так ROI
   отличается от ROMI не только по названию.
8. Retention_D30 / Churn_D30 — доля зрелых клиентов, у которых есть хотя
   бы одна транзакция дохода на 30-й день после конверсии или позже.
   Churn_D30 = 1 − Retention_D30, тот же показатель с другой стороны.
"""

from __future__ import annotations

import csv
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"

CUTOFF = date(2026, 5, 15)
PAID_CHANNELS = {"google_ads", "facebook_ads", "referral"}
FOUR = Decimal("0.0001")
TWO = Decimal("0.01")


def read_leads() -> list[dict]:
    rows = []
    with (RAW / "leads.csv").open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            rows.append({
                "lead_id": r["lead_id"],
                "channel": r["channel"],
                "signup_date": date.fromisoformat(r["signup_date"]),
                "user_id": r["user_id"] or None,
                "conversion_date": date.fromisoformat(r["conversion_date"]) if r["conversion_date"] else None,
            })
    return rows


def read_revenue() -> list[dict]:
    rows = []
    with (RAW / "revenue.csv").open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            rows.append({
                "user_id": r["user_id"],
                "txn_date": date.fromisoformat(r["txn_date"]),
                "amount": Decimal(r["amount"]),
            })
    return rows


def read_spend() -> list[dict]:
    rows = []
    with (RAW / "channel_spend.csv").open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            rows.append({
                "channel": r["channel"],
                "month": r["month"],
                "spend_uah": Decimal(r["spend_uah"]),
            })
    return rows


def ratio(a: Decimal, b: Decimal, digits=TWO) -> Decimal:
    if b == 0:
        return Decimal("NaN")
    return (a / b).quantize(digits, rounding=ROUND_HALF_UP)


def main() -> int:
    leads = read_leads()
    revenue = read_revenue()
    spend = read_spend()

    users = [l for l in leads if l["user_id"]]

    spend_by_channel: dict[str, Decimal] = {}
    for s in spend:
        spend_by_channel[s["channel"]] = spend_by_channel.get(s["channel"], Decimal("0")) + s["spend_uah"]

    leads_by_channel: dict[str, int] = {}
    conv_by_channel: dict[str, int] = {}
    for l in leads:
        leads_by_channel[l["channel"]] = leads_by_channel.get(l["channel"], 0) + 1
        if l["user_id"]:
            conv_by_channel[l["channel"]] = conv_by_channel.get(l["channel"], 0) + 1

    # 1. CPL, 2. CPA - платные каналы
    cpl = {c: ratio(spend_by_channel[c], Decimal(leads_by_channel.get(c, 0))) for c in PAID_CHANNELS}
    cpa = {c: ratio(spend_by_channel[c], Decimal(conv_by_channel.get(c, 0))) for c in PAID_CHANNELS}

    # 3. CAC - смешанная
    total_spend = sum(spend_by_channel.values())
    total_conversions = len(users)
    cac = ratio(total_spend, Decimal(total_conversions))

    # 4. LTV_D30 - только зрелые клиенты (>=30 дней от конверсии до CUTOFF)
    mature_users = [u for u in users if (CUTOFF - u["conversion_date"]).days >= 30]
    immature_users = [u for u in users if (CUTOFF - u["conversion_date"]).days < 30]
    ltv_sum = Decimal("0")
    for u in mature_users:
        conv = u["conversion_date"]
        window_end = conv + timedelta(days=30)
        total = sum((r["amount"] for r in revenue
                    if r["user_id"] == u["user_id"] and conv <= r["txn_date"] <= window_end),
                   Decimal("0"))
        ltv_sum += total
    ltv_d30 = ratio(ltv_sum, Decimal(len(mature_users))) if mature_users else Decimal("NaN")

    # 5. ROAS, 6. ROMI - весь период
    total_revenue = sum((r["amount"] for r in revenue), Decimal("0"))
    roas = ratio(total_revenue, total_spend, digits=Decimal("0.001"))
    romi = ratio(total_revenue - total_spend, total_spend, digits=Decimal("0.0001"))

    # 7. ROI (LTV:CAC)
    roi = ratio(ltv_d30 - cac, cac, digits=Decimal("0.0001"))

    # 8. Retention/Churn D30 - зрелые клиенты, доход на 30-й день или позже
    retained = 0
    for u in mature_users:
        d30 = u["conversion_date"] + timedelta(days=30)
        has_late_txn = any(r["user_id"] == u["user_id"] and r["txn_date"] >= d30 for r in revenue)
        if has_late_txn:
            retained += 1
    retention_d30 = ratio(Decimal(retained), Decimal(len(mature_users)), digits=Decimal("0.0001")) if mature_users else Decimal("NaN")
    churn_d30 = (Decimal("1") - retention_d30).quantize(Decimal("0.0001")) if mature_users else Decimal("NaN")

    # --- вывод -----------------------------------------------------------
    print(f"лидов: {len(leads)}, конвертировано: {len(users)}")
    print(f"зрелых для D30: {len(mature_users)}, незрелых: {len(immature_users)}")
    print()
    print("1. CPL (грн/лид, платные каналы):")
    for c in sorted(PAID_CHANNELS):
        print(f"   {c}: {cpl[c]} ({leads_by_channel.get(c,0)} лидов, {spend_by_channel[c]:.2f} грн)")
    print("2. CPA (грн/клиент, платные каналы):")
    for c in sorted(PAID_CHANNELS):
        print(f"   {c}: {cpa[c]} ({conv_by_channel.get(c,0)} клиентов)")
    print(f"3. CAC (смешанный, все каналы): {cac} грн ({total_conversions} клиентов, {total_spend:.2f} грн)")
    print(f"4. LTV_D30 (только зрелые): {ltv_d30} грн (n={len(mature_users)})")
    print(f"5. ROAS: {roas}")
    print(f"6. ROMI: {romi} ({(romi*100):.2f}%)")
    print(f"7. ROI (LTV:CAC): {roi} ({(roi*100):.2f}%)")
    print(f"8. Retention_D30: {retention_d30} ({(retention_d30*100):.2f}%), Churn_D30: {churn_d30} ({(churn_d30*100):.2f}%)")

    def write_csv(name: str, header: list[str], rows: list[list]) -> None:
        with (HERE / name).open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\r\n")
            w.writerow(header)
            w.writerows(rows)

    write_csv("ref_channel_metrics.csv",
              ["channel", "leads", "conversions", "spend_uah", "cpl", "cpa"],
              [[c, leads_by_channel.get(c, 0), conv_by_channel.get(c, 0), f"{spend_by_channel[c]:.2f}",
                str(cpl[c]), str(cpa[c])] for c in sorted(PAID_CHANNELS)])

    write_csv("ref_business_metrics.csv",
              ["метрика", "значение", "n"],
              [["CAC", str(cac), total_conversions],
               ["LTV_D30", str(ltv_d30), len(mature_users)],
               ["ROAS", str(roas), total_conversions],
               ["ROMI", str(romi), total_conversions],
               ["ROI_LTV_CAC", str(roi), len(mature_users)],
               ["Retention_D30", str(retention_d30), len(mature_users)],
               ["Churn_D30", str(churn_d30), len(mature_users)]])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
