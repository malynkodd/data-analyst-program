"""Эталонный расчёт P2 — независимо от SQL учащегося.

Печатает: контрольную точку, число дублей платежей (ретраи), число
задвоенных аккаунтов и их влияние, помесячную конверсию по каналам и
смешанную (симпсоновский парадокс), обе трактовки тренда конверсии
(по когорте регистрации против по календарному месяцу оплаты).
"""
import csv
import hashlib
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

# Кириллица в консоли не полагается на кодировку терминала
# (решение 17; симуляция 2026-09-04, дефект M9-1: без этой строки
# скрипт падал с UnicodeEncodeError, допечатав часть вывода).
sys.stdout.reconfigure(encoding="utf-8")

RAW = Path(__file__).resolve().parent / "raw"
OUT_DIR = Path(__file__).resolve().parent


def month_key(d: date) -> str:
    return f"{d.year}-{d.month:02d}"


def main() -> None:
    signups = list(csv.DictReader((RAW / "signups.csv").open(encoding="utf-8")))
    payments = list(csv.DictReader((RAW / "payments.csv").open(encoding="utf-8")))

    print("=== Контрольная точка ===")
    for name in ("signups.csv", "payments.csv"):
        p = RAW / name
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        n = len(p.read_text(encoding="utf-8").splitlines()) - 1
        print(f"{name}: {n} строк, sha256 {digest}")

    # --- дубли платежей (ретраи): тот же user_id и amount в пределах 5 минут ---
    by_user = defaultdict(list)
    for p in payments:
        by_user[p["user_id"]].append(p)
    dup_count = 0
    for uid, plist in by_user.items():
        plist.sort(key=lambda r: r["payment_ts"])
        for i in range(1, len(plist)):
            t0 = datetime.strptime(plist[i - 1]["payment_ts"], "%Y-%m-%d %H:%M:%S")
            t1 = datetime.strptime(plist[i]["payment_ts"], "%Y-%m-%d %H:%M:%S")
            if plist[i]["amount"] == plist[i - 1]["amount"] and (t1 - t0) <= timedelta(minutes=5):
                dup_count += 1
    print(f"\n=== Критерий 5: дубли платежей (ретраи, <=5 мин, та же сумма) ===")
    print(f"строк-дублей: {dup_count} из {len(payments)} платежей")

    # --- задвоенные аккаунты: email встречается >1 раза ---
    email_to_uids = defaultdict(list)
    for s in signups:
        email_to_uids[s["email"]].append(s["user_id"])
    dup_emails = {e: uids for e, uids in email_to_uids.items() if len(uids) > 1}
    print(f"\n=== Критерий 6: задвоенные аккаунты ===")
    print(f"email с >1 аккаунтом: {len(dup_emails)} из {len(email_to_uids)} уникальных email")

    paying_users = {p["user_id"] for p in payments}
    # влияние: сколько email из дублей имеют оплату хотя бы на одном из двух аккаунтов,
    # но не были бы учтены во втором, если считать по user_id
    affected_conversions = sum(
        1 for uids in dup_emails.values() if any(u in paying_users for u in uids)
    )
    print(f"из них хотя бы один аккаунт из пары платит: {affected_conversions}")

    # --- конверсия по каналу и месяцу (когорта регистрации, окно 60 дней от конца датасета) ---
    obs_end = datetime(2026, 2, 28)  # достаточно данных вперёд, чтобы окно 45 дней закрылось у всех
    pay_by_user_first = {}
    for p in payments:
        uid = p["user_id"]
        ts = datetime.strptime(p["payment_ts"], "%Y-%m-%d %H:%M:%S")
        if uid not in pay_by_user_first or ts < pay_by_user_first[uid]:
            pay_by_user_first[uid] = ts

    reg_by_month_channel = defaultdict(list)
    for s in signups:
        d = date.fromisoformat(s["signup_date"])
        reg_by_month_channel[(month_key(d), s["channel"])].append(s["user_id"])

    print("\n=== Помесячная конверсия по каналу (когорта регистрации) ===")
    print(f"{'месяц':>7} {'organic':>10} {'referral':>10} {'paid_social':>12} {'смешанная':>11}")
    overall_by_month = {}
    for m in sorted({k[0] for k in reg_by_month_channel}):
        row = []
        total_reg = total_conv = 0
        for ch in ("organic", "referral", "paid_social"):
            uids = reg_by_month_channel.get((m, ch), [])
            conv = sum(1 for u in uids if u in pay_by_user_first)
            rate = conv / len(uids) if uids else 0
            row.append(rate)
            total_reg += len(uids)
            total_conv += conv
        blended = total_conv / total_reg if total_reg else 0
        overall_by_month[m] = blended
        print(f"{m:>7} {row[0]*100:9.1f}% {row[1]*100:9.1f}% {row[2]*100:11.1f}% {blended*100:10.1f}%")

    months_sorted = sorted(overall_by_month)
    print(f"\nПервый месяц смешанная: {overall_by_month[months_sorted[0]]*100:.1f}%, "
          f"последний: {overall_by_month[months_sorted[-1]]*100:.1f}%")

    # --- две трактовки тренда: по когорте регистрации vs по календарному месяцу оплаты ---
    print("\n=== Критерий 1-2: конверсия по когорте регистрации vs по календарю оплаты ===")
    reg_by_month = defaultdict(list)
    for s in signups:
        reg_by_month[month_key(date.fromisoformat(s["signup_date"]))].append(s["user_id"])

    print("По когорте регистрации (доля этой когорты, когда-либо оплатившая):")
    for m in months_sorted:
        uids = reg_by_month[m]
        conv = sum(1 for u in uids if u in pay_by_user_first)
        print(f"  {m}: {conv}/{len(uids)} = {conv/len(uids)*100:.1f}%")

    pay_month_count = defaultdict(int)
    for uid, ts in pay_by_user_first.items():
        pay_month_count[month_key(ts.date())] += 1
    print("По календарному месяцу первой оплаты, делённому на регистрации ТОГО ЖЕ месяца:")
    for m in months_sorted:
        reg_n = len(reg_by_month[m])
        pay_n = pay_month_count.get(m, 0)
        print(f"  {m}: {pay_n}/{reg_n} = {pay_n/reg_n*100:.1f}%")

    # --- критерий 9: ретеншн по когортам выдачи первого платежа ---
    print("\n=== Критерий 9: retention по 12 когортам (месяц первого платежа) ===")
    all_ts_by_user = defaultdict(list)
    for p in payments:
        all_ts_by_user[p["user_id"]].append(datetime.strptime(p["payment_ts"], "%Y-%m-%d %H:%M:%S"))
    for uid in all_ts_by_user:
        all_ts_by_user[uid].sort()

    cohort_users = defaultdict(list)  # first-payment month -> [user_id]
    for uid, ts in pay_by_user_first.items():
        cohort_users[month_key(ts.date())].append(uid)

    HORIZON = 6  # месяцев вперёд от первого платежа, столько поместится у всех когорт до DATA_CUTOFF
    ref_rows = []
    print(f"{'когорта':>9}" + "".join(f"{'M'+str(i):>7}" for i in range(HORIZON)))
    for m in months_sorted:
        uids = cohort_users.get(m, [])
        if not uids:
            continue
        row = []
        for i in range(HORIZON):
            active = 0
            for uid in uids:
                first = pay_by_user_first[uid]
                lo = first + timedelta(days=30 * i - 10)
                hi = first + timedelta(days=30 * i + 10)
                if any(lo <= t <= hi for t in all_ts_by_user[uid]):
                    active += 1
            rate = active / len(uids)
            row.append(rate)
        ref_rows.append((m, len(uids), row))
        print(f"{m:>9}" + "".join(f"{r*100:6.1f}%" for r in row))

    ref_path = OUT_DIR / "ref_retention.csv"
    with ref_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cohort_month", "cohort_size"] + [f"m{i}" for i in range(HORIZON)])
        for m, size, row in ref_rows:
            w.writerow([m, size] + [f"{r:.4f}" for r in row])
    print(f"\n{ref_path.name} записан — {len(ref_rows)} когорт")


if __name__ == "__main__":
    main()
