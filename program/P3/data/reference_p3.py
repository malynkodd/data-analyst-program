"""Эталонный расчёт P3 — независимо от Power BI учащегося.

Читает оба реальных снапшота (Prozorro CPV 15, курсы НБУ), делит
тендеры на «период A» (до 2026-08-17) и «период B» (2026-08-17…21,
последняя неполная неделя — данные выгружены в пятницу, часть тендеров
недели ещё не отыграна) — тот же смысл, что «Подмена исходного файла
на файл следующего периода» в M4, только оба периода реальны и взяты
из одного и того же снапшота, а не досочинены.

Печатает: контрольные точки обоих файлов, разбивку периодов, пять
кандидатных метрик, эффект НДС-нейтрального сравнения через курс НБУ,
долю «застрявших» (stale, тот же курс, что днём раньше) строк курса.
"""
import csv
import hashlib
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Кириллица в консоли не полагается на кодировку терминала
# (решение 17; симуляция 2026-09-04, дефект M9-1: без этой строки
# скрипт падал с UnicodeEncodeError, допечатав часть вывода).
sys.stdout.reconfigure(encoding="utf-8")

RAW = Path(__file__).resolve().parent / "snapshot"
OUT_DIR = Path(__file__).resolve().parent
PERIOD_SPLIT = datetime.fromisoformat("2026-08-17T00:00:00+03:00")


def main() -> None:
    print("=== Контрольные точки ===")
    for name in ("tenders_food.csv", "exchange_rates.csv"):
        p = RAW / name
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        n = sum(1 for _ in p.open(encoding="utf-8", newline=""))
        if name.endswith(".csv"):
            n = sum(1 for _ in csv.reader(p.open(encoding="utf-8", newline=""))) - 1
        print(f"{name}: {n} строк, sha256 {digest}")

    tenders = list(csv.DictReader((RAW / "tenders_food.csv").open(encoding="utf-8")))
    for t in tenders:
        t["_created"] = datetime.fromisoformat(t["date_created"])

    period_a = [t for t in tenders if t["_created"] < PERIOD_SPLIT]
    period_b = [t for t in tenders if t["_created"] >= PERIOD_SPLIT]
    print(f"\nПериод A (до 2026-08-17): {len(period_a)} тендеров")
    print(f"Период B (2026-08-17..21, неполная неделя): {len(period_b)} тендеров")

    def write_period(rows, name):
        path = OUT_DIR / name
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            cols = ["tender_id", "tenderID", "date_created", "date_modified", "status",
                    "main_category", "cpv_id", "cpv_description", "value_amount",
                    "value_currency", "procuring_entity_name", "procuring_entity_edrpou",
                    "region"]
            w.writerow(cols)
            for r in rows:
                w.writerow([r[c] for c in cols])
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        print(f"{name}: {len(rows)} строк, sha256 {digest}")

    write_period(period_a, "ref_tenders_period_a.csv")
    write_period(period_b, "ref_tenders_period_b.csv")

    print("\n=== Пять кандидатных метрик (на период A — 'опубликованный' срез) ===")
    total_value = sum(float(t["value_amount"]) for t in period_a)
    print(f"1. Сумма закупівель, грн: {total_value:.2f}")
    statuses = defaultdict(int)
    for t in period_a:
        statuses[t["status"]] += 1
    print(f"2. Розподіл за статусом: {dict(statuses)}")
    by_entity = defaultdict(float)
    for t in period_a:
        by_entity[t["procuring_entity_name"]] += float(t["value_amount"])
    top5 = sorted(by_entity.items(), key=lambda x: -x[1])[:5]
    print("3. Топ-5 замовників за сумою:")
    for name, v in top5:
        print(f"   {v:.2f}  {name[:70]}")
    by_cpv = defaultdict(lambda: [0, 0.0])
    for t in period_a:
        by_cpv[t["cpv_id"][:6]][0] += 1
        by_cpv[t["cpv_id"][:6]][1] += float(t["value_amount"])
    print("4. Розподіл за підкатегорією CPV (перші 6 знаків коду), топ-5 за сумою:")
    for cpv, (n, v) in sorted(by_cpv.items(), key=lambda x: -x[1][1])[:5]:
        print(f"   {cpv}: {n} тендерів, {v:.2f} грн")
    completed = [t for t in period_a if t["status"] == "complete"]
    print(f"5. Завершених тендерів: {len(completed)} з {len(period_a)} "
          f"({len(completed)/len(period_a)*100:.1f}%)")

    print("\n=== Курс НБУ: доля 'застряглих' (той самий курс, що днем раніше) ===")
    usd = [r for r in csv.DictReader((RAW / "exchange_rates.csv").open(encoding="utf-8"))
           if r["cc"] == "USD"]
    usd.sort(key=lambda r: datetime.strptime(r["exchangedate"], "%d.%m.%Y"))
    stale = sum(1 for i in range(1, len(usd)) if usd[i]["rate"] == usd[i - 1]["rate"])
    print(f"USD: {len(usd)} строк, {stale} застряглих ({stale/len(usd)*100:.1f}%)")

    print("\n=== Дефляція суми тендерів курсом USD/UAH (реальна купівельна спроможність) ===")
    usd_by_date = {r["exchangedate"]: float(r["rate"]) for r in usd}
    for label, period in (("A", period_a), ("B", period_b)):
        usd_total = 0.0
        for t in period:
            d = t["_created"].strftime("%d.%m.%Y")
            rate = usd_by_date.get(d)
            if rate:
                usd_total += float(t["value_amount"]) / rate
        nominal = sum(float(t["value_amount"]) for t in period)
        print(f"Період {label}: {nominal:.2f} грн номінально, "
              f"{usd_total:.2f} USD-еквівалент на дату кожного тендера")


if __name__ == "__main__":
    main()
