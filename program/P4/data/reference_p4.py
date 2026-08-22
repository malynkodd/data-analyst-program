"""Эталонный расчёт P4 — независимо от fetch_prozorro.py/fetch_edr.py/fetch_nbu.py.

Двусторонняя сверка (тот же приём, что M6, `program/M6/data/reference_m6.py`):
первый проход точный по ключу без причин, второй проход объясняет
каждую потерю ровно одной причиной из исчерпывающего списка, порядок
причин фиксирован (первая подходящая причина — как в M6/M5).

Объект сверки — контрагенты (поставщики и заказчики) контрактов
CPV 15 против реестра ЄДР юридичних осіб (`UO.zip`, решение 35/36).
Тендеры и контракты — независимые выборки живой ленты
(`fetch_prozorro.py`, докстрока), не связаны построчно 1:1 в этом
снапшоте — сравниваются агрегатами, не join'ом.
"""
from __future__ import annotations

import csv
import hashlib
import statistics
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
SNAP = HERE / "snapshot"


def read_csv(name):
    with (SNAP / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> int:
    contracts = read_csv("contracts_food.csv")
    tenders = read_csv("tenders_food.csv")
    edr_rows = read_csv("edr_lookup.csv")
    edr_by_code = {r["edrpou"]: r for r in edr_rows}
    not_found = set((SNAP / "edrpous_not_found.txt").read_text(encoding="utf-8").splitlines())
    not_found = {e for e in not_found if e}
    usd = read_csv("usd_uah.csv")

    # --- Сторона 1: контрагенты контрактов (постачальник + замовник) ---
    parties = []  # (role, edrpou, name, contract_id)
    for c in contracts:
        if c["supplier_edrpou"]:
            parties.append(("supplier", c["supplier_edrpou"], c["supplier_name"], c["contract_id"]))
        if c["buyer_edrpou"]:
            parties.append(("buyer", c["buyer_edrpou"], c["buyer_name"], c["contract_id"]))

    unique_codes = sorted({p[1] for p in parties})
    total_in = len(unique_codes)

    # --- Первый проход: точный по ключу, без причин ---
    matched = [c for c in unique_codes if c in edr_by_code]
    unmatched = [c for c in unique_codes if c not in edr_by_code]
    assert len(matched) + len(unmatched) == total_in, "вход = сопоставлено + потеряно"

    # --- Второй проход: причина на каждую потерю, порядок фиксирован ---
    name_by_code: dict[str, str] = {}
    for _role, code, name, _cid in parties:
        name_by_code.setdefault(code, name)

    reasons = Counter()
    reason_by_code: dict[str, str] = {}
    for code in unmatched:
        name = name_by_code.get(code, "")
        if not code:
            reasons["пустой идентификатор"] += 1
            reason_by_code[code] = "пустой идентификатор"
        elif not code.isdigit():
            reasons["не числовой код при scheme=UA-EDR (ошибка ввода в Prozorro)"] += 1
            reason_by_code[code] = "не числовой код при scheme=UA-EDR (ошибка ввода в Prozorro)"
        elif len(code) == 10:
            reasons["10-значный код — РНОКПП ФОП, не ЄДРПОУ юрлиц"] += 1
            reason_by_code[code] = "10-значный код — РНОКПП ФОП, не ЄДРПОУ юрлиц"
        elif len(code) != 8:
            reasons["код не 8 и не 10 цифр — нестандартная длина"] += 1
            reason_by_code[code] = "код не 8 и не 10 цифр — нестандартная длина"
        elif "філія" in name.lower():
            reasons["филиал (структурное подразделение) — свой ЄДРПОУ, но не отдельная запись SUBJECT в реестре"] += 1
            reason_by_code[code] = "филиал (структурное подразделение) — свой ЄДРПОУ, но не отдельная запись SUBJECT в реестре"
        else:
            reasons["8-значный ЄДРПОУ, но не найден в UO.xml (причина не установлена)"] += 1
            reason_by_code[code] = "8-значный ЄДРПОУ, но не найден в UO.xml (причина не установлена)"

    explained = sum(reasons.values())
    assert explained == len(unmatched), "необъяснённых 0"

    # --- Найденные: статус (діючий / припинено / ...) ---
    stan_counts = Counter(edr_by_code[c]["stan"] for c in matched)

    # --- Агрегаты: тендеры (ожидаемая сумма) vs контракты (факт) ---
    tender_total = sum(float(t["value_amount"]) for t in tenders if t["value_amount"] and t["value_currency"] == "UAH")
    contract_total = sum(float(c["amount"]) for c in contracts if c["amount"] and c["currency"] == "UAH")
    contract_non_uah = [c for c in contracts if c["currency"] and c["currency"] != "UAH"]

    # --- Курс USD/UAH: среднее за период выгрузки контрактов, для контекста ---
    rates = [float(r["rate"]) for r in usd]
    avg_rate = round(statistics.mean(rates), 4)
    first_rate = float(usd[-1]["rate"])  # файл по убыванию даты
    last_rate = float(usd[0]["rate"])

    # --- Топ-10 поставщиков по сумме контрактов ---
    supplier_sum: dict[str, float] = {}
    supplier_name: dict[str, str] = {}
    for c in contracts:
        if c["currency"] != "UAH" or not c["amount"] or not c["supplier_edrpou"]:
            continue
        code = c["supplier_edrpou"]
        supplier_sum[code] = supplier_sum.get(code, 0.0) + float(c["amount"])
        supplier_name[code] = c["supplier_name"]
    top10 = sorted(supplier_sum.items(), key=lambda kv: kv[1], reverse=True)[:10]

    # --- Критерии 7-8: решение по несопоставленному остатку, обе версии ---
    total_all_suppliers = sum(supplier_sum.values())
    total_verified_only = sum(v for code, v in supplier_sum.items() if code in edr_by_code)
    unverified_value = total_all_suppliers - total_verified_only
    scale = total_all_suppliers / total_verified_only if total_verified_only else 0.0
    top10_excluded = sorted(
        ((code, v) for code, v in supplier_sum.items() if code in edr_by_code),
        key=lambda kv: kv[1], reverse=True)[:10]
    top10_distributed = sorted(
        ((code, v * scale) for code, v in supplier_sum.items() if code in edr_by_code),
        key=lambda kv: kv[1], reverse=True)[:10]

    print("=== Сверка контрагентов контрактов против ЄДР (UO.xml) ===")
    print(f"уникальных ЄДРПОУ/кодов у контрагентов: {total_in}")
    print(f"найдено в реестре: {len(matched)}")
    print(f"не найдено: {len(unmatched)}")
    for reason, n in reasons.most_common():
        print(f"  {reason}: {n}")
    print(f"необъяснённых: {len(unmatched) - explained} (должно быть 0)")
    print()
    print("Статус найденных контрагентов:")
    for stan, n in stan_counts.most_common():
        print(f"  {stan}: {n}")

    print()
    print("=== Тендеры (ожидание) vs контракты (факт) ===")
    print(f"тендеров CPV15 в снапшоте: {len(tenders)}, сумма UAH: {tender_total:,.2f}")
    print(f"контрактов CPV15 в снапшоте: {len(contracts)}, сумма UAH: {contract_total:,.2f}")
    print(f"контрактов в валюте, отличной от UAH: {len(contract_non_uah)}")
    print("Тендеры и контракты — независимые выборки живой ленты, не 1:1 —"
          " сравнение агрегатное, не построчный join (см. docstring fetch_prozorro.py)")

    print()
    print(f"=== Курс USD/UAH за период снапшота: среднее {avg_rate}, "
          f"начало {first_rate}, конец {last_rate} ===")
    print(f"Сумма контрактов в USD по среднему курсу: {contract_total/avg_rate:,.2f}")

    print()
    print("=== Топ-10 поставщиков по сумме контрактов (только найденные в ЄДР помечены) ===")
    for code, total in top10:
        in_edr = "в ЄДР" if code in edr_by_code else "НЕ в ЄДР"
        print(f"  {supplier_name.get(code, code)} ({code}, {in_edr}): {total:,.2f}")

    print()
    print("=== Критерии 7-8: решение по несопоставленному остатку ===")
    print(f"итог по всем поставщикам (включая не в ЄДР): {total_all_suppliers:,.2f}")
    print(f"итог только по подтверждённым в ЄДР: {total_verified_only:,.2f}")
    print(f"остаток (не подтверждён в ЄДР): {unverified_value:,.2f} "
          f"({unverified_value/total_all_suppliers:.1%} от общей суммы)")
    print(f"коэффициент распределения остатка на подтверждённых: {scale:.4f}")
    print("Топ-10, версия 'исключить' (остаток выброшен, итог занижен):")
    for code, total in top10_excluded:
        print(f"  {supplier_name.get(code, code)} ({code}): {total:,.2f}")
    print("Топ-10, версия 'распределить' (остаток размазан пропорционально долям):")
    for code, total in top10_distributed:
        print(f"  {supplier_name.get(code, code)} ({code}): {total:,.2f}")

    # --- Запись файлов ---
    with (HERE / "ref_match_report.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["показатель", "значение"])
        w.writerow(["уникальных_кодов_контрагентов", total_in])
        w.writerow(["найдено_в_ЄДР", len(matched)])
        w.writerow(["не_найдено", len(unmatched)])

    with (HERE / "ref_unmatched_report.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["edrpou", "причина"])
        for code in unmatched:
            w.writerow([code, reason_by_code[code]])

    with (HERE / "ref_top10_suppliers.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["supplier_edrpou", "supplier_name", "total_uah", "в_ЄДР"])
        for code, total in top10:
            w.writerow([code, supplier_name.get(code, ""), round(total, 2), code in edr_by_code])

    with (HERE / "ref_totals_comparison.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["версия", "итог_uah"])
        w.writerow(["все_поставщики_без_фильтра", round(total_all_suppliers, 2)])
        w.writerow(["исключить_неподтверждённых", round(total_verified_only, 2)])
        w.writerow(["распределить_остаток_пропорционально", round(total_all_suppliers, 2)])

    for name in ("ref_match_report.csv", "ref_unmatched_report.csv", "ref_top10_suppliers.csv",
                 "ref_totals_comparison.csv"):
        digest = hashlib.sha256((HERE / name).read_bytes()).hexdigest()
        print(f"{name}: sha256 {digest}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
