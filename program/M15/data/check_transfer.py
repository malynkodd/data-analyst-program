"""Проверка переноса дашборда M4 в Tableau Public (умение C3, step-02.md).

Три независимые проверки:
1. program\\M15\\work\\values.csv — шесть чисел, которые учащийся
   переписал с итогового визуала Tableau, сверяются с
   program\\M4\\data\\ref_totals.csv (тот же эталон, что закрывал C1 в
   M4, гейт подтвердил его сверкой с независимым SQL-расчётом).
2. program\\M15\\work\\transfer_log.md — публичная ссылка (регэксп
   ищет https://public.tableau.com/...) проверяется живым HTTP-запросом;
   строка "Затрачено: N ч" сверяется с порогом критерия C3, ≤6 ч.

Ни то, ни другое не читает сам файл .twbx — Tableau Public не даёт
машинного доступа к содержимому воркбука без своего API, которым эта
программа не пользуется (решение 20 CLAUDE.md, «условия проверки без
стороннего доступа»). Числа сверяются по тому, что учащийся сам
переписал с экрана, — тот же класс проверки, что у M4 (визуал/строка
состояния читает человек, скрипт сверяет число), не слепое доверие:
опечатку в переписанном числе поймает вторая проверка — публичная
ссылка, которую любой может открыть и свериться глазами.
"""
import csv
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
REF = ROOT / "program" / "M4" / "data" / "ref_totals.csv"
VALUES = Path(__file__).resolve().parent.parent / "work" / "values.csv"
LOG = Path(__file__).resolve().parent.parent / "work" / "transfer_log.md"

# Допуск по каждой мере — тот же, что задаёт критерий step-04.md M4:
# до второго знака, Decline Rate — до четвёртого, Tx Count — целое.
TOLERANCE = {
    "Total Amount": 0.005, "Settled Amount": 0.005, "Tx Count": 0.5,
    "Decline Rate": 0.00005, "Commission": 0.005, "Settled YTD": 0.005,
}

URL_RE = re.compile(r"https://public\.tableau\.com/\S+")
HOURS_RE = re.compile(r"Затрачено:\s*([\d.,]+)\s*ч")

FAILED = False


def ok(msg: str) -> None:
    print(f"[OK]   {msg}")


def bad(msg: str) -> None:
    global FAILED
    print(f"[FAIL] {msg}")
    FAILED = True


def read_csv_row(path: Path) -> dict:
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    return rows[0] if rows else {}


def main() -> int:
    if not VALUES.exists():
        bad(f"{VALUES} не найден")
        return 1
    if not LOG.exists():
        bad(f"{LOG} не найден")
        return 1

    ref = read_csv_row(REF)
    got = read_csv_row(VALUES)

    for metric, tol in TOLERANCE.items():
        if metric not in got:
            bad(f"{metric}: колонки нет в values.csv")
            continue
        try:
            g = float(got[metric])
            r = float(ref[metric])
        except ValueError:
            bad(f"{metric}: значение '{got[metric]}' не число")
            continue
        if abs(g - r) <= tol:
            ok(f"{metric}: {g} совпадает с Power BI ({r}), допуск {tol}")
        else:
            bad(f"{metric}: {g} расходится с Power BI ({r}) больше чем на {tol}")

    text = LOG.read_text(encoding="utf-8")
    url_m = URL_RE.search(text)
    if not url_m:
        bad("transfer_log.md: публичная ссылка public.tableau.com/... не найдена")
    else:
        url = url_m.group(0)
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                status = resp.status
        except Exception as exc:  # noqa: BLE001 — любая ошибка сети/сервера — это [FAIL]
            bad(f"ссылка {url} не открылась: {exc}")
        else:
            if status == 200:
                ok(f"публичная ссылка живая: {url} → HTTP {status}")
            else:
                bad(f"ссылка {url} вернула HTTP {status}, ожидался 200")

    hours_m = HOURS_RE.search(text)
    if not hours_m:
        bad("transfer_log.md: строка 'Затрачено: N ч' не найдена")
    else:
        hours = float(hours_m.group(1).replace(",", "."))
        if hours <= 6:
            ok(f"затрачено {hours} ч на перенос — укладывается в порог C3 (≤6 ч)")
        else:
            bad(f"затрачено {hours} ч — превышен порог C3 (≤6 ч)")

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
