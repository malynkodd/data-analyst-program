"""Генератор датасета P2 — конверсия в первую оплату, сервис подписки.

Период регистраций: 2025-01-01 .. 2025-12-31 (12 месяцев). Пишет
program/P2/data/raw/signups.csv и raw/payments.csv.

Три встроенных дефекта (часть 5 blueprint, P2):
1. Дубли платежей от ретраев шлюза — один и тот же успешный платёж
   иногда появляется двумя строками (тот же user_id, та же сумма,
   секунды разницы во времени).
2. Часть пользователей регистрируется дважды с одним email (два разных
   user_id) — обнаруживается только по email, не по user_id.
3. Три канала (organic, paid_social, referral) с разной и меняющейся
   долей регистраций месяц к месяцу — намеренно так, что доля
   paid_social (канал с самой низкой конверсией) растёт от месяца к
   месяцу, создавая симпсоновский парадокс: конверсия каждого канала
   растёт помесячно, а смешанная — падает, потому что доля дешёвого
   канала растёт быстрее.

SEED зафиксирован до первого обращения к random (решение 29).
"""
import csv
import hashlib
import random
from datetime import date, datetime, timedelta
from pathlib import Path

SEED = 20260821
random.seed(SEED)

OUT_DIR = Path(__file__).resolve().parent / "raw"
OUT_DIR.mkdir(exist_ok=True)

MONTHS = [date(2025, m, 1) for m in range(1, 13)]

# canal -> (базовая конверсия в месяц 1, прирост конверсии за месяц,
#           базовая доля регистраций, изменение доли за месяц)
CHANNELS = {
    "organic":     (0.42, 0.010, 0.55, -0.028),
    "referral":    (0.55, 0.010, 0.15, -0.007),
    "paid_social": (0.20, 0.002, 0.30, 0.035),
}

REG_PER_MONTH = 1400  # среднее число регистраций в месяц (шум +-10%)
DUP_ACCOUNT_RATE = 0.04   # доля пользователей с повторной регистрацией по тому же email
RETRY_DUPLICATE_RATE = 0.06  # доля успешных платежей, задвоенных ретраем
RETENTION_BASE = 0.86  # вероятность продлить подписку на следующий месяц
DATA_CUTOFF = date(2026, 6, 30)  # платежи после этой даты не пишутся (наблюдение закрыто)


def add_payment_with_renewals(payments: list, payment_id: int, user_id: int,
                               first_ts: datetime, amount: float) -> int:
    """Пишет первый платёж и цепочку продлений (retention) с шансом ретрай-дубля
    на каждом. Останавливается на churn или на DATA_CUTOFF. Возвращает следующий
    свободный payment_id."""
    ts = first_ts
    month_no = 0
    while ts.date() <= DATA_CUTOFF:
        payments.append((payment_id, user_id, ts, amount))
        payment_id += 1
        if random.random() < RETRY_DUPLICATE_RATE:
            dup_ts = ts + timedelta(seconds=random.randint(3, 120))
            payments.append((payment_id, user_id, dup_ts, amount))
            payment_id += 1
        month_no += 1
        retain_prob = RETENTION_BASE * (0.985 ** month_no)  # retention чуть слабеет со временем
        if random.random() >= retain_prob:
            break  # churn
        ts = ts + timedelta(days=30, hours=random.randint(-6, 6))
    return payment_id


def month_days(d: date) -> int:
    nxt = date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)
    return (nxt - d).days


def main() -> None:
    signups = []  # user_id, email, signup_date, channel
    payments = []  # payment_id, user_id, payment_ts, amount

    user_id = 1
    payment_id = 1
    email_pool: dict[int, str] = {}  # user_id -> email, для дублей аккаунтов

    for m_idx, month_start in enumerate(MONTHS):
        days = month_days(month_start)
        n_reg = round(REG_PER_MONTH * random.uniform(0.9, 1.1))

        # доли каналов на этот месяц, нормализованные
        shares = {}
        for ch, (conv0, conv_step, share0, share_step) in CHANNELS.items():
            shares[ch] = max(0.02, share0 + share_step * m_idx)
        total_share = sum(shares.values())
        shares = {ch: s / total_share for ch, s in shares.items()}

        for _ in range(n_reg):
            ch = random.choices(list(shares), weights=list(shares.values()))[0]
            conv0, conv_step, *_ = CHANNELS[ch]
            conv_rate = min(0.95, conv0 + conv_step * m_idx)

            reg_day = month_start + timedelta(days=random.randint(0, days - 1))
            email = f"user{user_id}@example.test"
            signups.append((user_id, email, reg_day.isoformat(), ch))
            email_pool[user_id] = email

            converts = random.random() < conv_rate
            if converts:
                lag = random.randint(1, 45)
                pay_ts = datetime.combine(reg_day, datetime.min.time()) + timedelta(
                    days=lag, hours=random.randint(0, 23), minutes=random.randint(0, 59))
                amount = round(random.uniform(199, 999), 2)
                payment_id = add_payment_with_renewals(payments, payment_id, user_id, pay_ts, amount)

            user_id += 1

    # дубли аккаунтов: часть пользователей регистрируется повторно тем же email,
    # в течение 0-14 дней от первой регистрации, в том же канале.
    original_users = list(range(1, user_id))
    n_dup = round(len(original_users) * DUP_ACCOUNT_RATE)
    for orig_uid in random.sample(original_users, n_dup):
        orig_email = email_pool[orig_uid]
        orig_signup = next(s for s in signups if s[0] == orig_uid)
        reg_day = min(
            date.fromisoformat(orig_signup[2]) + timedelta(days=random.randint(0, 14)),
            date(2025, 12, 31),
        )
        ch = orig_signup[3]
        signups.append((user_id, orig_email, reg_day.isoformat(), ch))
        # у повторного аккаунта конверсия считается независимо, тем же каналом
        conv0, conv_step, *_ = CHANNELS[ch]
        m_idx = reg_day.month - 1
        conv_rate = min(0.95, conv0 + conv_step * m_idx)
        if random.random() < conv_rate:
            lag = random.randint(1, 45)
            pay_ts = datetime.combine(reg_day, datetime.min.time()) + timedelta(
                days=lag, hours=random.randint(0, 23), minutes=random.randint(0, 59))
            amount = round(random.uniform(199, 999), 2)
            payment_id = add_payment_with_renewals(payments, payment_id, user_id, pay_ts, amount)
        user_id += 1

    signups.sort(key=lambda r: r[0])
    payments.sort(key=lambda r: r[0])

    signups_path = OUT_DIR / "signups.csv"
    with signups_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["user_id", "email", "signup_date", "channel"])
        w.writerows(signups)

    payments_path = OUT_DIR / "payments.csv"
    with payments_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["payment_id", "user_id", "payment_ts", "amount"])
        for pid, uid, ts, amt in payments:
            w.writerow([pid, uid, ts.strftime("%Y-%m-%d %H:%M:%S"), amt])

    for p in (signups_path, payments_path):
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        n = len(p.read_text(encoding="utf-8").splitlines()) - 1
        print(f"{p.name}: {n} строк, sha256 {digest}")


if __name__ == "__main__":
    main()
