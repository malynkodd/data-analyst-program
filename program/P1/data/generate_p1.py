"""Генератор датасета P1 — сеть из 12 магазинов, вопрос «какую точку
закрывать первой».

Период: 2026-01-01 .. 2026-06-30 (181 день, 26 недель). Пишет
program/P1/data/sales_transactions.csv — построчные продажи и возвраты
(один столбец amount, знак определяет тип).

Четыре дефекта встроены намеренно, под умение принять решение (часть 5
blueprint, P1):
1. Три точки (103, 106, 109) меняют внутренний store_id в середине
   периода — store_name/city остаются теми же, это единственная зацепка
   для склейки.
2. Возвраты — отрицательные суммы в том же столбце amount, что и
   продажи; отдельного флага «это возврат» нет.
3. Даты до 2026-04-01 записаны как DD.MM.YYYY (старая касса), с
   2026-04-01 — как YYYY-MM-DD (миграция кассовой системы в начале
   апреля).
4. Две точки (104, 111) закрыты на 6-недельный ремонт — 0 строк за этот
   период.

SEED зафиксирован до первого обращения к random (решение 29).
"""
import csv
import hashlib
import random
import sys
from datetime import date, timedelta
from pathlib import Path

# Кириллица в консоли не полагается на кодировку терминала
# (решение 17; симуляция 2026-09-04, дефект M9-1: без этой строки
# скрипт падал с UnicodeEncodeError, допечатав часть вывода).
sys.stdout.reconfigure(encoding="utf-8")

SEED = 20260821
random.seed(SEED)

OUT_DIR = Path(__file__).resolve().parent / "raw"
OUT_DIR.mkdir(exist_ok=True)
START = date(2026, 1, 1)
END = date(2026, 6, 30)
DAYS = (END - START).days + 1  # 181
DATE_FORMAT_CUTOVER = date(2026, 4, 1)

# store_id -> (city, street, базовый дневной оборот, доля возвратов)
STORES = {
    101: ("Київ", "вул. Хрещатик", 26000, 0.05),
    102: ("Київ", "просп. Перемоги", 21000, 0.05),
    103: ("Львів", "вул. Городоцька", 15000, 0.05),  # сменит ID на 203
    104: ("Дніпро", "просп. Яворницького", 17000, 0.05),  # ремонт
    105: ("Одеса", "вул. Дерибасівська", 10500, 0.55),  # аномально высокая доля возвратов
    106: ("Харків", "вул. Сумська", 14000, 0.05),  # сменит ID на 206
    107: ("Запоріжжя", "просп. Соборний", 12500, 0.05),
    108: ("Вінниця", "вул. Соборна", 11000, 0.05),
    109: ("Полтава", "вул. Соборності", 9500, 0.05),  # сменит ID на 209
    110: ("Черкаси", "бул. Шевченка", 8800, 0.05),
    111: ("Житомир", "вул. Київська", 9000, 0.05),  # ремонт
    112: ("Суми", "вул. Соборна", 8200, 0.05),
}

# store_id -> (день смены ID (индекс от 0), новый ID)
ID_CHANGES = {
    103: (60, 203),   # 2026-03-02
    106: (100, 206),  # 2026-04-11
    109: (140, 209),  # 2026-05-21
}

# store_id -> (первый закрытый день, последний закрытый день) — 6 недель = 42 дня
RENOVATIONS = {
    104: (50, 91),   # 2026-02-20 .. 2026-04-02
    111: (95, 136),  # 2026-04-06 .. 2026-05-17
}


def fmt_date(d: date) -> str:
    if d < DATE_FORMAT_CUTOVER:
        return d.strftime("%d.%m.%Y")
    return d.strftime("%Y-%m-%d")


def store_id_for_day(base_id: int, day_idx: int) -> int:
    change = ID_CHANGES.get(base_id)
    if change and day_idx >= change[0]:
        return change[1]
    return base_id


def is_closed(base_id: int, day_idx: int) -> bool:
    ren = RENOVATIONS.get(base_id)
    return bool(ren and ren[0] <= day_idx <= ren[1])


def main() -> None:
    rows = []
    tx_id = 1
    for day_idx in range(DAYS):
        d = START + timedelta(days=day_idx)
        for base_id, (city, street, daily_turnover, return_rate) in STORES.items():
            if is_closed(base_id, day_idx):
                continue
            sid = store_id_for_day(base_id, day_idx)
            # число транзакций и их суммы — так, чтобы сумма продаж дня
            # была около daily_turnover с шумом +-20%
            n_sales = random.randint(15, 35)
            target = daily_turnover * random.uniform(0.8, 1.2)
            per_tx = target / n_sales
            for _ in range(n_sales):
                amount = round(per_tx * random.uniform(0.4, 1.8), 2)
                rows.append((tx_id, sid, city, street, fmt_date(d), amount))
                tx_id += 1
            # возвраты — отдельные строки, отрицательная сумма
            n_returns = max(0, round(n_sales * return_rate * random.uniform(0.6, 1.4)))
            for _ in range(n_returns):
                amount = -round(per_tx * random.uniform(0.4, 1.8), 2)
                rows.append((tx_id, sid, city, street, fmt_date(d), amount))
                tx_id += 1

    out = OUT_DIR / "sales_transactions.csv"
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tx_id", "store_id", "city", "street", "tx_date", "amount"])
        w.writerows(rows)

    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    print(f"{out.name}: {len(rows)} строк, sha256 {digest}")


if __name__ == "__main__":
    main()
