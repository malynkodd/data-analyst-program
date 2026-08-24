"""Проверка шага M2.09 «Диаграмма под вопрос» (умение D4).

Первая машинная сверка в модуле M2: до 2026-08-24 все восемь шагов
модуля (31–41 ч) проверялись сверкой глазами с числами, напечатанными в
разделе 1.5 — это дефект CG-9 внешнего аудита.

Что проверяется — пять вещей, каждая с кодом возврата:

1. `work\\charts.csv` существует, содержит ровно шесть строк с id Q1…Q6 и
   шесть колонок;
2. выбранная форма совпадает с эталонной не менее чем в 5 случаях из 6;
3. ни одна выбранная форма не входит в список запрещённых (3D, круговая,
   пончик, двойная ось) — запрет из части 5 blueprint и acceptance
   criteria всех шести проектов;
4. у каждой строки заполнены ось X, ось Y, единицы измерения и причина
   выбора формы (причина — не короче пяти слов);
5. два экспортированных агрегата (`work\\chart_quarter.csv`,
   `work\\chart_channel_share.csv`) построчно совпадают с эталонами, и
   шесть картинок `work\\chart_q1.png` … `chart_q6.png` существуют и
   весят не меньше 5 КБ.

Запуск из корня репозитория:

    .venv\\Scripts\\python.exe program\\M2\\data\\check_charts.py

Код возврата 0 — шаг сдан, 1 — нет. Каждая непройденная проверка
печатает, что именно не сошлось, а не только «неверно».
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
WORK = HERE.parent / "work"

FORBIDDEN = ["3d", "объёмн", "объемн", "кругов", "пончик", "кольцев", "двойная ось"]
MIN_MATCH = 5
MIN_REASON_WORDS = 5
MIN_PNG_BYTES = 5 * 1024

COLUMNS = ["id", "тип_вопроса", "форма", "ось_x", "ось_y", "единицы", "почему"]

failures: list[str] = []


def fail(message: str) -> None:
    failures.append(message)
    print("[FAIL]", message)


def ok(message: str) -> None:
    print("[OK]  ", message)


def read_csv(path: Path) -> list[dict[str, str]] | None:
    if not path.exists():
        fail(f"нет файла {path}")
        return None
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def normalise(form: str) -> str:
    return " ".join(form.strip().lower().replace("ё", "е").split())


def check_choices() -> None:
    reference = read_csv(HERE / "ref_charts.csv")
    answer = read_csv(WORK / "charts.csv")
    if reference is None or answer is None:
        return

    if list(answer[0].keys()) != COLUMNS:
        fail(
            "колонки charts.csv: ожидались "
            f"{','.join(COLUMNS)}, получены {','.join(answer[0].keys())}"
        )
        return
    if len(answer) != len(reference):
        fail(f"строк в charts.csv: ожидалось {len(reference)}, получено {len(answer)}")
        return

    expected = {row["id"]: row for row in reference}
    matched = 0
    for row in answer:
        rid = row["id"].strip()
        if rid not in expected:
            fail(f"неизвестный id {rid!r}: ожидались {', '.join(sorted(expected))}")
            continue

        form = normalise(row["форма"])
        for bad in FORBIDDEN:
            if bad in form:
                fail(f"{rid}: форма {row['форма']!r} входит в список запрещённых")
                break

        if form == normalise(expected[rid]["форма"]):
            matched += 1
        else:
            print(
                f"       {rid}: выбрана {row['форма']!r}, "
                f"эталон — {expected[rid]['форма']!r}"
            )

        for column in ("ось_x", "ось_y", "единицы"):
            if not row[column].strip():
                fail(f"{rid}: колонка {column} пуста")
        if len(row["почему"].split()) < MIN_REASON_WORDS:
            fail(
                f"{rid}: причина выбора формы короче {MIN_REASON_WORDS} слов "
                f"({row['почему']!r})"
            )

    if matched >= MIN_MATCH:
        ok(f"форма совпала с эталоном в {matched} случаях из {len(reference)}")
    else:
        fail(
            f"форма совпала с эталоном в {matched} случаях из {len(reference)}, "
            f"порог — {MIN_MATCH}"
        )


def check_numbers(name: str, work_name: str) -> None:
    reference = read_csv(HERE / name)
    answer = read_csv(WORK / work_name)
    if reference is None or answer is None:
        return
    if len(answer) != len(reference):
        fail(f"{work_name}: строк {len(answer)}, эталон — {len(reference)}")
        return
    mismatched = 0
    for index, (got, want) in enumerate(zip(answer, reference), start=2):
        if list(got.values()) != list(want.values()):
            mismatched += 1
            if mismatched <= 3:
                print(f"       {work_name}, строка {index}: {got} против {want}")
    if mismatched:
        fail(f"{work_name}: расходится строк {mismatched} из {len(reference)}")
    else:
        ok(f"{work_name}: {len(reference)} строк совпадают с эталоном")


def check_images() -> None:
    missing = []
    small = []
    for index in range(1, 7):
        path = WORK / f"chart_q{index}.png"
        if not path.exists():
            missing.append(path.name)
        elif path.stat().st_size < MIN_PNG_BYTES:
            small.append(f"{path.name} ({path.stat().st_size} байт)")
    if missing:
        fail("нет картинок: " + ", ".join(missing))
    if small:
        fail("картинки меньше 5 КБ (пустой экспорт): " + ", ".join(small))
    if not missing and not small:
        ok("шесть картинок chart_q1.png … chart_q6.png на месте")


def main() -> int:
    check_choices()
    check_numbers("ref_chart_quarter.csv", "chart_quarter.csv")
    check_numbers("ref_chart_channel_share.csv", "chart_channel_share.csv")
    check_images()
    print()
    if failures:
        print(f"НЕ СОШЛОСЬ: {len(failures)} проверок из 5 групп")
        return 1
    print("СОВПАДАЕТ: шаг M2.09 сдан")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
