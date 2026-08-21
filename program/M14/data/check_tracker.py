"""Проверка трекера откликов умения J3 (program/M14/step-01.md).

Читает program\\M14\\work\\tracker.csv и проверяет структуру и пять
учебных строк-примеров: заголовок из 9 колонок в заданном порядке, ровно
пять строк данных, среди компаний — все пять компаний из решения 5
(design/decisions.md) с верными ссылками из research/market.md, и нулевая
доля строк с geo_open = "ні" (заведомо закрытая география) — критерий
J3 части 1 blueprint.

Пять примеров учебные, а не результат реального поиска: колонка status
у каждого стоит "приклад", а не "відгук" — реальное 4-недельное ведение
трекера начинается после модуля (DEFERRED.md, раздел "Ведение трекера
откликов (J3)").
"""
import csv
import sys
from pathlib import Path

TRACKER = Path(__file__).resolve().parent.parent / "work" / "tracker.csv"

REQUIRED_HEADER = [
    "дата", "компанія", "посада", "канал", "посилання",
    "регіон", "geo_open", "мін_досвід", "статус",
]

# Компанії названі рішенням 5 (design/decisions.md) як приклад
# junior-сегменту UA-вибірки; посилання звірені з research/market.md
# (рядки 16/19, 26, 27, 29, 30).
REQUIRED_COMPANIES = {
    "Є гроші", "Symbol", "SKELAR", "Everstar", "WOG",
}

FAILED = False


def ok(msg: str) -> None:
    print(f"[OK]   {msg}")


def bad(msg: str) -> None:
    global FAILED
    print(f"[FAIL] {msg}")
    FAILED = True


def main() -> int:
    if not TRACKER.exists():
        bad(f"{TRACKER} не найден — трекер ещё не создан")
        return 1

    with TRACKER.open(encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))

    if not rows:
        bad("файл пуст")
        return 1

    header, data = rows[0], rows[1:]
    if header == REQUIRED_HEADER:
        ok(f"заголовок: {len(header)} колонок, порядок верный")
    else:
        bad(f"заголовок не совпадает. ожидалось {REQUIRED_HEADER}, получено {header}")

    if len(data) == 5:
        ok("строк данных: 5")
    else:
        bad(f"строк данных: {len(data)}, ожидалось 5")

    companies = {r[1].strip() for r in data if len(r) > 1}
    missing = REQUIRED_COMPANIES - companies
    if not missing:
        ok("все пять компаний решения 5 присутствуют")
    else:
        bad(f"компаний не хватает: {sorted(missing)}")

    geo_idx = REQUIRED_HEADER.index("geo_open")
    closed = [r for r in data if len(r) > geo_idx and r[geo_idx].strip().lower() == "ні"]
    if not closed:
        ok(f"доля закрытых географий: 0 из {len(data)}")
    else:
        bad(f"закрытых географий: {len(closed)} из {len(data)}, ожидалось 0")

    status_idx = REQUIRED_HEADER.index("статус")
    non_example = [r for r in data if len(r) > status_idx and r[status_idx].strip() != "приклад"]
    if not non_example:
        ok("все пять строк помечены 'приклад' — учебные, не реальные отклики")
    else:
        bad(f"строк без пометки 'приклад': {len(non_example)} — это уже реальные отклики, "
            f"учебный критерий их не покрывает")

    print()
    if FAILED:
        print("НЕ СОШЛОСЬ. Шаг не закрыт.")
        print("код возврата: 1")
        return 1
    print("ВСЁ СОШЛОСЬ: расхождений 0.")
    print("код возврата: 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
