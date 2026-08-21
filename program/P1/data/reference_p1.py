"""Эталонный расчёт P1 — независимый от Excel/Sheets, тот же принцип,
что reference_m4.py/reference_m5.py: код, а не таблица, источник истины
для acceptance criteria.

Печатает: контрольную точку датасета, сумму по точкам против общей
суммы (критерий 7), худшую точку под двумя определениями выручки
(критерий 3), 2-е и 3-е место под двумя способами учёта ремонтных
недель, число найденных смен ID (критерий 4).
"""
import csv
import hashlib
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parent / "raw" / "sales_transactions.csv"
OUT_DIR = Path(__file__).resolve().parent

# Решение (критерий 5): склейка по city+street, единственной зацепке —
# store_id меняется, название/адрес нет.
STITCH = {203: 103, 206: 106, 209: 109}
ID_CHANGES = {103: "02.03.2026 -> 203", 106: "11.04.2026 -> 206", 109: "21.05.2026 -> 209"}
RENOVATED = {104: 42, 111: 42}  # store_id -> дней закрытия
TOTAL_DAYS = 181
WEEKS = TOTAL_DAYS / 7


def canon(sid: str) -> int:
    sid = int(sid)
    return STITCH.get(sid, sid)


def main() -> None:
    raw = DATA.read_bytes()
    rows = list(csv.DictReader(DATA.read_text(encoding="utf-8").splitlines()))

    print("=== Контрольная точка ===")
    print(f"sales_transactions.csv: {len(rows)} строк, sha256 {hashlib.sha256(raw).hexdigest()}")

    net = defaultdict(float)
    gross = defaultdict(float)
    days_active = defaultdict(set)
    for r in rows:
        sid = canon(r["store_id"])
        amt = float(r["amount"])
        net[sid] += amt
        if amt > 0:
            gross[sid] += amt
        days_active[sid].add(r["tx_date"])

    total_file = sum(float(r["amount"]) for r in rows)
    total_by_store = sum(net.values())
    print("\n=== Критерий 7: сумма по точкам = сумма по файлу ===")
    print(f"по файлу: {total_file:.2f}, по точкам: {total_by_store:.2f}, "
          f"расхождение {abs(total_file - total_by_store):.6f}")

    print("\n=== Критерий 4: смены ID ===")
    for sid, note in ID_CHANGES.items():
        print(f"  {sid}: {note}")

    print("\n=== Критерий 3: худшая точка под двумя определениями выручки ===")
    worst_net = min(net.items(), key=lambda x: x[1])
    worst_gross = min(gross.items(), key=lambda x: x[1])
    print(f"с возвратами (net, включая возвраты как есть): "
          f"худшая {worst_net[0]}, {worst_net[1]:.2f}")
    print(f"без возвратов (gross, только положительные суммы): "
          f"худшая {worst_gross[0]}, {worst_gross[1]:.2f}")

    print("\n=== Ремонтные недели: 2-е и 3-е место под двумя способами ===")
    flat = {sid: v / WEEKS for sid, v in net.items()}
    excl = {sid: v / (len(days_active[sid]) / 7) for sid, v in net.items()}
    print("Способ А — считать закрытые недели нулевой выручкой (среднее за 26 недель):")
    for sid, v in sorted(flat.items(), key=lambda x: x[1])[:4]:
        print(f"  {sid}: {v:.2f}/нед")
    print("Способ Б — исключить закрытые недели (среднее только за активные недели):")
    for sid, v in sorted(excl.items(), key=lambda x: x[1])[:4]:
        print(f"  {sid}: {v:.2f}/нед")

    ref_path = OUT_DIR / "ref_by_store.csv"
    with ref_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["store_id", "net_revenue", "gross_revenue",
                     "avg_weekly_flat26", "avg_weekly_excl_closed"])
        for sid in sorted(net):
            w.writerow([sid, f"{net[sid]:.2f}", f"{gross[sid]:.2f}",
                        f"{flat[sid]:.2f}", f"{excl[sid]:.2f}"])
    print(f"\n{ref_path.name} записан — 12 строк, по одной на точку")


if __name__ == "__main__":
    main()
