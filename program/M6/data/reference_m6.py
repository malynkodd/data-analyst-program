"""Эталонные числа модуля M6 (Данные, которые ломаются).

Запуск (после `generate_m6.py`):

    python reference_m6.py

Правило двойного авторства (скилл, раздел 1.3): реализация здесь не
переиспользует внутренние списки генератора — оба файла читаются с диска
теми же средствами, что доступны учащемуся, и сверка строится заново.

Канон модуля (правила ниже упоминаются в шагах по номеру):

1. Ожидаемая связь — один `ledger_txn_id` на одну операцию со статусом
   `completed`, кроме операций-ретраев (см. правило 4).
2. Расчёт приходит не раньше дня операции и не позже +2 дней; операции
   последних 3 дней периода (окно отставания) могут не дойти до расчёта
   вовсе — это не потеря, а расчёт, который ещё не наступил.
3. Расчёт, ссылающийся на `ledger_txn_id`, которого в леджере нет вообще,
   — расчёт без основания.
4. Дубль-ретрай — вторая операция с тем же счётом, той же суммой и
   отметкой времени в пределах 60 секунд от другой такой же операции;
   расчёт приходит только на первую, вторая не должна считаться потерей.
5. `failed` не должен иметь расчёта вовсе; `reversed` должен иметь ровно
   два расчёта — исходное списание и компенсацию отрицательной суммой в
   пределах 5 дней от исходного — иначе нарушение.
6. Статистический выброс — сумма операции более чем в 5 раз выше медианы
   по этому же счёту (IQR-независимый порог, устойчивый к самим
   выбросам: медиана не сдвигается единичными большими значениями так,
   как сдвинулось бы среднее).
"""

from __future__ import annotations

import csv
import statistics
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"

LAG_DAYS = 3
PERIOD_END = date(2026, 3, 31)
LAG_CUTOFF = PERIOD_END - timedelta(days=LAG_DAYS)
DUP_WINDOW_SECONDS = 60
COMPENSATION_WINDOW_DAYS = 5
OUTLIER_MULTIPLE = 5


def read_ledger() -> list[dict]:
    rows = []
    with (RAW / "ledger.csv").open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            rows.append({
                "txn_id": r["txn_id"],
                "account_id": r["account_id"],
                "amount": Decimal(r["amount"]),
                "currency": r["currency"],
                "ts": datetime.strptime(r["ts"], "%Y-%m-%dT%H:%M:%S"),
                "status": r["status"],
            })
    return rows


def read_settlement() -> list[dict]:
    rows = []
    with (RAW / "settlement.csv").open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            rows.append({
                "settlement_id": r["settlement_id"],
                "ledger_txn_id": r["ledger_txn_id"],
                "amount": Decimal(r["amount_cents"]) / 100,
                "fee": Decimal(r["fee_cents"]) / 100,
                "settled_date": datetime.fromtimestamp(int(r["settled_ts"])).date(),
            })
    return rows


def find_duplicates(completed: list[dict]) -> dict[str, str]:
    """Правило 4. Возвращает {id_второй_операции: id_первой}."""
    by_account: dict[str, list[dict]] = {}
    for t in completed:
        by_account.setdefault(t["account_id"], []).append(t)
    dup_map: dict[str, str] = {}
    for txns in by_account.values():
        txns = sorted(txns, key=lambda t: t["ts"])
        for i, t in enumerate(txns):
            if t["txn_id"] in dup_map:
                continue
            for other in txns[i + 1:]:
                if other["txn_id"] in dup_map:
                    continue
                gap = (other["ts"] - t["ts"]).total_seconds()
                if gap > DUP_WINDOW_SECONDS:
                    break
                if other["amount"] == t["amount"]:
                    dup_map[other["txn_id"]] = t["txn_id"]
                    break
    return dup_map


def main() -> int:
    ledger = read_ledger()
    settlement = read_settlement()

    by_id = {t["txn_id"]: t for t in ledger}
    settled_by_ledger_id: dict[str, list[dict]] = {}
    for s in settlement:
        settled_by_ledger_id.setdefault(s["ledger_txn_id"], []).append(s)

    completed = [t for t in ledger if t["status"] == "completed"]
    failed = [t for t in ledger if t["status"] == "failed"]
    reversed_txns = [t for t in ledger if t["status"] == "reversed"]

    dup_map = find_duplicates(completed)

    # --- отчёт сверки: почему completed-операция не рассчитана --------
    unmatched_rows: list[list] = []
    lag_n = dup_n = unexplained_n = 0
    for t in completed:
        rows = settled_by_ledger_id.get(t["txn_id"], [])
        positive = [s for s in rows if s["amount"] > 0]
        if positive:
            continue
        if t["ts"].date() > LAG_CUTOFF:
            lag_n += 1
            reason = "в пределах окна отставания (последние 3 дня периода)"
        elif t["txn_id"] in dup_map:
            dup_n += 1
            reason = f"дубль ретрая операции {dup_map[t['txn_id']]}"
        else:
            unexplained_n += 1
            reason = "необъяснено"
        unmatched_rows.append([t["txn_id"], t["account_id"], f"{t['amount']:.2f}",
                               t["ts"].isoformat(), reason])

    # --- висячие расчёты: ledger_txn_id не существует в леджере --------
    orphans = [s for s in settlement if s["ledger_txn_id"] not in by_id]

    # --- расчёты на статусах, где им не место --------------------------
    failed_settled = [s for s in settlement
                      if s["ledger_txn_id"] in by_id
                      and by_id[s["ledger_txn_id"]]["status"] == "failed"]

    reversed_violations: list[str] = []
    for t in reversed_txns:
        rows = settled_by_ledger_id.get(t["txn_id"], [])
        positive = [s for s in rows if s["amount"] > 0]
        negative = [s for s in rows if s["amount"] < 0]
        if not positive:
            continue  # исходное списание само не пришло — отдельный класс, здесь не встречается
        if not negative:
            reversed_violations.append(t["txn_id"])
            continue
        gap_days = (negative[0]["settled_date"] - positive[0]["settled_date"]).days
        if gap_days > COMPENSATION_WINDOW_DAYS:
            reversed_violations.append(t["txn_id"])

    # --- статистические выбросы (правило 6) -----------------------------
    by_account_completed: dict[str, list[Decimal]] = {}
    for t in completed:
        by_account_completed.setdefault(t["account_id"], []).append(t["amount"])

    outliers: list[list] = []
    for t in completed:
        amounts = by_account_completed[t["account_id"]]
        med = statistics.median(amounts)
        if t["amount"] > med * OUTLIER_MULTIPLE:
            outliers.append([t["txn_id"], t["account_id"], f"{t['amount']:.2f}", f"{med:.2f}",
                             f"{(t['amount'] / med):.1f}x"])

    # --- запись эталонов --------------------------------------------------
    def write_csv(name: str, header: list[str], rows: list[list]) -> None:
        with (HERE / name).open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\r\n")
            w.writerow(header)
            w.writerows(rows)

    write_csv("ref_match_report.csv",
              ["показатель", "значение"],
              [["completed-операций", len(completed)],
               ["есть расчёт", len(completed) - len(unmatched_rows)],
               ["расчёта нет", len(unmatched_rows)],
               ["расчётов без основания", len(orphans)]])

    write_csv("ref_unmatched_report.csv",
              ["txn_id", "account_id", "amount", "ts", "причина"],
              sorted(unmatched_rows, key=lambda r: r[3]))

    write_csv("ref_orphan_settlements.csv",
              ["settlement_id", "ledger_txn_id", "amount", "settled_date"],
              [[s["settlement_id"], s["ledger_txn_id"], f"{s['amount']:.2f}", s["settled_date"].isoformat()]
               for s in sorted(orphans, key=lambda s: s["settlement_id"])])

    write_csv("ref_status_violations.csv",
              ["txn_id", "тип нарушения"],
              sorted(
                  [[s["ledger_txn_id"], "failed, но расчёт пришёл"] for s in failed_settled] +
                  [[tid, "reversed без компенсации в пределах 5 дней"] for tid in reversed_violations],
                  key=lambda r: r[0]))

    write_csv("ref_outliers.csv",
              ["txn_id", "account_id", "amount", "медиана_счёта", "во_сколько_раз"],
              sorted(outliers, key=lambda r: r[0]))

    # --- печать ------------------------------------------------------------
    print(f"леджер: {len(ledger)} операций (completed {len(completed)}, "
          f"failed {len(failed)}, reversed {len(reversed_txns)})")
    print(f"расчёт: {len(settlement)} записей")
    print()
    print("Шаг 01/02 — сверка completed-операций (первый проход и объяснённые причины):")
    print(f"  без расчёта всего: {len(unmatched_rows)}")
    print(f"    в пределах окна отставания: {lag_n}")
    print(f"    дубль ретрая: {dup_n}")
    print(f"    необъяснено: {unexplained_n}")
    print(f"  висячих расчётов (ledger_txn_id не существует): {len(orphans)}")
    print()
    print("Шаг 04 — нарушения правил статуса:")
    print(f"  failed, но расчёт пришёл: {len(failed_settled)}")
    print(f"  reversed без компенсации в пределах {COMPENSATION_WINDOW_DAYS} дней: {len(reversed_violations)} из {len(reversed_txns)}")
    print()
    print(f"Статистические выбросы (> {OUTLIER_MULTIPLE}x медианы счёта): {len(outliers)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
