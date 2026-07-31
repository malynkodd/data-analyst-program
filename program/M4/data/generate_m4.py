"""Генератор сквозного датасета модуля M4 (Power BI).

Запуск:

    python generate_m4.py

Пишет две папки рядом с собой:

    csv/       — базовый период, 2025-01-01 .. 2026-06-30 (умение C1)
    csv_next/  — тот же набор, продлённый по 2026-07-31 (умение C2:
                 подмена файла + Refresh)

Пять файлов в каждой папке: transactions.csv, merchants.csv,
mcc_categories.csv, merchant_plan.csv, calendar.csv.

Ни одна из папок не коммитится (`.gitignore` в корне репозитория) —
решение 22 `design/decisions.md`, раздел «Что коммитится»: в git лежат
генератор и контрольная точка, а не данные. Скрипт печатает после
генерации число строк и sha256 каждого файла — учащийся сверяет их с
`reference_answers.md`, раздел «Контрольная точка», ДО того, как
приступать к задачам шагов.

Детерминированность: `SEED` задан до первого обращения к генератору
случайных чисел, порядок вызовов фиксирован циклами. Повторный запуск
даёт побайтово те же файлы.

Кодировка и перевод строки заданы явно (решение 17): UTF-8 **без BOM**,
CRLF. Ровно та конфигурация, на которой прогонялся гейт
(`research/tools-gate.md`, раздел 3), — файлы гейта тоже писались
`csv.writer` с `lineterminator="\\r\\n"`, а не редиректом.
"""

from __future__ import annotations

import csv
import hashlib
import random
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

SEED = 20260731
RNG = random.Random(SEED)

HERE = Path(__file__).resolve().parent

BASE_START = date(2025, 1, 1)
BASE_END = date(2026, 6, 30)
NEXT_END = date(2026, 7, 31)

MONTHS_UK = [
    "січень", "лютий", "березень", "квітень", "травень", "червень",
    "липень", "серпень", "вересень", "жовтень", "листопад", "грудень",
]

# code, category_name, минимальная и максимальная сумма операции
CATEGORIES = [
    (4121, "Таксі та перевезення", 45, 450),
    (5411, "Продуктові магазини", 80, 2500),
    (5541, "АЗС та пальне", 300, 3500),
    (5812, "Кафе та ресторани", 120, 1800),
    (5912, "Аптеки", 40, 1200),
    (6012, "Фінансові послуги", 500, 9000),
]

# merchant_id, merchant_name, city, mcc.
# Две записи содержат запятую внутри значения, две другие — перевод строки
# внутри значения (многострочный адрес, `MULTILINE_ADDRESS` ниже). Это не
# украшение: коннектор «Текст или CSV» пишет QuoteStyle = QuoteStyle.None
# (измерено, `research/tools-gate.md`, P8), а по документации
# [Csv.Document](https://learn.microsoft.com/en-us/powerquery-m/csv-document)
# при этом значении «все переводы строки считаются концом строки, даже
# когда встречаются внутри значения в кавычках». Без многострочного
# значения требование задавать QuoteStyle руками нечем проверить: запятую
# внутри кавычек разбирает не QuoteStyle, а CsvStyle, и его умолчание
# (`QuoteAfterDelimiter`) с ней справляется.
MERCHANTS = [
    (101, "ТОВ «Аврора Маркет»", "Київ", 5411),
    (102, "ТОВ «Світанок»", "Київ", 5411),
    (103, "Мережа АЗС «Крок», ТОВ", "Київ", 5541),
    (104, "ТОВ «Тепла Кава»", "Київ", 5812),
    (105, "Аптека «Добродія», ФОП", "Київ", 5912),
    (106, "ТОВ «ШвидкоТаксі»", "Київ", 4121),
    (107, "ТОВ «Фінпорт»", "Київ", 6012),
    (108, "ТОВ «Харківський Гастроном»", "Харків", 5411),
    (109, "ТОВ «Слобожанський Смак»", "Харків", 5812),
    (110, "ТОВ «Автолідер»", "Харків", 5541),
    (111, "ТОВ «Здорова Родина»", "Харків", 5912),
    (112, "ТОВ «Портовий Маркет»", "Одеса", 5411),
    (113, "ТОВ «Причал»", "Одеса", 5812),
    (114, "ТОВ «Одеса Таксі»", "Одеса", 4121),
    (115, "ТОВ «Гривня Плюс»", "Одеса", 6012),
    (116, "ТОВ «Січ Маркет»", "Дніпро", 5411),
    (117, "ТОВ «Дніпро Пальне»", "Дніпро", 5541),
    (118, "ТОВ «Аптека на Розі»", "Дніпро", 5912),
    (119, "ТОВ «Львівська Кава»", "Львів", 5812),
    (120, "ТОВ «Ратуша Маркет»", "Львів", 5411),
    (121, "ТОВ «Левеня Таксі»", "Львів", 4121),
    (122, "ТОВ «Поділля Пальне»", "Вінниця", 5541),
    (123, "ТОВ «Полтавський Двір»", "Полтава", 5812),
    (124, "ТОВ «Запорізький Фінсервіс»", "Запоріжжя", 6012),
]

# Новый мерчант появляется только в csv_next/ — вместе с городом, которого
# в базовом периоде нет ни в одной строке. Условие 3 переформулированного
# критерия C2 (решение 22): файл следующего месяца обязан содержать
# кириллицу, которой не было в файле первого месяца.
NEW_MERCHANT = (125, "ТОВ «Ужгородський Транзит»", "Ужгород", 4121)

# Многострочный адрес — у двух мерчантов из 24. Перевод строки внутри
# значения в кавычках: ровно тот случай, который разбирает параметр
# QuoteStyle и не разбирает ничто другое.
MULTILINE_ADDRESS = {
    101: "вул. Хрещатик, 12\nоф. 407",
    112: "вул. Дерибасівська, 8\nпід'їзд 2, оф. 15",
}


def address_of(merchant_id: int, city: str) -> str:
    return MULTILINE_ADDRESS.get(merchant_id, f"м. {city}, вул. Центральна, {merchant_id % 50 + 1}")

PLAN_RATES = {"basic": Decimal("0.025"), "standard": Decimal("0.019"), "premium": Decimal("0.014")}

STATUSES = ["settled", "declined", "refunded"]
STATUS_WEIGHTS = [0.85, 0.11, 0.04]

TX_HEADER = ["tx_id", "merchant_id", "tx_date", "settled_date", "mcc", "status",
             "amount_uah", "period_ym"]


def months_between(start: date, end: date) -> list[str]:
    out: list[str] = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def business_shift(d: date, days: int) -> date:
    """Дата расчёта: +1..3 дня, с переносом с выходных на понедельник.

    Из-за переноса часть операций конца месяца рассчитывается уже в
    следующем месяце — это и делает `settled_date` второй колонкой-
    кандидатом на связь с календарём (решение 22, ограничение C1, случай 2),
    а не копией `tx_date` со сдвигом."""
    out = d + timedelta(days=days)
    while out.weekday() >= 5:
        out += timedelta(days=1)
    return out


def build_plans(merchants: list[tuple], periods: list[str]) -> list[dict]:
    """Тариф мерчанта по месяцам. Часть мерчантов тариф меняет — из-за
    этого связь с фактом идёт по паре (мерчант, период), а не по мерчанту."""
    rows: list[dict] = []
    for merchant_id, _name, _city, _mcc in merchants:
        plan = RNG.choice(["basic", "standard", "premium"])
        switch_at = RNG.randrange(len(periods)) if RNG.random() < 0.55 else None
        for i, period in enumerate(periods):
            if switch_at is not None and i == switch_at:
                plan = RNG.choice([p for p in PLAN_RATES if p != plan])
            rows.append({
                "merchant_ref": merchant_id,
                "period_ym": period,
                "plan_code": plan,
                "commission_pct": str(PLAN_RATES[plan]),
            })
    return rows


def build_transactions(merchants: list[tuple], start: date, end: date) -> list[dict]:
    cat_range = {code: (lo, hi) for code, _name, lo, hi in CATEGORIES}
    rows: list[dict] = []
    tx_id = 500001
    day = start
    while day <= end:
        for _ in range(RNG.randint(8, 16)):
            merchant_id, _name, _city, mcc = RNG.choice(merchants)
            lo, hi = cat_range[mcc]
            amount = Decimal(RNG.randrange(lo * 100, hi * 100)) / 100
            status = RNG.choices(STATUSES, STATUS_WEIGHTS)[0]
            rows.append({
                "tx_id": tx_id,
                "merchant_id": merchant_id,
                "tx_date": day.isoformat(),
                "settled_date": business_shift(day, RNG.randint(1, 3)).isoformat(),
                "mcc": mcc,
                "status": status,
                "amount_uah": f"{amount:.2f}",
                "period_ym": day.isoformat()[:7],
            })
            tx_id += 1
        day += timedelta(days=1)
    return rows


def build_calendar(start: date, end: date) -> list[dict]:
    rows: list[dict] = []
    day = start
    while day <= end:
        rows.append({
            "date_key": day.isoformat(),
            "year": day.year,
            "month_no": day.month,
            "month_uk": MONTHS_UK[day.month - 1],
        })
        day += timedelta(days=1)
    return rows


def write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    # Кодировка названа явно (решение 17). BOM не пишется: гейт мерил
    # именно файлы без BOM, и M-код шагов задаёт Encoding = 65001 руками.
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\r\n")
        w.writerow(header)
        for r in rows:
            w.writerow([r[c] for c in header])


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_folder(folder: Path, files: list[tuple[str, list[str], list[dict]]]) -> list[tuple[str, int, str]]:
    folder.mkdir(parents=True, exist_ok=True)
    out: list[tuple[str, int, str]] = []
    for name, header, rows in files:
        path = folder / name
        write_csv(path, header, rows)
        out.append((name, len(rows), sha256_of(path)))
    return out


def main() -> int:
    print(f"SEED = {SEED}")

    # Один прогон генератора на оба периода: csv_next обязан быть
    # надмножеством csv, иначе подмена файла в C2 читалась бы как
    # «пришли другие данные за те же месяцы», а не «добавился месяц».
    periods_all = months_between(BASE_START, NEXT_END)
    plans_old = build_plans(MERCHANTS, periods_all)
    tx_old = build_transactions(MERCHANTS, BASE_START, NEXT_END)
    plans_new = build_plans([NEW_MERCHANT], periods_all[-1:])
    tx_new = build_transactions([NEW_MERCHANT], date(2026, 7, 1), NEXT_END)
    calendar_all = build_calendar(BASE_START, NEXT_END)

    base_periods = set(months_between(BASE_START, BASE_END))
    merchant_header = ["merchant_id", "merchant_name", "city", "address"]
    merchant_rows = [{"merchant_id": m, "merchant_name": n, "city": c,
                      "address": address_of(m, c)} for m, n, c, _k in MERCHANTS]
    category_rows = [{"code": c, "category_name": n} for c, n, _lo, _hi in CATEGORIES]

    layout = {
        "csv": [
            ("merchants.csv", merchant_header, merchant_rows),
            ("mcc_categories.csv", ["code", "category_name"], category_rows),
            ("merchant_plan.csv", ["merchant_ref", "period_ym", "plan_code", "commission_pct"],
             [r for r in plans_old if r["period_ym"] in base_periods]),
            ("calendar.csv", ["date_key", "year", "month_no", "month_uk"],
             [r for r in calendar_all if r["date_key"] <= BASE_END.isoformat()]),
            ("transactions.csv", TX_HEADER,
             [r for r in tx_old if r["tx_date"] <= BASE_END.isoformat()]),
        ],
        "csv_next": [
            ("merchants.csv", merchant_header,
             merchant_rows + [{"merchant_id": NEW_MERCHANT[0], "merchant_name": NEW_MERCHANT[1],
                               "city": NEW_MERCHANT[2],
                               "address": address_of(NEW_MERCHANT[0], NEW_MERCHANT[2])}]),
            ("mcc_categories.csv", ["code", "category_name"], category_rows),
            ("merchant_plan.csv", ["merchant_ref", "period_ym", "plan_code", "commission_pct"],
             plans_old + plans_new),
            ("calendar.csv", ["date_key", "year", "month_no", "month_uk"], calendar_all),
            ("transactions.csv", TX_HEADER, tx_old + tx_new),
        ],
    }

    for name, files in layout.items():
        print(f"\n{name}/")
        for fname, rows, digest in write_folder(HERE / name, files):
            print(f"  {fname}: {rows} строк, sha256 {digest}")
    print("\nСверьте эти числа с data/reference_answers.md, раздел "
          "«Контрольная точка», до начала задач шага.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
