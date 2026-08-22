"""Снапшот P6 — курс USD/UAH, НБУ, весь период данных Держстату
(2015-01-01 .. дата запуска). Один код валюты — тот же путь массового
временного ряда, что нашёл P3 (`research/tools-gate.md`, S1 не
относится; сам путь — `program/P3/data/fetch_nbu.py`, найдено прогоном
2026-08-21): `NBU_Exchange/exchange_site`, не `statdirectory`.
"""
import csv
import hashlib
import json
import time
import urllib.request
from datetime import date
from pathlib import Path

HEADERS = {"User-Agent": "data-analyst-program research (P6 snapshot)"}
OUT_DIR = Path(__file__).resolve().parent / "snapshot"
OUT_DIR.mkdir(parents=True, exist_ok=True)

START = "20150101"
END = date.today().strftime("%Y%m%d")


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


def main() -> None:
    url = (f"https://bank.gov.ua/NBU_Exchange/exchange_site"
           f"?start={START}&end={END}&valcode=usd&sort=exchangedate&json")
    rows = fetch(url)
    out_path = OUT_DIR / "usd_uah.csv"
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "rate"])
        for r in rows:
            w.writerow([r["exchangedate"], r["rate"]])
    digest = hashlib.sha256(out_path.read_bytes()).hexdigest()
    print(f"{out_path.name}: {len(rows)} строк, sha256 {digest}")


if __name__ == "__main__":
    main()
