"""Эталонный расчёт P5 — независимо от generate_p5.py.

Каждая метрика — своя функция с докстрокой (база, ключ, окно зрелости).
Печатает контрольную точку и пишет:
  ref_funnel_metrics.csv        — approval_rate, fpd, fpd30, roll_rate_30_60
  ref_vintage.csv               — 12 строк, когорты 2025-01..2025-12
  ref_business_metrics_p5.csv   — repeat_customer_rate, avg_ticket, cac_per_loan
  ref_default_comparison.csv    — до/после смены скоринга, 30dpd и 90dpd
"""
from __future__ import annotations

import csv
import hashlib
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"

CUTOFF = date(2026, 7, 1)
SCORE_CHANGE = date(2026, 4, 1)


def read_csv(name):
    with (RAW / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def d(s: str) -> date:
    return date.fromisoformat(s)


def main() -> int:
    applications = read_csv("applications.csv")
    loans = read_csv("loans.csv")
    schedule = read_csv("schedule.csv")
    payments = read_csv("payments.csv")
    spend = float(read_csv("marketing_spend.csv")[0]["spend_uah"])

    # --- 1. approval_rate: база — все заявки, ключ — approved == 'True' ---
    approved_n = sum(1 for a in applications if a["approved"] == "True")
    approval_rate = approved_n / len(applications)

    # --- 2. avg_ticket: средний principal по ВСЕМ выданным займам --------
    principals = [float(l["principal"]) for l in loans]
    avg_ticket = sum(principals) / len(principals)

    # --- собрать по каждому installment фактический dpd_strict -----------
    # dpd_strict = (факт.дата платежа - дата по графику).days, если оплачен;
    # иначе (CUTOFF - дата по графику).days -- пролонгация не меняет эту
    # величину: график (schedule.csv) неизменен, extended -- только у
    # payments.csv, справочно (решение по обработке пролонгаций — P5.project.md).
    sched_by_key = {(s["loan_id"], int(s["installment_no"])): d(s["due_date"]) for s in schedule}
    dpd = {}  # (loan_id, installment_no) -> int dpd_strict
    for p in payments:
        key = (p["loan_id"], int(p["installment_no"]))
        due = sched_by_key[key]
        if p["paid_date"]:
            dpd[key] = (d(p["paid_date"]) - due).days
        else:
            dpd[key] = (CUTOFF - due).days

    loans_by_id = {l["loan_id"]: l for l in loans}

    # --- 3-4. FPD / FPD30: только installment_no == 1, только «зрелые» ---
    # fpd зрелость: due_date(installment 1) <= CUTOFF (origination <= 2026-06-01)
    # fpd30 зрелость: due_date(installment 1) + 30 <= CUTOFF (origination <= 2026-05-02)
    fpd_mature = []
    fpd30_mature = []
    for key, due in sched_by_key.items():
        loan_id, no = key
        if no != 1:
            continue
        if due <= CUTOFF:
            fpd_mature.append(key)
        if due + timedelta(days=30) <= CUTOFF:
            fpd30_mature.append(key)

    fpd = sum(1 for k in fpd_mature if dpd[k] > 0) / len(fpd_mature)
    fpd30 = sum(1 for k in fpd30_mature if dpd[k] >= 30) / len(fpd30_mature)

    # --- «зрелость» для винтажа / roll rate / default_90: последний
    # платёж (installment 3) должен быть due, и должно пройти ещё 90 дней
    # сверх его due_date, чтобы знать итоговый (не censored) статус ------
    ever90_mature_loans = []
    for loan_id, l in loans_by_id.items():
        due3 = sched_by_key[(loan_id, 3)]
        if due3 + timedelta(days=90) <= CUTOFF:
            ever90_mature_loans.append(loan_id)

    worst_dpd = {}
    ever90 = {}
    ever60 = {}
    for loan_id in ever90_mature_loans:
        vals = [dpd[(loan_id, i)] for i in (1, 2, 3)]
        worst_dpd[loan_id] = max(vals)
        ever90[loan_id] = worst_dpd[loan_id] >= 90
        ever60[loan_id] = worst_dpd[loan_id] >= 60

    # --- 5. roll_rate_30_60: среди зрелых, «уже была в 30-корзине» -------
    in_30 = [lid for lid in ever90_mature_loans if worst_dpd[lid] >= 30]
    still_60 = [lid for lid in in_30 if worst_dpd[lid] >= 60]
    roll_rate = len(still_60) / len(in_30)

    # --- 6. vintage: доля ever_60 по когорте месяца выдачи, 2025 целиком -
    vintage_rows = []
    for m in range(1, 13):
        month_start = date(2025, m, 1)
        month_end = date(2025, m + 1, 1) if m < 12 else date(2026, 1, 1)
        cohort = [lid for lid in ever90_mature_loans
                  if month_start <= d(loans_by_id[lid]["origination_date"]) < month_end]
        share = sum(1 for lid in cohort if ever60[lid]) / len(cohort)
        vintage_rows.append((month_start.strftime("%Y-%m"), round(share, 4), len(cohort)))

    # --- 7. repeat_customer_rate: доля заявителей с >1 займом (не заявкой)
    loans_per_applicant: dict[str, int] = {}
    for l in loans:
        loans_per_applicant[l["applicant_id"]] = loans_per_applicant.get(l["applicant_id"], 0) + 1
    repeat_rate = sum(1 for n in loans_per_applicant.values() if n > 1) / len(loans_per_applicant)

    # --- 8. cac_per_loan: бюджет / число ВЫДАННЫХ займов ------------------
    cac = spend / len(loans)

    # --- Основной вопрос проекта: default rate до/после SCORE_CHANGE,
    # отдельно на 30dpd (быстрый сигнал) и 90dpd (полный горизонт) --------
    before_fpd30 = [k for k in fpd30_mature if d(loans_by_id[k[0]]["origination_date"]) < SCORE_CHANGE]
    after_fpd30 = [k for k in fpd30_mature if d(loans_by_id[k[0]]["origination_date"]) >= SCORE_CHANGE]
    rate_30_before = sum(1 for k in before_fpd30 if dpd[k] >= 30) / len(before_fpd30)
    rate_30_after = (sum(1 for k in after_fpd30 if dpd[k] >= 30) / len(after_fpd30)) if after_fpd30 else None

    before_90 = [lid for lid in ever90_mature_loans if d(loans_by_id[lid]["origination_date"]) < SCORE_CHANGE]
    after_90 = [lid for lid in ever90_mature_loans if d(loans_by_id[lid]["origination_date"]) >= SCORE_CHANGE]
    rate_90_before = sum(1 for lid in before_90 if ever90[lid]) / len(before_90)
    rate_90_after = (sum(1 for lid in after_90 if ever90[lid]) / len(after_90)) if after_90 else None

    # --- запись файлов -----------------------------------------------------
    with (HERE / "ref_funnel_metrics.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["метрика", "значение", "n"])
        w.writerow(["approval_rate", round(approval_rate, 4), len(applications)])
        w.writerow(["fpd", round(fpd, 4), len(fpd_mature)])
        w.writerow(["fpd30", round(fpd30, 4), len(fpd30_mature)])
        w.writerow(["roll_rate_30_60", round(roll_rate, 4), len(in_30)])

    with (HERE / "ref_vintage.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["месяц_выдачи", "доля_60plus_dpd", "n"])
        w.writerows(vintage_rows)

    with (HERE / "ref_business_metrics_p5.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["метрика", "значение", "n"])
        w.writerow(["repeat_customer_rate", round(repeat_rate, 4), len(loans_per_applicant)])
        w.writerow(["avg_ticket", round(avg_ticket, 2), len(loans)])
        w.writerow(["cac_per_loan", round(cac, 2), len(loans)])

    with (HERE / "ref_default_comparison.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["определение", "период", "значение", "n"])
        w.writerow(["fpd30", "до 2026-04-01", round(rate_30_before, 4), len(before_fpd30)])
        w.writerow(["fpd30", "с 2026-04-01", "" if rate_30_after is None else round(rate_30_after, 4), len(after_fpd30)])
        w.writerow(["ever_90dpd", "до 2026-04-01", round(rate_90_before, 4), len(before_90)])
        w.writerow(["ever_90dpd", "с 2026-04-01", "" if rate_90_after is None else round(rate_90_after, 4), len(after_90)])

    def sha256_of(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    print("Контрольная точка P5 (прогон на машине автора)")
    print()
    print(f"approval_rate:   {approval_rate:.4f} ({approved_n}/{len(applications)})")
    print(f"avg_ticket:      {avg_ticket:.2f} грн ({len(loans)} займов)")
    print(f"fpd:             {fpd:.4f} (n={len(fpd_mature)})")
    print(f"fpd30:           {fpd30:.4f} (n={len(fpd30_mature)})")
    print(f"roll_rate_30_60: {roll_rate:.4f} ({len(still_60)}/{len(in_30)}, зрелых для 90dpd {len(ever90_mature_loans)})")
    print(f"repeat_customer_rate: {repeat_rate:.4f} ({sum(1 for n in loans_per_applicant.values() if n>1)}/{len(loans_per_applicant)})")
    print(f"cac_per_loan:    {cac:.2f} грн (бюджет {spend:.2f} / {len(loans)} займов)")
    print()
    print("Default rate до/после смены скоринга 2026-04-01:")
    print(f"  fpd30:      до {rate_30_before:.4f} (n={len(before_fpd30)}), после "
          f"{'нет данных' if rate_30_after is None else f'{rate_30_after:.4f} (n={len(after_fpd30)})'}")
    print(f"  ever_90dpd: до {rate_90_before:.4f} (n={len(before_90)}), после "
          f"{'нет зрелых когорт' if rate_90_after is None else f'{rate_90_after:.4f} (n={len(after_90)})'} "
          f"(n={len(after_90)})")
    print()
    for name in ("ref_funnel_metrics.csv", "ref_vintage.csv", "ref_business_metrics_p5.csv",
                 "ref_default_comparison.csv"):
        path = HERE / name
        print(f"{name}: sha256 {sha256_of(path)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
