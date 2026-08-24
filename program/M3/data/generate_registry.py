"""Генератор `registry_seed.sql` — данные шага M3.13 (умение A6).

Две таблицы поверх схемы модуля:

* `partner_registry` — справочник контрагентов, 12 строк. Названия
  канонические: одинарные пробелы, «ёлочки», регистр как в реестре.
* `invoice_feed` — входящий поток счетов, 60 строк. Контрагент указан
  **только названием**, кода в потоке нет, и название приходит в пяти
  написаниях: канонично, капсом, с пробелами по краям, с двойными
  пробелами внутри, с прямыми кавычками вместо «ёлочек». Плюс 8 счетов
  от контрагентов, которых в справочнике нет вовсе. Двум партнёрам
  справочника (`partner_id` 11 и 12) не соответствует ни один счёт —
  это нужно, чтобы у `FULL OUTER JOIN` были непарные строки с обеих
  сторон, а не только со стороны потока.

Это не выдуманная грязь: ровно такой поток даёт любая выгрузка, где
контрагент вводится руками или приходит из чужой системы. Задача шага —
измерить, сколько строк теряется при соединении по такому ключу «в лоб»
и сколько остаётся после нормализации средствами SQL.

Детерминирован: никакой случайности, порядок строк задан списками.
Перегенерация даёт побайтово тот же файл.

Запуск из корня репозитория:

    .venv\\Scripts\\python.exe program\\M3\\data\\generate_registry.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
OUT = HERE / "registry_seed.sql"

PARTNERS = [
    (1, "ТОВ «Кобза Логістик»", "30000148"),
    (2, "ТОВ «Черемош Маркет»", "30000127"),
    (3, "ПП «Каштан Маркет»", "30000036"),
    (4, "ТОВ «Дніпро Трейд»", "30000099"),
    (5, "ТОВ «Карпати Сервіс»", "30000064"),
    (6, "ПП «Лиман Груп»", "30000078"),
    (7, "ТОВ «Славутич Пром»", "30000295"),
    (8, "ТОВ «Оріон Постач»", "30000311"),
    (9, "ПП «Едельвейс Плюс»", "30000402"),
    (10, "ТОВ «Барвінок Агро»", "30000455"),
    (11, "ТОВ «Тиса Транс»", "30000501"),
    (12, "ПП «Верховина Буд»", "30000577"),
]

UNKNOWN = [
    "ТОВ «Незалежний Постачальник»",
    "ФОП Іваненко І. І.",
    "ТОВ «Січ Логістик»",
    "ПП «Дністер Опт»",
    "ТОВ «Полісся Ресурс»",
    "ФОП Петренко П. П.",
    "ТОВ «Бескид Сервіс»",
    "ПП «Азов Постач»",
]


def variant(name: str, form: int) -> str:
    """Пять написаний одного и того же названия."""
    if form == 0:
        return name
    if form == 1:
        return name.upper()
    if form == 2:
        return f"  {name} "
    if form == 3:
        return name.replace(" ", "  ")
    return name.replace("«", '"').replace("»", '"')


def main() -> int:
    lines: list[str] = [
        "-- Данные шага M3.13 (умение A6): справочник контрагентов и поток",
        "-- счетов, где контрагент указан только названием и в пяти",
        "-- написаниях. Файл порождается generate_registry.py, руками не",
        "-- правится: перегенерация даёт побайтово тот же результат.",
        "",
        "CREATE TABLE partner_registry (",
        "    partner_id INTEGER PRIMARY KEY,",
        "    legal_name TEXT NOT NULL,",
        "    edrpou     TEXT NOT NULL",
        ");",
        "",
        "CREATE TABLE invoice_feed (",
        "    invoice_id      INTEGER PRIMARY KEY,",
        "    counterparty_raw TEXT NOT NULL,",
        "    invoice_date    TEXT NOT NULL,",
        "    amount          REAL NOT NULL",
        ");",
        "",
        "INSERT INTO partner_registry (partner_id, legal_name, edrpou) VALUES",
    ]
    rows = [f"({pid}, '{name}', '{code}')" for pid, name, code in PARTNERS]
    lines.append(",\n".join(rows) + ";")
    lines.append("")
    lines.append(
        "INSERT INTO invoice_feed (invoice_id, counterparty_raw, invoice_date, amount) VALUES"
    )

    feed: list[str] = []
    invoice_id = 9001
    # 52 счёта от известных контрагентов: 12 партнёров, формы по кругу
    active = PARTNERS[:10]  # партнёры 11 и 12 остаются без счетов
    for index in range(52):
        pid, name, _ = active[index % len(active)]
        form = (index // len(active) + index) % 5
        raw = variant(name, form).replace("'", "''")
        day = 1 + (index % 28)
        amount = 1000.00 + index * 137.50
        feed.append(f"({invoice_id}, '{raw}', '2026-06-{day:02d}', {amount:.2f})")
        invoice_id += 1
    # 8 счетов от контрагентов вне справочника
    for index, name in enumerate(UNKNOWN):
        raw = name.replace("'", "''")
        day = 1 + (index % 28)
        amount = 2500.00 + index * 211.25
        feed.append(f"({invoice_id}, '{raw}', '2026-06-{day:02d}', {amount:.2f})")
        invoice_id += 1

    lines.append(",\n".join(feed) + ";")
    lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8")

    forms = [0] * 5
    for index in range(52):
        forms[(index // 10 + index) % 5] += 1
    print("registry_seed.sql записан:", OUT)
    print("партнёров в справочнике:", len(PARTNERS), "| из них без счетов: 2")
    print("счетов всего:", len(feed), "| от известных:", 52, "| от неизвестных:", len(UNKNOWN))
    print("распределение написаний среди 52 известных:")
    labels = ["канонично", "капсом", "пробелы по краям", "двойные пробелы", "прямые кавычки"]
    for label, count in zip(labels, forms):
        print(f"  {label:<20} {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
