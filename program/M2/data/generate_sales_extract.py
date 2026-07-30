"""
Генератор сквозного датасета модуля M2 (Таблицы).

Синтетика. Спецификация встроенных дефектов — в program/M2/data/README.md.
Запуск детерминирован (SEED фиксирован), поэтому файлы можно
перегенерировать и получить побайтово тот же результат.

Категория (часть 1.3 curriculum-design): синтетика для модуля, ведущего к
проекту (M2 -> P1, часть 3.1 blueprint) - генератор и спецификация
дефектов лежат в репозитории, эталон известен точно. Собственный датасет
P1 (сеть из 12 магазинов) пишется отдельно при авторинге P1 - это не то
же самое, что учебный датасет M2.

Строятся два файла:
- sales_extract_raw.csv (20 000 строк) - "грязная" выгрузка продаж.
- product_lookup.csv (60 товаров) - справочник для XLOOKUP/INDEX+MATCH
  (D2). Часть product_id в sales_extract_raw.csv намеренно отсутствует в
  этом справочнике (снятые с продажи товары) - это и есть материал для
  задач на IFERROR/IFNA.

Четыре встроенных дефекта sales_extract_raw.csv, все документированы в
README.md:
1. order_date_raw - два формата (ISO и DD.MM.YYYY), различимы по
   разделителю (- против .), без обратной неоднозначности.
2. category_raw - 5 канонических категорий, каждая встречается в 5
   вариантах регистра/пробелов.
3. amount_raw - число как текст, 4 варианта формата (точка, запятая как
   десятичный разделитель, пробел как разделитель тысяч, суффикс "грн"),
   плюс возвраты - отрицательные суммы в той же колонке, часть из них в
   "бухгалтерском" формате (в скобках вместо минуса).
4. product_id - 4% строк ссылаются на товар, которого нет в
   product_lookup.csv (снят с продажи).
"""

import csv
import random
from datetime import date, timedelta

SEED = 20260802
N = 20000

CATEGORIES = ["Ноутбуки", "Смартфони", "Аксесуари", "Побутова техніка", "Одяг"]
CATEGORY_CODE = {
    "Ноутбуки": "laptops",
    "Смартфони": "phones",
    "Аксесуари": "accessories",
    "Побутова техніка": "appliances",
    "Одяг": "clothing",
}
PRICE_RANGE = {
    "Ноутбуки": (8000, 35000),
    "Смартфони": (3000, 25000),
    "Аксесуари": (100, 2000),
    "Побутова техніка": (1500, 20000),
    "Одяг": (200, 3000),
}
CHANNELS = ["online", "retail", "wholesale"]
CHANNEL_WEIGHTS = [0.45, 0.40, 0.15]

N_PRODUCTS_REAL = 60
N_PRODUCTS_DISCONTINUED = 15

START_DATE = date(2024, 1, 1)
END_DATE = date(2025, 12, 31)
DATE_SPAN_DAYS = (END_DATE - START_DATE).days

random.seed(SEED)


def noisy_category(canonical):
    roll = random.random()
    if roll < 0.40:
        return canonical
    elif roll < 0.60:
        return canonical.lower()
    elif roll < 0.75:
        return canonical.upper()
    elif roll < 0.90:
        return canonical + " "
    else:
        return " " + canonical.lower() + " "


def random_date():
    return START_DATE + timedelta(days=random.randint(0, DATE_SPAN_DAYS))


def format_date(d):
    if random.random() < 0.55:
        return d.isoformat()
    return d.strftime("%d.%m.%Y")


def quarter_label(d):
    q = (d.month - 1) // 3 + 1
    return f"{d.year}-Q{q}"


def format_amount(value, is_return):
    style = random.choices(["plain", "comma", "thousands", "currency"], weights=[0.55, 0.20, 0.15, 0.10])[0]
    abs_value = abs(value)
    if style == "plain":
        text = f"{abs_value:.2f}"
    elif style == "comma":
        text = f"{abs_value:.2f}".replace(".", ",")
    elif style == "thousands":
        text = f"{abs_value:,.2f}".replace(",", " ")
    else:  # currency
        text = f"{abs_value:.2f} грн"

    if is_return:
        if random.random() < 0.50:
            return f"({text})"
        return f"-{text}"
    return text


def make_product_catalog():
    products = []
    for i in range(1, N_PRODUCTS_REAL + 1):
        category = CATEGORIES[(i - 1) % len(CATEGORIES)]
        lo, hi = PRICE_RANGE[category]
        unit_cost = round(random.uniform(lo * 0.5, lo * 0.8), 2)
        products.append({
            "product_id": f"P{i:03d}",
            "product_name": f"{CATEGORY_CODE[category]}-{i:03d}",
            "category": category,
            "unit_cost": unit_cost,
        })
    return products


def make_sale_row(order_id, catalog):
    real_ids = [p["product_id"] for p in catalog]
    if random.random() < 0.04:
        product_id = f"P{random.randint(N_PRODUCTS_REAL + 1, N_PRODUCTS_REAL + N_PRODUCTS_DISCONTINUED):03d}"
        category = random.choice(CATEGORIES)
    else:
        product = random.choice(catalog)
        product_id = product["product_id"]
        category = product["category"]

    d = random_date()
    lo, hi = PRICE_RANGE[category]
    unit_price = round(random.uniform(lo, hi), 2)
    quantity = random.randint(1, 5)
    is_return = random.random() < 0.05
    raw_total = quantity * unit_price
    signed_total = -raw_total if is_return else raw_total

    return {
        "order_id": f"S{order_id:05d}",
        "order_date_raw": format_date(d),
        "category_raw": noisy_category(category),
        "product_id": product_id,
        "channel": random.choices(CHANNELS, weights=CHANNEL_WEIGHTS)[0],
        "quantity": quantity,
        "unit_price": f"{unit_price:.2f}",
        "amount_raw": format_amount(signed_total, is_return),
    }


def main():
    catalog = make_product_catalog()

    with open("product_lookup.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["product_id", "product_name", "category", "unit_cost"])
        writer.writeheader()
        writer.writerows(catalog)

    rows = [make_sale_row(i, catalog) for i in range(1, N + 1)]
    with open("sales_extract_raw.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "order_id", "order_date_raw", "category_raw", "product_id",
                "channel", "quantity", "unit_price", "amount_raw",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"written {len(catalog)} rows to product_lookup.csv")
    print(f"written {len(rows)} rows to sales_extract_raw.csv")


if __name__ == "__main__":
    main()
