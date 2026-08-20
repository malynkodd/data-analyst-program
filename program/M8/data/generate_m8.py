"""Генератор датасета M8 (Бизнес- и продуктовые метрики).

Домен fintech (решение 21, п. 2): приложение микрокредитов приобретает
пользователей через маркетинговые каналы; часть лидов конвертируется в
платящих клиентов, часть клиентов со временем перестаёт быть активной.

Категория — синтетика учебного модуля с генератором (решение 29).

Запуск:

    python program\\M8\\data\\generate_m8.py

Пишет `program/M8/data/raw/` (в `.gitignore`) и печатает контрольную
точку. Детерминирован — `SEED` фиксирован до первого обращения к
`random`.

Дата выгрузки ("сегодня" внутри задачи) — 2026-05-15. Лиды приходят
2026-01-01..2026-04-30. Из-за этого апрельская когорта расколота: лиды
1-14 апреля успевают дожить до 30 дней наблюдения на дату выгрузки,
15-30 апреля - нет. Раскол намеренный (см. таблицу дефектов
`step-00.md`) - без него любая формула retention D30 "случайно" сходится,
не различая созревшую и незрелую когорту.
"""

from __future__ import annotations

import csv
import hashlib
import random
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

SEED = 20260822
random.seed(SEED)

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"

SIGNUP_START = date(2026, 1, 1)
SIGNUP_END = date(2026, 4, 30)
CUTOFF = date(2026, 5, 15)  # дата выгрузки

CHANNELS = {
    # канал: (доля лидов, конверсия в платящего клиента)
    "google_ads": (0.35, 0.28),
    "facebook_ads": (0.30, 0.24),
    "referral": (0.15, 0.40),
    "organic": (0.20, 0.45),
}
PAID_CHANNELS = {"google_ads", "facebook_ads", "referral"}  # organic - без прямых затрат

TWO = Decimal("0.01")


def money(v) -> Decimal:
    return Decimal(str(v)).quantize(TWO, rounding=ROUND_HALF_UP)


def daterange(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)

    channel_names = list(CHANNELS.keys())
    weights = [CHANNELS[c][0] for c in channel_names]

    leads: list[dict] = []
    lead_seq = 1
    for day in daterange(SIGNUP_START, SIGNUP_END):
        n_today = random.randint(15, 35)
        for _ in range(n_today):
            channel = random.choices(channel_names, weights=weights, k=1)[0]
            leads.append({
                "lead_id": f"L{lead_seq:06d}",
                "channel": channel,
                "signup_date": day,
            })
            lead_seq += 1

    # --- конверсия в платящего клиента -----------------------------------
    users: list[dict] = []
    user_seq = 1
    for lead in leads:
        _, conv_rate = CHANNELS[lead["channel"]]
        if random.random() < conv_rate:
            # конверсия случается 1-5 дней после регистрации
            conv_date = lead["signup_date"] + timedelta(days=random.randint(1, 5))
            if conv_date > CUTOFF:
                continue  # ещё не успел конвертироваться к дате выгрузки
            user = {
                "user_id": f"U{user_seq:06d}",
                "lead_id": lead["lead_id"],
                "channel": lead["channel"],
                "conversion_date": conv_date,
            }
            users.append(user)
            lead["user_id"] = user["user_id"]
            lead["conversion_date"] = conv_date
            user_seq += 1
        else:
            lead["user_id"] = ""
            lead["conversion_date"] = None

    # --- доход: транзакции раз в ~7 дней, до дня оттока или до CUTOFF ----
    revenue: list[dict] = []
    for u in users:
        days_available = (CUTOFF - u["conversion_date"]).days
        churn_day = int(random.expovariate(1 / 55))  # средний срок жизни ~55 дней
        churn_day = max(5, min(churn_day, 400))
        u["churn_day"] = churn_day  # для наглядности задания генератора; не пишется в CSV
        last_active_day = min(churn_day, days_available)
        day_offset = random.randint(1, 4)  # первая транзакция через 1-4 дня
        txn_seq_local = 0
        while day_offset <= last_active_day:
            amount = money(random.uniform(80, 1500))
            revenue.append({
                "user_id": u["user_id"],
                "txn_date": u["conversion_date"] + timedelta(days=day_offset),
                "amount": amount,
            })
            txn_seq_local += 1
            day_offset += random.randint(5, 9)

    # --- затраты по каналам, помесячно -------------------------------------
    spend_rows: list[dict] = []
    months = sorted({month_key(d) for d in daterange(SIGNUP_START, SIGNUP_END)})
    for channel in channel_names:
        if channel not in PAID_CHANNELS:
            continue
        for m in months:
            base = {"google_ads": 45000, "facebook_ads": 32000, "referral": 9000}[channel]
            spend = money(base * random.uniform(0.85, 1.2))
            spend_rows.append({"channel": channel, "month": m, "spend_uah": spend})

    # --- запись файлов -----------------------------------------------------
    with (RAW / "leads.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["lead_id", "channel", "signup_date", "user_id", "conversion_date"])
        for l in leads:
            conv = l.get("conversion_date")
            w.writerow([l["lead_id"], l["channel"], l["signup_date"].isoformat(), l["user_id"],
                       conv.isoformat() if conv else ""])

    with (RAW / "revenue.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["user_id", "txn_date", "amount"])
        for r in sorted(revenue, key=lambda r: (r["user_id"], r["txn_date"])):
            w.writerow([r["user_id"], r["txn_date"].isoformat(), f"{r['amount']:.2f}"])

    with (RAW / "channel_spend.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["channel", "month", "spend_uah"])
        for s in sorted(spend_rows, key=lambda r: (r["channel"], r["month"])):
            w.writerow([s["channel"], s["month"], f"{s['spend_uah']:.2f}"])

    def sha256_of(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    print("Датасет M8 записан в", RAW)
    print("SEED =", SEED)
    print()
    print(f"{'файл':<20}{'строк данных':>14}  sha256")
    for name in ("leads.csv", "revenue.csv", "channel_spend.csv"):
        path = RAW / name
        rows = sum(1 for _ in path.open(encoding="utf-8")) - 1
        print(f"{name:<20}{rows:>14}  {sha256_of(path)}")

    print()
    print("Инварианты:")
    print(f"  лидов всего: {len(leads)}")
    print(f"  конвертировано в клиентов: {len(users)}")
    print(f"  транзакций дохода: {len(revenue)}")
    print(f"  дата выгрузки: {CUTOFF.isoformat()}")
    mature = [u for u in users if (CUTOFF - u['conversion_date']).days >= 30]
    immature = [u for u in users if (CUTOFF - u['conversion_date']).days < 30]
    print(f"  клиентов зрелых для retention D30 (>=30 дней с конверсии): {len(mature)}")
    print(f"  клиентов незрелых (<30 дней с конверсии на дату выгрузки): {len(immature)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
