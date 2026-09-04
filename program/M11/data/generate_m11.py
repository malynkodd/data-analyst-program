"""Генератор датасета M11 (Доменный пакет — fintech, кредитование).

Домен fintech (решение 21, п. 2; часть 4 blueprint, «Решение 2» —
операционные метрики кредитования): тот же сервис микрокредитов, что в
M8, только со стороны кредитного портфеля, а не привлечения клиентов.

Категория — синтетика учебного модуля с генератором (решение 29).

Запуск: python program\\M11\\data\\generate_m11.py
Пишет `program/M11/data/raw/` (в `.gitignore`) и печатает контрольную
точку. SEED фиксирован до первого обращения к random.

Дата выгрузки ("сегодня") — 2026-08-01. Заявки приходят 2026-01-01..
2026-06-30 (полгода). Срок займа — 14 дней, поэтому июньская когорта
раскалывается на зрелую и незрелую для метрик, требующих возраста займа
>=60 дней (винтажный анализ), тем же приёмом, что в M8.
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

SEED = 20260827
random.seed(SEED)

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"

APP_START = date(2026, 1, 1)
APP_END = date(2026, 6, 30)
CUTOFF = date(2026, 8, 1)
LOAN_TERM_DAYS = 14

N_APPLICANTS = 2200
APPLICANT_IDS = [f"APL-{i:05d}" for i in range(1, N_APPLICANTS + 1)]
TWO = Decimal("0.01")


def money(v) -> Decimal:
    return Decimal(str(v)).quantize(TWO, rounding=ROUND_HALF_UP)


def daterange(start, end):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)

    # у каждого заявителя — истинный кредитный рейтинг (не наблюдается
    # напрямую, определяет вероятность одобрения и вероятность просрочки)
    true_score = {a: random.gauss(640, 90) for a in APPLICANT_IDS}

    applications: list[dict] = []
    app_seq = 1
    for day in daterange(APP_START, APP_END):
        n_today = random.randint(14, 22)
        for _ in range(n_today):
            applicant = random.choice(APPLICANT_IDS)
            score = true_score[applicant] + random.gauss(0, 15)  # шум скоринга
            approved = score > 600
            applications.append({
                "application_id": f"A{app_seq:06d}",
                "applicant_id": applicant,
                "applied_date": day,
                "requested_amount": money(random.uniform(500, 8000)),
                "score": round(score),
                "approved": approved,
            })
            app_seq += 1

    # --- одобренные заявки становятся займами (5% отваливается на этапе
    # оформления - клиент передумал) ------------------------------------
    loans: list[dict] = []
    loan_seq = 1
    for app in applications:
        if not app["approved"]:
            continue
        if random.random() < 0.05:
            continue  # передумал оформлять
        origination_date = app["applied_date"] + timedelta(days=random.randint(0, 1))
        due_date = origination_date + timedelta(days=LOAN_TERM_DAYS)
        loans.append({
            "loan_id": f"LN{loan_seq:06d}",
            "application_id": app["application_id"],
            "applicant_id": app["applicant_id"],
            "origination_date": origination_date,
            "due_date": due_date,
            "principal": money(app["requested_amount"] * Decimal(str(round(random.uniform(0.7, 1.0), 2)))),
            "_true_score": true_score[app["applicant_id"]],
        })
        loan_seq += 1

    # --- поведение погашения: чем ниже истинный скор, тем выше риск
    # просрочки; resolution_day_after_due: 0 = в срок, >0 = просрочка на
    # столько дней, None = не погашен вовсе на дату выгрузки (либо
    # списан, либо ещё может заплатить позже) ----------------------------
    for loan in loans:
        risk = max(0.02, min(0.60, (680 - loan["_true_score"]) / 260))
        roll = random.random()
        days_since_due = (CUTOFF - loan["due_date"]).days
        if roll > risk:
            # платит вовремя или почти вовремя
            resolution = 0 if random.random() < 0.85 else random.randint(1, 5)
        else:
            # уходит в просрочку; часть в итоге платит позже, часть - нет
            late_stage = random.random()
            if late_stage < 0.35:
                resolution = random.randint(6, 29)      # платит с опозданием до 30 дней
            elif late_stage < 0.55:
                resolution = random.randint(30, 59)     # платит с опозданием 30-60
            elif late_stage < 0.70:
                resolution = random.randint(60, 89)     # платит с опозданием 60-90
            else:
                resolution = None                        # не платит вовсе (в перспективе списание)
        if resolution is not None and resolution > days_since_due:
            # ещё не успел заплатить настолько поздно к дате выгрузки
            resolution = None if days_since_due < 0 else min(resolution, days_since_due)
            if days_since_due < 0:
                resolution = None
        loan["resolution_days"] = resolution  # None или число дней сверх due_date
        del loan["_true_score"]

    # --- стоимость привлечения (упрощённо: один общий бюджет на период) -
    total_marketing_spend = money(len(loans) * random.uniform(55, 75))

    # --- запись файлов -----------------------------------------------------
    with (RAW / "applications.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["application_id", "applicant_id", "applied_date",
                   "requested_amount", "score", "approved"])
        for a in applications:
            w.writerow([a["application_id"], a["applicant_id"], a["applied_date"].isoformat(),
                       f"{a['requested_amount']:.2f}", a["score"], a["approved"]])

    with (RAW / "loans.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["loan_id", "application_id", "applicant_id", "origination_date",
                   "due_date", "principal", "resolution_days"])
        for l in loans:
            w.writerow([l["loan_id"], l["application_id"], l["applicant_id"],
                       l["origination_date"].isoformat(), l["due_date"].isoformat(),
                       f"{l['principal']:.2f}",
                       "" if l["resolution_days"] is None else l["resolution_days"]])

    with (RAW / "marketing_spend.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["период", "spend_uah"])
        w.writerow(["2026-01..2026-06", f"{total_marketing_spend:.2f}"])

    def sha256_of(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    print("Датасет M11 записан в", RAW)
    print("SEED =", SEED)
    print()
    print(f"{'файл':<22}{'строк данных':>14}  sha256")
    for name in ("applications.csv", "loans.csv", "marketing_spend.csv"):
        path = RAW / name
        rows = sum(1 for _ in path.open(encoding="utf-8")) - 1
        print(f"{name:<22}{rows:>14}  {sha256_of(path)}")

    approved_n = sum(1 for a in applications if a["approved"])
    print()
    print("Инварианты:")
    print(f"  заявок: {len(applications)}, одобрено: {approved_n} ({approved_n/len(applications):.1%})")
    print(f"  займов выдано: {len(loans)}")
    print(f"  дата выгрузки: {CUTOFF.isoformat()}")
    mature = [l for l in loans if (CUTOFF - l["due_date"]).days >= 60]
    print(f"  займов зрелых (>=60 дней с due_date до выгрузки): {len(mature)} из {len(loans)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
