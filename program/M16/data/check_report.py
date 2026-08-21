"""Проверка отчёта Looker Studio поверх BigQuery (умение C4, step-01.md).

Датасет M7 не детерминирован (`amount` — RAND(), решение 29 сознательно
не требует seed для облачных модулей с оплатой по объёму) — эталон
здесь не фиксированное число, а самосогласованность: то, что учащийся
получил SQL-запросом в консоли BigQuery, обязано совпасть с тем, что
показывает отчёт при тех же условиях (без применённых фильтров).

Читает program\\M16\\work\\report_log.md, проверяет:
1. Формат публичной ссылки — регэксп на `/reporting/...`, не живой
   HTTP-запрос. Живой запрос **испробован и отброшен этим же заходом**:
   lookerstudio.google.com отвечает HTTP 200 и для настоящего примера
   отчёта из документации Google, и для заведомо несуществующего
   `/reporting/00000000-...` — оба редиректят на общую страницу
   `/overview` при запросе без браузерной сессии (нет cookies, не
   выполняется JS). Различить «живой» и «мёртвый» отчёт скриптом без
   реального браузера нельзя — открытие ссылки проверяет тот, кто
   должен убедиться, что критерий выполнен: пункт задания требует
   открыть ссылку в приватном окне браузера самостоятельно
   (`DEFERRED.md`, раздел «Проверка публичной ссылки Looker Studio»).
2. SQL-итог и итог отчёта без фильтров — расхождение 0.
3. Три отфильтрованных числа — каждое обязано отличаться от итога без
   фильтров (иначе фильтр ни на что не влияет, «работает» только по
   виду).
"""
import re
import sys
from pathlib import Path

LOG = Path(__file__).resolve().parent.parent / "work" / "report_log.md"

URL_RE = re.compile(r"https://lookerstudio\.google\.com/(?:u/\d+/)?reporting/\S+")
NUM_RE = re.compile(r"[-+]?\d[\d,]*\.?\d*")

FIELDS = {
    "SQL-итог": None,
    "Отчёт без фильтров": None,
    "Отчёт с фильтром по дате": None,
    "Отчёт с фильтром по account_id": None,
    "Отчёт с фильтром по category": None,
}

FAILED = False


def ok(msg: str) -> None:
    print(f"[OK]   {msg}")


def bad(msg: str) -> None:
    global FAILED
    print(f"[FAIL] {msg}")
    FAILED = True


def parse_number(label: str, text: str) -> float | None:
    m = re.search(rf"{re.escape(label)}:\s*([-\d.,]+)", text)
    if not m:
        return None
    return float(m.group(1).replace(",", ""))


def main() -> int:
    if not LOG.exists():
        bad(f"{LOG} не найден")
        return 1

    text = LOG.read_text(encoding="utf-8")

    url_m = URL_RE.search(text)
    if not url_m:
        bad("report_log.md: ссылка вида lookerstudio.google.com/reporting/... не найдена")
    else:
        ok(f"формат ссылки верный: {url_m.group(0)} (живость проверяется вручную — "
           f"открыть в приватном окне браузера, задание 1.4, п. 7)")

    values = {}
    for label in FIELDS:
        v = parse_number(label, text)
        if v is None:
            bad(f"report_log.md: строка '{label}: <число>' не найдена")
        else:
            values[label] = v

    if "SQL-итог" in values and "Отчёт без фильтров" in values:
        if abs(values["SQL-итог"] - values["Отчёт без фильтров"]) <= 0.01:
            ok(f"SQL-итог совпадает с отчётом без фильтров: {values['SQL-итог']}")
        else:
            bad(f"SQL-итог {values['SQL-итог']} расходится с отчётом "
                f"{values['Отчёт без фильтров']} — цифры не сходятся с SQL")

    base = values.get("Отчёт без фильтров")
    for label in ("Отчёт с фильтром по дате", "Отчёт с фильтром по account_id",
                  "Отчёт с фильтром по category"):
        if base is None or label not in values:
            continue
        if abs(values[label] - base) > 0.01:
            ok(f"{label}: {values[label]} отличается от итога без фильтров — контрол работает")
        else:
            bad(f"{label}: {values[label]} совпадает с итогом без фильтров — "
                f"фильтр не изменил результат, значит контрол не работает "
                f"(или выбрано значение фильтра, покрывающее весь датасет)")

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
