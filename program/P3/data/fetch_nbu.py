"""Снапшот P3 — курсы валют НБУ, все валюты, 2020-01-01 .. 2026-08-21.

Бюллетень «на дату» отдаёт ~45 валют за раз (research/sources-gate.md,
раздел 2, подтверждено прогоном 2026-08-21). Массовый временной ряд —
`https://bank.gov.ua/NBU_Exchange/exchange_site?...&valcode=X` (путь
`NBU_Exchange`, не `statdirectory` — второй путь на этом наборе
параметров отдаёт по одной строке вместо всего диапазона, найдено
прогоном 2026-08-21, `statdirectory/exchange_site` из sources-gate.md
рассчитан на другую комбинацию параметров). Существует **только для
одной валюты за запрос**, поэтому обход — по валютам: список кодов
берётся с одной дневной выгрузки, дальше на каждую валюту — один
запрос на весь период.

**Дефект найден прогоном, не такой, как в описании части 5 blueprint.**
Blueprint называет «пропуски в выходные и праздники» — измерено иное:
строка на каждый календарный день **есть**, но курс на субботу и
воскресенье — не новое значение, а буквально то же число, что в
последний рабочий день перед ними (`calcdate` тоже не меняется).
Строки не пропущены, они задвоены неотличимо от свежих котировок —
дефект того же семейства (искажает наивный расчёт волатильности или
дневного изменения), но не идентичен формулировке blueprint дословно;
явный повод для П3 объяснить его как есть, а не подогнать текст под
ожидание.
"""
import csv
import hashlib
import json
import time
import urllib.request
from pathlib import Path

HEADERS = {"User-Agent": "data-analyst-program research (P3 snapshot)"}
OUT_DIR = Path(__file__).resolve().parent / "snapshot"
OUT_DIR.mkdir(exist_ok=True)

START = "20200101"
END = "20260821"


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
    today = fetch("https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?json")
    codes = sorted({row["cc"] for row in today if row.get("cc") and row["cc"] != "UAH"})
    print(f"валют на сегодня: {len(codes)}")

    out_path = OUT_DIR / "exchange_rates.csv"
    total = 0
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cc", "exchangedate", "rate", "txt"])
        for i, cc in enumerate(codes):
            url = (f"https://bank.gov.ua/NBU_Exchange/exchange_site"
                   f"?start={START}&end={END}&valcode={cc}&sort=exchangedate&json")
            try:
                rows = fetch(url)
            except Exception as exc:  # noqa: BLE001
                print(f"skip {cc}: {exc}")
                continue
            for r in rows:
                w.writerow([r["cc"], r["exchangedate"], r["rate"], r.get("txt", "")])
            total += len(rows)
            print(f"{i+1}/{len(codes)} {cc}: {len(rows)} строк (итого {total})")

    digest = hashlib.sha256(out_path.read_bytes()).hexdigest()
    print(f"\n{out_path.name}: {total} строк, sha256 {digest}")


if __name__ == "__main__":
    main()
