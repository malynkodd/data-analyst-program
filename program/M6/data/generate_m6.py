"""Генератор датасета M6 (Данные, которые ломаются).

Домен fintech (решение 21, п. 2): сверка внутреннего леджера платёжного
сервиса с выпиской расчётного банка (эквайера) за один и тот же период.
Обе стороны видят одни и те же операции по-разному — это и есть предмет
модуля: не разбитый файл, а две правдоподобные, но расходящиеся версии
одной реальности.

Категория — синтетика учебного модуля с генератором (решение 29
`design/decisions.md`): эталон обязан быть известен точно.

Запуск:

    python program\\M6\\data\\generate_m6.py

Пишет `program/M6/data/raw/` (в `.gitignore`, решение 29) и печатает
контрольную точку: число строк и sha256 каждого файла плюс все внесённые
дефекты по числу. Детерминирован — `SEED` фиксирован до первого
обращения к `random`.
"""

from __future__ import annotations

import csv
import hashlib
import random
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

# Кириллица в консоли не полагается на кодировку терминала
# (решение 17; симуляция 2026-09-04, дефект M9-1: без этой строки
# скрипт падал с UnicodeEncodeError, допечатав часть вывода).
sys.stdout.reconfigure(encoding="utf-8")

SEED = 20260821
random.seed(SEED)

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"

PERIOD_START = date(2026, 1, 1)
PERIOD_END = date(2026, 3, 31)  # 90 дней
N_DAYS = (PERIOD_END - PERIOD_START).days + 1

N_ACCOUNTS = 40
ACCOUNTS = [f"ACC-{i:04d}" for i in range(1, N_ACCOUNTS + 1)]

# у каждого счёта — свой типичный размер операции (для статистических
# выбросов шага 03: выброс определяется относительно СВОЕГО счёта, а не
# общего распределения)
ACCOUNT_TYPICAL = {a: Decimal(random.choice([500, 800, 1200, 2000, 3500])) for a in ACCOUNTS}

FEE_RATE = Decimal("0.018")  # 1.8% комиссия эквайера, вычитается при расчёте
LAG_DAYS = 3  # расчёт приходит не раньше чем через 0-2 дня; последние LAG_DAYS дней периода расчёт мог не дойти
TWO = Decimal("0.01")


def money(v: Decimal) -> Decimal:
    return v.quantize(TWO, rounding=ROUND_HALF_UP)


def rand_amount(account: str) -> Decimal:
    base = ACCOUNT_TYPICAL[account]
    factor = Decimal(str(round(random.uniform(0.4, 1.8), 2)))
    return money(base * factor)


def rand_ts(day: date) -> datetime:
    return datetime(day.year, day.month, day.day,
                     random.randint(0, 23), random.randint(0, 59), random.randint(0, 59))


def daterange():
    d = PERIOD_START
    while d <= PERIOD_END:
        yield d
        d += timedelta(days=1)


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)

    ledger: list[dict] = []
    txn_seq = 1

    # --- обычные операции --------------------------------------------
    for day in daterange():
        n_today = random.randint(20, 32)
        for _ in range(n_today):
            account = random.choice(ACCOUNTS)
            status = random.choices(
                ["completed", "failed", "reversed"], weights=[88, 8, 4], k=1
            )[0]
            ledger.append({
                "txn_id": f"T{txn_seq:06d}",
                "account_id": account,
                "amount": rand_amount(account),
                "currency": "UAH",
                "ts": rand_ts(day),
                "status": status,
            })
            txn_seq += 1

    # --- дефект F: статистические выбросы (10 полных операций) --------
    outlier_ids: list[str] = []
    completed = [t for t in ledger if t["status"] == "completed"]
    for t in random.sample(completed, 10):
        t["amount"] = money(ACCOUNT_TYPICAL[t["account_id"]] * Decimal(str(round(random.uniform(8, 15), 1))))
        outlier_ids.append(t["txn_id"])

    # --- дефект B: дублирующиеся ретраи (25 пар) -----------------------
    dup_pairs: list[tuple[str, str]] = []
    candidates = [t for t in ledger if t["status"] == "completed" and t["txn_id"] not in outlier_ids]
    for original in random.sample(candidates, 25):
        retry = {
            "txn_id": f"T{txn_seq:06d}",
            "account_id": original["account_id"],
            "amount": original["amount"],
            "currency": "UAH",
            "ts": original["ts"] + timedelta(seconds=random.randint(2, 40)),
            "status": "completed",
        }
        txn_seq += 1
        ledger.append(retry)
        dup_pairs.append((original["txn_id"], retry["txn_id"]))

    ledger.sort(key=lambda t: t["ts"])

    # --- расчёт (settlement) -------------------------------------------
    settlement: list[dict] = []
    settle_seq = 1
    lag_cutoff = PERIOD_END - timedelta(days=LAG_DAYS)

    # дубли ретраев: расчёт приходит только на первую операцию пары
    dup_retry_ids = {retry for _, retry in dup_pairs}

    lag_excluded: list[str] = []
    for t in ledger:
        if t["status"] != "completed":
            continue
        if t["txn_id"] in dup_retry_ids:
            continue  # вторая операция пары ретраев не рассчитывается вовсе
        settle_day = t["ts"].date() + timedelta(days=random.randint(0, 2))
        if settle_day > PERIOD_END:
            if t["ts"].date() > lag_cutoff:
                lag_excluded.append(t["txn_id"])
                continue
            settle_day = PERIOD_END
        fee = money(t["amount"] * FEE_RATE)
        settlement.append({
            "settlement_id": f"S{settle_seq:06d}",
            "ledger_txn_id": t["txn_id"],
            "amount": money(t["amount"] - fee),
            "fee": fee,
            "settled_date": settle_day,
        })
        settle_seq += 1

    # --- дефект D: failed, но расчёт всё равно пришёл (8 штук) ---------
    failed = [t for t in ledger if t["status"] == "failed"]
    failed_settled_ids: list[str] = []
    for t in random.sample(failed, 8):
        fee = money(t["amount"] * FEE_RATE)
        settlement.append({
            "settlement_id": f"S{settle_seq:06d}",
            "ledger_txn_id": t["txn_id"],
            "amount": money(t["amount"] - fee),
            "fee": fee,
            "settled_date": t["ts"].date() + timedelta(days=1),
        })
        settle_seq += 1
        failed_settled_ids.append(t["txn_id"])

    # --- дефект E: reversed без компенсирующей отрицательной проводки --
    reversed_txns = [t for t in ledger if t["status"] == "reversed"]
    reversed_uncompensated_ids: list[str] = []
    for t in reversed_txns:
        fee = money(t["amount"] * FEE_RATE)
        # исходное списание расчитывается всегда
        settlement.append({
            "settlement_id": f"S{settle_seq:06d}",
            "ledger_txn_id": t["txn_id"],
            "amount": money(t["amount"] - fee),
            "fee": fee,
            "settled_date": t["ts"].date() + timedelta(days=1),
        })
        settle_seq += 1
        got_compensation = random.random() < 0.75
        if got_compensation:
            settlement.append({
                "settlement_id": f"S{settle_seq:06d}",
                "ledger_txn_id": t["txn_id"],
                "amount": money(-(t["amount"] - fee)),
                "fee": Decimal("0.00"),
                "settled_date": t["ts"].date() + timedelta(days=random.randint(2, 4)),
            })
            settle_seq += 1
        else:
            reversed_uncompensated_ids.append(t["txn_id"])

    # --- дефект C: висячие расчёты без записи в леджере (15 штук) ------
    orphan_ids: list[str] = []
    for _ in range(15):
        account = random.choice(ACCOUNTS)
        day = PERIOD_START + timedelta(days=random.randint(0, N_DAYS - 1))
        amount = rand_amount(account)
        fee = money(amount * FEE_RATE)
        sid = f"S{settle_seq:06d}"
        settlement.append({
            "settlement_id": sid,
            "ledger_txn_id": f"T{txn_seq + 900:06d}",  # заведомо не существующий в леджере id
            "amount": money(amount - fee),
            "fee": fee,
            "settled_date": day,
        })
        orphan_ids.append(sid)
        settle_seq += 1
        txn_seq += 1

    settlement.sort(key=lambda s: (s["settled_date"], s["settlement_id"]))

    # --- запись файлов ---------------------------------------------------
    # settlement.csv: дата — unix-время (секунды), сумма и комиссия — в
    # копейках целым числом. Это реальный формат многих выписок эквайеров
    # и намеренная messiness B1: денежная колонка требует деления на 100,
    # дата требует конвертации из timestamp, а не строкового разбора.
    with (RAW / "ledger.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["txn_id", "account_id", "amount", "currency", "ts", "status"])
        for t in ledger:
            w.writerow([t["txn_id"], t["account_id"], f"{t['amount']:.2f}",
                       t["currency"], t["ts"].strftime("%Y-%m-%dT%H:%M:%S"), t["status"]])

    with (RAW / "settlement.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["settlement_id", "ledger_txn_id", "amount_cents", "fee_cents", "settled_ts"])
        for s in settlement:
            ts = int(datetime(s["settled_date"].year, s["settled_date"].month,
                              s["settled_date"].day, 12, 0, 0).timestamp())
            w.writerow([s["settlement_id"], s["ledger_txn_id"],
                       int(s["amount"] * 100), int(s["fee"] * 100), ts])

    def sha256_of(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    print("Датасет M6 записан в", RAW)
    print("SEED =", SEED)
    print()
    print(f"{'файл':<20}{'строк данных':>14}  sha256")
    for name in ("ledger.csv", "settlement.csv"):
        path = RAW / name
        rows = sum(1 for _ in path.open(encoding="utf-8")) - 1
        print(f"{name:<20}{rows:>14}  {sha256_of(path)}")

    print()
    print("Инварианты (проверяются здесь, а не доверием к описанию):")
    print(f"  операций в леджере: {len(ledger)} (completed {sum(1 for t in ledger if t['status']=='completed')}, "
          f"failed {len(failed)}, reversed {len(reversed_txns)})")
    print(f"  записей расчёта: {len(settlement)}")
    print(f"  дубли ретраев (пар): {len(dup_pairs)}")
    print(f"  расчёт не пришёл из-за окна отставания (последние {LAG_DAYS} дн.): {len(lag_excluded)}")
    print(f"  висячие расчёты без записи в леджере: {len(orphan_ids)}")
    print(f"  failed, но расчёт всё равно пришёл: {len(failed_settled_ids)}")
    print(f"  reversed без компенсирующей проводки: {len(reversed_uncompensated_ids)} из {len(reversed_txns)}")
    print(f"  статистические выбросы по сумме: {len(outlier_ids)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
