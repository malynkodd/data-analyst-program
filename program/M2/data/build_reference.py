"""
Строит SQL-эталон для сквозного датасета M2: читает "грязный"
sales_extract_raw.csv, применяет ровно те правила очистки, которые
описаны в шагах модуля (program/M2/step-01.md, step-02.md), и печатает
контрольные суммы через SQL-запрос к sqlite (решение 15,
design/decisions.md, применяется здесь не к M3, а по тому же принципу:
эталон - реальный SQL, а не посчитанное вручную число).

Все контрольные числа в reference_answers.md и в текстах шагов M2 взяты
из вывода именно этого скрипта - ручной ввод чисел в шаги запрещён
(ограничение задачи Фазы 2).

category_code (laptops/phones/...) — стабильный ключ для SQL GROUP BY/
WHERE, не обход кодировки: обходной путь ASCII-вывода решение 17
отменяет с M2 и далее. Сырой кириллический category_raw читается,
очищается и остаётся в самом шаге (step-02.md) — кодом заменяется
только внутренний ключ группировки в этом скрипте.
"""

import csv
import sqlite3
from datetime import date

CATEGORY_CODE = {
    "Ноутбуки": "laptops",
    "Смартфони": "phones",
    "Аксесуари": "accessories",
    "Побутова техніка": "appliances",
    "Одяг": "clothing",
}
CANONICAL_LOWER = {c.lower(): c for c in CATEGORY_CODE}


def clean_category(raw):
    canonical = CANONICAL_LOWER.get(raw.strip().lower())
    if canonical is None:
        raise ValueError(f"unrecognized category: {raw!r}")
    return canonical


def parse_date(raw):
    if "-" in raw:
        y, m, d = raw.split("-")
    else:
        d, m, y = raw.split(".")
    return date(int(y), int(m), int(d))


def quarter_label(d):
    q = (d.month - 1) // 3 + 1
    return f"{d.year}-Q{q}"


def parse_amount(raw):
    text = raw.strip()
    is_paren_negative = text.startswith("(") and text.endswith(")")
    if is_paren_negative:
        text = text[1:-1]
    text = text.replace(" грн", "").replace("грн", "").strip()
    text = text.replace(" ", "")
    if "," in text:
        text = text.replace(",", ".")
    value = float(text)
    if is_paren_negative:
        value = -value
    elif raw.strip().startswith("-"):
        value = -abs(value)
    return value


def load_lookup(path):
    return {r["product_id"] for r in csv.DictReader(open(path, encoding="utf-8"))}


def main():
    known_products = load_lookup("product_lookup.csv")

    con = sqlite3.connect(":memory:")
    con.execute(
        """
        CREATE TABLE sales (
            order_id TEXT, order_date TEXT, quarter TEXT, category_code TEXT,
            product_id TEXT, product_known INTEGER, channel TEXT,
            quantity INTEGER, unit_price REAL, amount REAL
        )
        """
    )

    rows = list(csv.DictReader(open("sales_extract_raw.csv", encoding="utf-8")))
    date_format_counts = {"iso": 0, "eu": 0}
    category_exact_counts = {code: 0 for code in CATEGORY_CODE.values()}
    category_total_counts = {code: 0 for code in CATEGORY_CODE.values()}
    return_count = 0
    return_paren_count = 0
    missing_product_count = 0

    to_insert = []
    for r in rows:
        d = parse_date(r["order_date_raw"])
        if "-" in r["order_date_raw"]:
            date_format_counts["iso"] += 1
        else:
            date_format_counts["eu"] += 1

        canonical = clean_category(r["category_raw"])
        code = CATEGORY_CODE[canonical]
        category_total_counts[code] += 1
        if r["category_raw"] == canonical:
            category_exact_counts[code] += 1

        amount = parse_amount(r["amount_raw"])
        if amount < 0:
            return_count += 1
            if r["amount_raw"].strip().startswith("("):
                return_paren_count += 1

        known = r["product_id"] in known_products
        if not known:
            missing_product_count += 1

        to_insert.append((
            r["order_id"], d.isoformat(), quarter_label(d), code,
            r["product_id"], 1 if known else 0, r["channel"],
            int(r["quantity"]), float(r["unit_price"]), amount,
        ))

    con.executemany(
        "INSERT INTO sales VALUES (?,?,?,?,?,?,?,?,?,?)", to_insert
    )
    con.commit()

    print("=== control sums (SQL reference) ===")

    grand_total = con.execute("SELECT ROUND(SUM(amount), 2) FROM sales").fetchone()[0]
    print(f"grand_total_amount: {grand_total}")

    print("--- total by category_code ---")
    for code, total in con.execute(
        "SELECT category_code, ROUND(SUM(amount),2) FROM sales GROUP BY category_code ORDER BY category_code"
    ):
        print(f"category={code} total={total}")

    print("--- total by category_code + quarter + channel (one slice combo) ---")
    combo = con.execute(
        "SELECT ROUND(SUM(amount),2), COUNT(*) FROM sales "
        "WHERE category_code='laptops' AND quarter='2025-Q2' AND channel='online'"
    ).fetchone()
    print(f"category=laptops quarter=2025-Q2 channel=online total={combo[0]} rows={combo[1]}")

    print("--- total by channel ---")
    for ch, total, cnt in con.execute(
        "SELECT channel, ROUND(SUM(amount),2), COUNT(*) FROM sales GROUP BY channel ORDER BY channel"
    ):
        print(f"channel={ch} total={total} rows={cnt}")

    print("--- total by quarter ---")
    for q, total, cnt in con.execute(
        "SELECT quarter, ROUND(SUM(amount),2), COUNT(*) FROM sales GROUP BY quarter ORDER BY quarter"
    ):
        print(f"quarter={q} total={total} rows={cnt}")

    print("--- total by category_code + channel (SUMIFS reference combos) ---")
    for cat, ch in [
        ("phones", "online"), ("appliances", "retail"), ("laptops", "wholesale"),
        ("clothing", "online"), ("accessories", "retail"),
    ]:
        total, cnt = con.execute(
            "SELECT ROUND(SUM(amount),2), COUNT(*) FROM sales WHERE category_code=? AND channel=?",
            (cat, ch),
        ).fetchone()
        print(f"category={cat} channel={ch} total={total} rows={cnt}")

    print("--- naive gross recompute (quantity*unit_price, ignores return sign) vs cleaned amount ---")
    naive, cleaned = con.execute(
        "SELECT ROUND(SUM(quantity*unit_price),2), ROUND(SUM(amount),2) FROM sales"
    ).fetchone()
    print(f"naive_gross_total={naive} cleaned_amount_total={cleaned} difference={round(naive-cleaned,2)}")

    print("=== defect counts ===")
    print(f"rows total: {len(rows)}")
    print(f"date format iso: {date_format_counts['iso']}")
    print(f"date format eu (DD.MM.YYYY): {date_format_counts['eu']}")
    print(f"return rows (negative amount): {return_count}")
    print(f"return rows formatted with parentheses: {return_paren_count}")
    print(f"return rows formatted with minus sign: {return_count - return_paren_count}")
    print(f"rows with product_id missing from product_lookup.csv: {missing_product_count}")
    print("--- category: exact-canonical spelling vs total rows ---")
    for code in sorted(CATEGORY_CODE.values()):
        exact = category_exact_counts[code]
        total = category_total_counts[code]
        print(f"category={code} exact_spelling={exact} total_rows={total} needs_cleaning={total - exact}")


if __name__ == "__main__":
    main()
