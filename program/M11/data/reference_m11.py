"""Эталонные числа модуля M11 (Доменный пакет — fintech, кредитование).

Запуск (после generate_m11.py): python reference_m11.py

Правило двойного авторства: реализация не переиспользует внутренние
списки генератора, читает три CSV заново.

Канон модуля — восемь метрик, каждая с базой и определением:

1. Approval rate — доля одобренных заявок от всех поданных.
2. FPD (First Payment Default) — доля займов, не погашенных РОВНО в
   срок (due_date); любая просрочка, от 1 дня, засчитывается.
3. FPD30 — доля займов, просроченных на 30+ дней относительно
   due_date (включая непогашенные вовсе на дату выгрузки).
4. Roll rate 30→60 — среди займов, просроченных на 30+ дней на
   контрольную дату due_date+30, доля тех, что остаются просроченными
   на 60+ дней к due_date+60. Считается только по займам, у которых
   due_date+60 уже наступил на дату выгрузки (иначе статус на 60-й
   день неизвестен).
5. Винтажный анализ — доля займов с просрочкой 60+ дней на дату
   выгрузки, по месяцу выдачи (origination_date), только по зрелым
   займам (due_date+60 <= дата выгрузки).
6. Repeat customer rate — доля заявителей (среди получивших хотя бы
   один заём), у которых займов больше одного.
7. Средний чек — средний размер займа (principal) по всем выданным.
8. CAC на выданный заём — общий маркетинговый бюджет периода / число
   выданных займов.
"""

from __future__ import annotations

import csv
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

CUTOFF = date(2026, 8, 1)
TWO = Decimal("0.01")
FOUR = Decimal("0.0001")


def ratio(a, b, digits=FOUR):
    if b == 0:
        return Decimal("NaN")
    return (Decimal(a) / Decimal(b)).quantize(digits, rounding=ROUND_HALF_UP)


def read_applications():
    rows = []
    with open("raw/applications.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            rows.append({
                "application_id": r["application_id"],
                "applicant_id": r["applicant_id"],
                "applied_date": date.fromisoformat(r["applied_date"]),
                "approved": r["approved"] == "True",
            })
    return rows


def read_loans():
    rows = []
    with open("raw/loans.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            rows.append({
                "loan_id": r["loan_id"],
                "applicant_id": r["applicant_id"],
                "origination_date": date.fromisoformat(r["origination_date"]),
                "due_date": date.fromisoformat(r["due_date"]),
                "principal": Decimal(r["principal"]),
                "resolution_days": int(r["resolution_days"]) if r["resolution_days"] else None,
            })
    return rows


def read_spend():
    with open("raw/marketing_spend.csv", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    return Decimal(rows[0]["spend_uah"])


def main():
    applications = read_applications()
    loans = read_loans()
    spend = read_spend()

    # 1. Approval rate
    approved_n = sum(1 for a in applications if a["approved"])
    approval_rate = ratio(approved_n, len(applications))

    # 2. FPD, 3. FPD30
    fpd_n = sum(1 for l in loans if l["resolution_days"] != 0)
    fpd30_n = sum(1 for l in loans
                 if l["resolution_days"] is None or l["resolution_days"] >= 30)
    fpd = ratio(fpd_n, len(loans))
    fpd30 = ratio(fpd30_n, len(loans))

    # 4. Roll rate 30->60 (только займы, у которых due_date+60 <= CUTOFF)
    mature60 = [l for l in loans if (CUTOFF - l["due_date"]).days >= 60]
    bucket30 = [l for l in mature60
               if l["resolution_days"] is None or l["resolution_days"] > 30]
    rolled60 = [l for l in bucket30
               if l["resolution_days"] is None or l["resolution_days"] > 60]
    roll_rate = ratio(len(rolled60), len(bucket30))

    # 5. Винтаж по месяцу выдачи (только зрелые займы)
    vintage: dict[str, list] = {}
    for l in mature60:
        month = l["origination_date"].strftime("%Y-%m")
        vintage.setdefault(month, []).append(
            1 if (l["resolution_days"] is None or l["resolution_days"] > 60) else 0)
    vintage_rates = {m: ratio(sum(v), len(v)) for m, v in sorted(vintage.items())}

    # 6. Repeat customer rate
    loans_per_applicant: dict[str, int] = {}
    for l in loans:
        loans_per_applicant[l["applicant_id"]] = loans_per_applicant.get(l["applicant_id"], 0) + 1
    repeat_n = sum(1 for n in loans_per_applicant.values() if n > 1)
    repeat_rate = ratio(repeat_n, len(loans_per_applicant))

    # 7. Средний чек
    avg_principal = (sum((l["principal"] for l in loans), Decimal("0")) / len(loans)).quantize(TWO, rounding=ROUND_HALF_UP)

    # 8. CAC на заём
    cac = (spend / len(loans)).quantize(TWO, rounding=ROUND_HALF_UP)

    print(f"заявок: {len(applications)}, одобрено: {approved_n}")
    print(f"1. Approval rate: {approval_rate} ({approved_n}/{len(applications)})")
    print(f"2. FPD: {fpd} ({fpd_n}/{len(loans)})")
    print(f"3. FPD30: {fpd30} ({fpd30_n}/{len(loans)})")
    print(f"4. Roll rate 30->60: {roll_rate} ({len(rolled60)}/{len(bucket30)}, зрелых займов {len(mature60)})")
    print("5. Винтаж (доля 60+ dpd по месяцу выдачи, зрелые займы):")
    for m, r in vintage_rates.items():
        print(f"   {m}: {r} (n={len(vintage[m])})")
    print(f"6. Repeat customer rate: {repeat_rate} ({repeat_n}/{len(loans_per_applicant)})")
    print(f"7. Средний чек: {avg_principal}")
    print(f"8. CAC на заём: {cac} (бюджет {spend}, займов {len(loans)})")

    def write_csv(name, header, rows):
        with open(name, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\r\n")
            w.writerow(header)
            w.writerows(rows)

    write_csv("ref_funnel_metrics.csv", ["метрика", "значение", "n"],
             [["approval_rate", str(approval_rate), len(applications)],
              ["fpd", str(fpd), len(loans)],
              ["fpd30", str(fpd30), len(loans)],
              ["roll_rate_30_60", str(roll_rate), len(bucket30)]])

    write_csv("ref_vintage.csv", ["месяц_выдачи", "доля_60plus_dpd", "n"],
             [[m, str(r), len(vintage[m])] for m, r in vintage_rates.items()])

    write_csv("ref_business_metrics_m11.csv", ["метрика", "значение", "n"],
             [["repeat_customer_rate", str(repeat_rate), len(loans_per_applicant)],
              ["средний_чек", str(avg_principal), len(loans)],
              ["cac_на_заём", str(cac), len(loans)]])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
