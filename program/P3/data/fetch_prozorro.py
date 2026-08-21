"""Снапшот P3 — тендеры категории CPV 15 (Продукти харчування, напої,
тютюн) с Prozorro API.

Живая лента изменений (`GET /api/2.5/tenders`) отдаёт дешёво только
`dateCreated`, `procuringEntity`, `status`, `tenderID` — `value` и
`classification` не попадают в `opt_fields` ни при каком запрошенном
наборе (проверено прогоном 2026-08-21, research/sources-gate.md не
называл это ограничение явно). Чтобы получить сумму и категорию,
каждый тендер приходится читать полной карточкой (`GET /tenders/{id}`,
~300 КБ вместо оценки в 5 КБ из гейта источников — карточка с полной
историей ставок тяжелее одиночного тендера без ставок).

Скрипт идёт по живой ленте (самые недавно изменённые тендеры) и
оставляет только те, у первой позиции которых код CPV начинается на
"15". Останавливается, набрав TARGET подходящих тендеров или пройдя
MAX_SCAN тендеров ленты, что наступит раньше.
"""
import csv
import hashlib
import json
import time
import urllib.request
from pathlib import Path

BASE = "https://public.api.openprocurement.org/api/2.5/tenders"
HEADERS = {"User-Agent": "data-analyst-program research (P3 snapshot)"}
OUT_DIR = Path(__file__).resolve().parent / "snapshot"
OUT_DIR.mkdir(exist_ok=True)

TARGET = 600
MAX_SCAN = 6000
CPV_PREFIX = "15"


def fetch(url: str, retries: int = 3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            if attempt == retries - 1:
                raise
            time.sleep(2)


def main() -> None:
    scanned = 0
    kept = []
    url = f"{BASE}?opt_fields=dateCreated,status&descending=1&limit=100"

    while scanned < MAX_SCAN and len(kept) < TARGET:
        page = fetch(url)
        ids = [row["id"] for row in page["data"]]
        for tid in ids:
            if scanned >= MAX_SCAN or len(kept) >= TARGET:
                break
            try:
                detail = fetch(f"{BASE}/{tid}")["data"]
            except Exception as exc:  # noqa: BLE001
                print(f"skip {tid}: {exc}")
                scanned += 1
                continue
            scanned += 1
            items = detail.get("items", [])
            cpv = items[0]["classification"]["id"] if items and items[0].get("classification") else ""
            if cpv.startswith(CPV_PREFIX):
                kept.append(detail)
            if scanned % 200 == 0:
                print(f"просканировано {scanned}, найдено {len(kept)}")
        if not page.get("next_page"):
            break
        url = page["next_page"]["uri"]

    print(f"Итого: просканировано {scanned}, найдено {len(kept)} тендеров CPV {CPV_PREFIX}")

    # плоская таблица для анализа — одна строка на тендер. Полные карточки
    # (с историей ставок и документами) не сохраняются — то, что нужно для
    # дашборда, целиком укладывается в эти 13 колонок.
    flat_path = OUT_DIR / "tenders_food.csv"
    with flat_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "tender_id", "tenderID", "date_created", "date_modified", "status",
            "main_category", "cpv_id", "cpv_description",
            "value_amount", "value_currency",
            "procuring_entity_name", "procuring_entity_edrpou", "region",
        ])
        for d in kept:
            items = d.get("items", [])
            cpv = items[0].get("classification", {}) if items else {}
            pe = d.get("procuringEntity", {})
            val = d.get("value", {}) or {}
            w.writerow([
                d.get("id"), d.get("tenderID"), d.get("dateCreated"), d.get("dateModified"),
                d.get("status"), d.get("mainProcurementCategory"),
                cpv.get("id"), cpv.get("description"),
                val.get("amount"), val.get("currency"),
                pe.get("name"), pe.get("identifier", {}).get("id"),
                pe.get("address", {}).get("region"),
            ])

    digest = hashlib.sha256(flat_path.read_bytes()).hexdigest()
    n = sum(1 for _ in csv.reader(flat_path.open(encoding="utf-8", newline=""))) - 1
    print(f"{flat_path.name}: {n} строк, sha256 {digest}")


if __name__ == "__main__":
    main()
