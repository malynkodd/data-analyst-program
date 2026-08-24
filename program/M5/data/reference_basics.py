"""Эталонные числа шага M5.02 «Язык-минимум аналитика» (умение B6).

Считает те же пятнадцать величин, что проверяет `test_basics.py`, но
другим кодом: здесь всё делается через `collections` и сортировку
готовыми ключами, в задании шага — руками, циклом и словарём. Это и есть
двойное авторство (скилл curriculum-design, раздел 1.3): числа в критерии
1.5 получены не тем же кодом, который их потом сверяет.

Запуск из корня репозитория:

    .venv\\Scripts\\python.exe program\\M5\\data\\reference_basics.py

Печатает все пятнадцать величин. Ничего не пишет на диск: эталон шага —
не CSV, а зелёный `pytest`, и второй копии чисел на диске быть не должно.

Определения, без которых числа ничего не значат (решение 30):

* **база** — только `raw/payouts_2026_q1.csv`, 1996 строк; вторая выгрузка
  (q2) в расчёт не входит нигде;
* **ключ** — `partner_code` как строка, без приведения к числу;
* **пустые** — строки с пустым `partner_code` (262) выброшены везде, где
  считается «по партнёрам», и оставлены везде, где считается «по всем
  выплатам»; в каждой величине ниже это сказано отдельной строкой;
* **дубли** — в q1 их нет: `payout_id` уникален (инвариант генератора);
* **сравнение** — названия партнёров сравниваются строго, посимвольно, без
  обрезки пробелов и без приведения регистра. Другой способ сравнения даёт
  другое число вариантов — это предмет `ref_name_variants.csv` и шага
  M5.04, здесь фиксируется именно строгое сравнение.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"


def load_rows() -> list[dict[str, str]]:
    with (RAW / "payouts_2026_q1.csv").open(encoding="cp1251", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def load_pages() -> list[dict]:
    return json.loads((RAW / "fees_api.json").read_text(encoding="utf-8"))["pages"]


def amount(row: dict[str, str]) -> float:
    return float(row["amount"].replace(",", "."))


def main() -> int:
    rows = load_rows()
    pages = load_pages()

    amounts = [amount(r) for r in rows]
    paid = [amount(r) for r in rows if r["status"] == "PAID"]
    codes = [r["partner_code"].strip() for r in rows]

    by_partner: dict[str, float] = defaultdict(float)
    for row in rows:
        code = row["partner_code"].strip()
        if code and row["status"] == "PAID":
            by_partner[code] += amount(row)
    top5 = sorted(by_partner.items(), key=lambda kv: (-kv[1], kv[0]))[:5]

    variants: dict[str, set[str]] = defaultdict(set)
    first_name: dict[str, str] = {}
    for row in rows:
        code = row["partner_code"].strip()
        if not code:
            continue
        variants[code].add(row["partner_name"])
        first_name.setdefault(code, row["partner_name"])

    def bucket(value: float) -> str:
        if value < 20000:
            return "малая"
        if value < 60000:
            return "средняя"
        return "крупная"

    dates = sorted({r["payout_date"] for r in rows}, key=lambda d: (d[6:], d[3:5], d[:2]))
    fee_ids = [item["payout_id"] for page in pages for item in page["items"]]

    print("строк в q1:", len(rows))
    print("1  to_amount('49088,78') =", float("49088,78".replace(",", ".")))
    print("2  total_amount (все 1996 строк) = %.2f" % sum(amounts))
    print("3  paid_amount (только status == 'PAID') = %.2f" % sum(paid))
    print("4  count_by_status =", dict(Counter(r["status"] for r in rows)))
    print("5  unique_codes (непустые) =", len({c for c in codes if c}))
    print("6  rows_without_code =", sum(1 for c in codes if not c))
    print("7  size_bucket: границы 20000 и 60000, включительно снизу")
    print("8  bucket_counts (все строки) =", dict(Counter(bucket(a) for a in amounts)))
    print(
        "9  big_paid_ids(limit=80000) =",
        sum(1 for r in rows if r["status"] == "PAID" and amount(r) > 80000),
        "строк",
    )
    print("10 top_partners(5) =", [(c, round(v, 2)) for c, v in top5])
    print("11 period =", (dates[0], dates[-1]), "| уникальных дат:", len(dates))
    print("12 page_item_counts =", [len(p["items"]) for p in pages])
    print("13 элементов комиссий:", len(fee_ids), "| unique_fee_ids =", len(set(fee_ids)))
    print(
        "14 name_variants: кодов",
        len(variants),
        "| сумма вариантов",
        sum(len(v) for v in variants.values()),
        "| у 30000036:",
        len(variants["30000036"]),
    )
    print("15 partner_names['30000036'] =", repr(first_name["30000036"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
