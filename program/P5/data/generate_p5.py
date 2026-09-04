"""Генератор датасета P5 — «Портфель просрочки», риск-менеджер МФО.

Домен fintech, тот же кредитный продукт, что в M11, но со своей
историей (часть 5 blueprint, P5): скоринг ужесточён 2026-04-01 (ровно
за три месяца до даты выгрузки) — «стало ли лучше?». Заём — три
ежемесячных платежа (не один лямп-сам, как в M11), поэтому есть
отдельно график платежей (`schedule.csv`, неизменная договорная дата) и
факт платежей (`payments.csv`, включая пролонгации — сдвиг даты по
факту, не переписывающий график).

Встроенные, обнаруживаемые прогоном эффекты:
1. Скоринг ужесточён 2026-04-01: порог одобрения score>580 -> score>620.
2. Конфаундер: доля канала affiliate (более рискованный пул
   заявителей) падает 60%->25% примерно к тому же времени — улучшение
   после ужесточения скоринга может объясняться и сменой канала.
3. Пролонгации: по части просроченных платежей МФО сдвигает дату на 30
   дней; «дефолт» по расписанию (от исходной даты) и «дефолт» по факту
   (от актуальной даты) — два законных, разных числа.
4. Горизонт: за FPD30 (первый платёж, +60 дней от выдачи) видно уже 2
   когорты после смены скоринга; за «когда-либо 90+ dpd» (нужно +180
   дней от выдачи) — ни одной когорты после смены скоринга не зрело.

Категория — синтетика проекта портфолио с генератором (решение 29).
Запуск: python program\\P5\\data\\generate_p5.py
Пишет `program/P5/data/raw/` (в `.gitignore`) и печатает контрольную
точку. SEED зафиксирован до первого обращения к random.
"""
from __future__ import annotations

import csv
import hashlib
import random
import sys
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

# Кириллица в консоли не полагается на кодировку терминала
# (решение 17; симуляция 2026-09-04, дефект M9-1: без этой строки
# скрипт падал с UnicodeEncodeError, допечатав часть вывода).
sys.stdout.reconfigure(encoding="utf-8")

SEED = 20260822
random.seed(SEED)

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"

APP_START = date(2025, 1, 1)
APP_END = date(2026, 6, 30)
CUTOFF = date(2026, 7, 1)          # дата выгрузки ("сегодня")
SCORE_CHANGE = date(2026, 4, 1)    # скоринг ужесточён ровно за 3 мес. до CUTOFF
N_INSTALLMENTS = 3
INSTALLMENT_STEP_DAYS = 30         # платежи через 30/60/90 дней от выдачи
EXTENSION_TRIGGER_DAYS = 20        # пролонгация рассматривается, если просрочка тянет на 20+ дней
EXTENSION_PROB = 0.40
EXTENSION_SHIFT_DAYS = 30

TWO = Decimal("0.01")


def money(v) -> Decimal:
    return Decimal(str(v)).quantize(TWO, rounding=ROUND_HALF_UP)


def daterange(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


# канал -> (доля до смены скоринга, доля после, среднее true_score, sd true_score)
CHANNELS = {
    "affiliate":   (0.60, 0.25, 600, 65),
    "partner_app": (0.40, 0.75, 655, 60),
}


def channel_shares(day: date) -> dict:
    # линейная растяжка доли на +-45 дней вокруг SCORE_CHANGE, дальше плато
    span = 45
    t = (day - SCORE_CHANGE).days
    frac = max(0.0, min(1.0, (t + span) / (2 * span)))
    shares = {}
    for ch, (share_before, share_after, *_ ) in CHANNELS.items():
        shares[ch] = share_before + (share_after - share_before) * frac
    total = sum(shares.values())
    return {ch: s / total for ch, s in shares.items()}


def approval_threshold(day: date) -> int:
    return 620 if day >= SCORE_CHANGE else 580


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)

    applicant_channel: dict[str, str] = {}
    applicant_true_score: dict[str, float] = {}
    applicant_seq = 1
    active_pool: list[str] = []  # заявители, у которых уже есть хотя бы одна заявка

    applications: list[dict] = []
    app_seq = 1
    REAPPLY_PROB = 0.05  # на каждый день у каждого «старого» заявителя малый шанс подать снова

    for day in daterange(APP_START, APP_END):
        shares = channel_shares(day)
        n_new = random.randint(9, 15)
        n_repeat = sum(1 for _ in active_pool if random.random() < REAPPLY_PROB / len(active_pool) * 30) if active_pool else 0
        # ограничим repeat разумным числом в день, не завязываясь на размер пула построчно
        n_repeat = min(n_repeat, 6)

        for _ in range(n_new):
            ch = random.choices(list(shares), weights=list(shares.values()))[0]
            mean_s, sd_s = CHANNELS[ch][2], CHANNELS[ch][3]
            applicant_id = f"APL-{applicant_seq:05d}"
            applicant_channel[applicant_id] = ch
            applicant_true_score[applicant_id] = random.gauss(mean_s, sd_s)
            active_pool.append(applicant_id)
            applicant_seq += 1

            score = applicant_true_score[applicant_id] + random.gauss(0, 15)
            approved = score > approval_threshold(day)
            applications.append({
                "application_id": f"A{app_seq:06d}",
                "applicant_id": applicant_id,
                "applied_date": day,
                "channel": ch,
                "requested_amount": money(random.uniform(4000, 20000)),
                "score": round(score),
                "approved": approved,
            })
            app_seq += 1

        for _ in range(n_repeat):
            applicant_id = random.choice(active_pool)
            ch = applicant_channel[applicant_id]
            score = applicant_true_score[applicant_id] + random.gauss(0, 15)
            approved = score > approval_threshold(day)
            applications.append({
                "application_id": f"A{app_seq:06d}",
                "applicant_id": applicant_id,
                "applied_date": day,
                "channel": ch,
                "requested_amount": money(random.uniform(4000, 20000)),
                "score": round(score),
                "approved": approved,
            })
            app_seq += 1

    # --- одобренные заявки становятся займами (5% отваливается на этапе
    # оформления, как в M11) ------------------------------------------
    loans: list[dict] = []
    loan_seq = 1
    for app in applications:
        if not app["approved"]:
            continue
        if random.random() < 0.05:
            continue
        origination_date = app["applied_date"] + timedelta(days=random.randint(0, 1))
        loans.append({
            "loan_id": f"LN{loan_seq:06d}",
            "application_id": app["application_id"],
            "applicant_id": app["applicant_id"],
            "channel": app["channel"],
            "origination_date": origination_date,
            "principal": money(app["requested_amount"] * Decimal(str(round(random.uniform(0.7, 1.0), 2)))),
            "_true_score": applicant_true_score[app["applicant_id"]],
        })
        loan_seq += 1

    schedule: list[dict] = []
    payments: list[dict] = []
    for loan in loans:
        risk = max(0.02, min(0.60, (680 - loan["_true_score"]) / 260))
        installment_amount = money(loan["principal"] / N_INSTALLMENTS)
        for i in range(1, N_INSTALLMENTS + 1):
            due_date = loan["origination_date"] + timedelta(days=INSTALLMENT_STEP_DAYS * i)
            schedule.append({
                "loan_id": loan["loan_id"],
                "installment_no": i,
                "due_date": due_date,
                "due_amount": installment_amount,
            })

            roll = random.random()
            if roll > risk:
                dpd_raw = 0 if random.random() < 0.85 else random.randint(1, 5)
            else:
                stage = random.random()
                if stage < 0.35:
                    dpd_raw = random.randint(6, 29)
                elif stage < 0.55:
                    dpd_raw = random.randint(30, 59)
                elif stage < 0.70:
                    dpd_raw = random.randint(60, 89)
                else:
                    dpd_raw = random.randint(90, 150)

            extended = dpd_raw >= EXTENSION_TRIGGER_DAYS and random.random() < EXTENSION_PROB
            extended_due_date = due_date + timedelta(days=EXTENSION_SHIFT_DAYS) if extended else None

            actual_paid_date = due_date + timedelta(days=dpd_raw)
            if actual_paid_date > CUTOFF:
                paid_date_out = ""  # ещё не заплачено на дату выгрузки — censored
            else:
                paid_date_out = actual_paid_date.isoformat()

            payments.append({
                "loan_id": loan["loan_id"],
                "installment_no": i,
                "paid_date": paid_date_out,
                "extended": extended,
                "extended_due_date": extended_due_date.isoformat() if extended_due_date else "",
            })

    # --- маркетинговый бюджет портфеля целиком (та же конвенция, что M11)
    total_marketing_spend = money(len(loans) * random.uniform(70, 95))

    for loan in loans:
        del loan["_true_score"]

    with (RAW / "applications.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["application_id", "applicant_id", "applied_date", "channel",
                    "requested_amount", "score", "approved"])
        for a in applications:
            w.writerow([a["application_id"], a["applicant_id"], a["applied_date"].isoformat(),
                        a["channel"], f"{a['requested_amount']:.2f}", a["score"], a["approved"]])

    with (RAW / "loans.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["loan_id", "application_id", "applicant_id", "channel",
                    "origination_date", "principal"])
        for l in loans:
            w.writerow([l["loan_id"], l["application_id"], l["applicant_id"], l["channel"],
                        l["origination_date"].isoformat(), f"{l['principal']:.2f}"])

    with (RAW / "schedule.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["loan_id", "installment_no", "due_date", "due_amount"])
        for s in schedule:
            w.writerow([s["loan_id"], s["installment_no"], s["due_date"].isoformat(),
                        f"{s['due_amount']:.2f}"])

    with (RAW / "payments.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["loan_id", "installment_no", "paid_date", "extended", "extended_due_date"])
        for p in payments:
            w.writerow([p["loan_id"], p["installment_no"], p["paid_date"], p["extended"],
                        p["extended_due_date"]])

    with (RAW / "marketing_spend.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["период", "spend_uah"])
        w.writerow(["2025-01..2026-06", f"{total_marketing_spend:.2f}"])

    def sha256_of(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    print("Датасет P5 записан в", RAW)
    print("SEED =", SEED)
    print()
    print(f"{'файл':<22}{'строк данных':>14}  sha256")
    for name in ("applications.csv", "loans.csv", "schedule.csv", "payments.csv", "marketing_spend.csv"):
        path = RAW / name
        rows = sum(1 for _ in path.open(encoding="utf-8")) - 1
        print(f"{name:<22}{rows:>14}  {sha256_of(path)}")

    approved_n = sum(1 for a in applications if a["approved"])
    print()
    print("Инварианты:")
    print(f"  заявок: {len(applications)}, одобрено: {approved_n} ({approved_n/len(applications):.1%})")
    print(f"  займов выдано: {len(loans)}")
    print(f"  дата выгрузки: {CUTOFF.isoformat()}, смена скоринга: {SCORE_CHANGE.isoformat()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
