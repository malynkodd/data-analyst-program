"""Снапшот P4 — тендеры и контракты категории CPV 15 (Продукти
харчування, напої, тютюн) с Prozorro API. Тот же приём, что P3
(`program/P3/data/fetch_prozorro.py`): живая лента отдаёт дёшево только
`id`/`dateModified`, `value`/`classification`/`suppliers` — только
полной карточкой.

Два потока — не дубли: `tenders` — что заказчик ПЛАНИРОВАЛ купить
(ожидаемая сумма, объявленная в тендере); `contracts` — что РЕАЛЬНО
подписано (сумма контракта, конкретный поставщик по ЄДРПОУ). Суммы
тендеров и контрактов не обязаны совпадать — это и есть часть проектной
неоднозначности (P4, часть 5 blueprint: «данные, которые не сходятся»).

`dateModified` в ленте — не `dateSigned` контракта (правка контракта
двигает `dateModified`, не дату подписания) — фильтрация по CPV идёт по
живой ленте (самые недавние правки), реальный охват по датам подписания
получается пост-фактум, из уже собранных карточек, не гарантируется
заранее.
"""
import csv
import hashlib
import json
import time
import urllib.request
from pathlib import Path

HEADERS = {"User-Agent": "data-analyst-program research (P4 snapshot)"}
OUT_DIR = Path(__file__).resolve().parent / "snapshot"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CPV_PREFIX = "15"
TENDERS_BASE = "https://public.api.openprocurement.org/api/2.5/tenders"
CONTRACTS_BASE = "https://public.api.openprocurement.org/api/2.5/contracts"


def fetch(url: str, retries: int = 3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:  # noqa: BLE001
            if attempt == retries - 1:
                raise
            time.sleep(2)


def fetch_tenders(target: int, max_scan: int):
    scanned, kept = 0, []
    url = f"{TENDERS_BASE}?opt_fields=dateCreated,status&descending=1&limit=100"
    while scanned < max_scan and len(kept) < target:
        page = fetch(url)
        ids = [row["id"] for row in page["data"]]
        for tid in ids:
            if scanned >= max_scan or len(kept) >= target:
                break
            try:
                detail = fetch(f"{TENDERS_BASE}/{tid}")["data"]
            except Exception as exc:  # noqa: BLE001
                print(f"skip tender {tid}: {exc}")
                scanned += 1
                continue
            scanned += 1
            items = detail.get("items", [])
            cpv = items[0]["classification"]["id"] if items and items[0].get("classification") else ""
            if cpv.startswith(CPV_PREFIX):
                kept.append(detail)
            if scanned % 200 == 0:
                print(f"тендеры: просканировано {scanned}, найдено {len(kept)}")
        if not page.get("next_page"):
            break
        url = page["next_page"]["uri"]
    print(f"Тендеры: просканировано {scanned}, найдено {len(kept)} CPV {CPV_PREFIX}")
    return kept


def fetch_contracts(target: int, max_scan: int):
    scanned, kept = 0, []
    url = f"{CONTRACTS_BASE}?descending=1&limit=100"
    while scanned < max_scan and len(kept) < target:
        page = fetch(url)
        ids = [row["id"] for row in page["data"]]
        for cid in ids:
            if scanned >= max_scan or len(kept) >= target:
                break
            try:
                detail = fetch(f"{CONTRACTS_BASE}/{cid}")["data"]
            except Exception as exc:  # noqa: BLE001
                print(f"skip contract {cid}: {exc}")
                scanned += 1
                continue
            scanned += 1
            items = detail.get("items", [])
            cpv = items[0]["classification"]["id"] if items and items[0].get("classification") else ""
            if cpv.startswith(CPV_PREFIX):
                kept.append(detail)
            if scanned % 200 == 0:
                print(f"контракты: просканировано {scanned}, найдено {len(kept)}")
        if not page.get("next_page"):
            break
        url = page["next_page"]["uri"]
    print(f"Контракты: просканировано {scanned}, найдено {len(kept)} CPV {CPV_PREFIX}")
    return kept


def write_tenders(kept):
    path = OUT_DIR / "tenders_food.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "tender_id", "tenderID", "date_created", "status",
            "cpv_id", "value_amount", "value_currency",
            "procuring_entity_name", "procuring_entity_edrpou", "region",
        ])
        for d in kept:
            items = d.get("items", [])
            cpv = items[0].get("classification", {}) if items else {}
            pe = d.get("procuringEntity", {})
            val = d.get("value", {}) or {}
            w.writerow([
                d.get("id"), d.get("tenderID"), d.get("dateCreated"), d.get("status"),
                cpv.get("id"), val.get("amount"), val.get("currency"),
                pe.get("name"), pe.get("identifier", {}).get("id"),
                pe.get("address", {}).get("region"),
            ])
    return path


def write_contracts(kept):
    path = OUT_DIR / "contracts_food.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "contract_id", "tender_id", "date_signed", "status",
            "cpv_id", "amount", "currency",
            "buyer_name", "buyer_edrpou",
            "supplier_name", "supplier_edrpou",
        ])
        for d in kept:
            items = d.get("items", [])
            cpv = items[0].get("classification", {}) if items else {}
            buyer = d.get("buyer", {}) or {}
            val = d.get("value", {}) or {}
            suppliers = d.get("suppliers") or [{}]
            sup = suppliers[0]
            w.writerow([
                d.get("id"), d.get("tender_id"), d.get("dateSigned"), d.get("status"),
                cpv.get("id"), val.get("amount"), val.get("currency"),
                buyer.get("name"), buyer.get("identifier", {}).get("id"),
                sup.get("name"), sup.get("identifier", {}).get("id"),
            ])
    return path


def main() -> None:
    tenders = fetch_tenders(target=300, max_scan=5000)
    contracts = fetch_contracts(target=500, max_scan=8000)

    t_path = write_tenders(tenders)
    c_path = write_contracts(contracts)

    for path in (t_path, c_path):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        # Строки, не байтовые переносы: часть buyer_name/supplier_name из
        # Prozorro содержит буквальный "\n" внутри значения (найдено
        # прогоном) — наивный подсчёт строк по переносам даёт число
        # больше настоящего (529 вместо 500 на прогоне 2026-08-22).
        n = sum(1 for _ in csv.reader(path.open(encoding="utf-8", newline=""))) - 1
        print(f"{path.name}: {n} строк, sha256 {digest}")

    # Уникальные ЄДРПОУ контрагентов (заказчик+поставщик) — нужны для
    # прицельного одного прохода по UO.xml (3.16 ГБ), не полного разбора.
    edrpous = set()
    for d in contracts:
        for entity in ([d.get("buyer", {})] + (d.get("suppliers") or [])):
            eid = (entity or {}).get("identifier", {}).get("id")
            if eid:
                edrpous.add(eid)
    for d in tenders:
        eid = d.get("procuringEntity", {}).get("identifier", {}).get("id")
        if eid:
            edrpous.add(eid)
    edrpous_path = OUT_DIR / "edrpous_needed.txt"
    edrpous_path.write_text("\n".join(sorted(edrpous)), encoding="utf-8")
    print(f"{edrpous_path.name}: {len(edrpous)} уникальных ЄДРПОУ/идентификаторов для сверки с UO.xml")


if __name__ == "__main__":
    main()
