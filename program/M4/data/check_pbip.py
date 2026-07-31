"""Проверка сохранённого проекта Power BI (.pbip) по критериям шагов M4.

Запуск:

    python check_pbip.py <папка проекта> --step 01

Папка проекта — та, в которую Power BI Desktop сохранил `.pbip`
(в программе это `program\\M4\\pbi`). Скрипт только читает файлы: ничего
не правит, ничего не запускает, Power BI Desktop ему не нужен.

Зачем скрипт, а не осмотр интерфейса. Всё, что проверяется ниже, живёт в
тексте проекта — решение 22 `design/decisions.md` (слои 0, 2, 3). Осмотр
интерфейса тот же факт даёт мягче: гейт измерил случай, где GUI показывал
«Многие к одному» и «Простое», а в `relationships.tmdl` не было ни одной
из этих строк, потому что TMDL пишет только отклонения от умолчаний
(`research/tools-gate.md`, 2.9). Отсюда правило, на котором построены
проверки: **свойство при значении по умолчанию отсутствует**, и критерий
формулируется как утверждение об отсутствии строки, а не о её наличии.

Пути ищутся по маскам, а не по фиксированным именам: имя проекта задаёт
автор, а внутренняя структура (`<имя>.SemanticModel`, `<имя>.Report`)
измерена на проекте гейта (`research/tools-gate.md`, 2.8) и подтверждена
документацией
[Power BI Desktop project report folder](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report).

Ограничение, названное вслух: скрипт прогонялся на макете структуры
проекта, собранном из измерений гейта, а не на проекте, сохранённом Power
BI Desktop. Первый настоящий прогон делает автор на своём проекте; если
маска не сойдётся с реальным именем папки, правится маска, а не критерий
шага.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

FAILED: list[str] = []


def ok(msg: str) -> None:
    print(f"[OK]   {msg}")


def bad(msg: str) -> None:
    FAILED.append(msg)
    print(f"[FAIL] {msg}")


def read(path: Path) -> str:
    # Кодировка названа явно (решение 17). Desktop пишет TMDL в UTF-8;
    # utf-8-sig снимает BOM, если он вдруг есть, и не мешает, если нет.
    return path.read_text(encoding="utf-8-sig")


def semantic_dir(project: Path) -> Path | None:
    found = sorted(project.glob("*.SemanticModel/definition"))
    return found[0] if found else None


def report_dir(project: Path) -> Path | None:
    found = sorted(project.glob("*.Report"))
    return found[0] if found else None


def table_files(project: Path) -> list[Path]:
    sem = semantic_dir(project)
    return sorted(sem.glob("tables/*.tmdl")) if sem else []


def visual_files(project: Path) -> list[Path]:
    rep = report_dir(project)
    return sorted(rep.glob("definition/pages/*/visuals/*/visual.json")) if rep else []


def check_step01(project: Path) -> None:
    """Три preview-функции включены — доказывается файлами на диске."""
    pbip = sorted(project.glob("*.pbip"))
    if pbip:
        ok(f"PBIP: файл проекта {pbip[0].name} на месте")
    else:
        bad("PBIP: в папке нет ни одного файла *.pbip — проект сохранён не как Power BI Project")

    tables = table_files(project)
    sem = semantic_dir(project)
    if sem is None:
        bad("TMDL: не найдена папка *.SemanticModel/definition")
    else:
        tmdl = sorted(sem.rglob("*.tmdl"))
        if tmdl:
            ok(f"TMDL: {len(tmdl)} файлов .tmdl в семантической модели")
        else:
            bad("TMDL: в *.SemanticModel/definition нет ни одного .tmdl — формат TMDL выключен")

    rep = report_dir(project)
    if rep is None:
        bad("PBIR: не найдена папка *.Report")
    else:
        if (rep / "definition").is_dir():
            ok("PBIR: папка *.Report/definition на месте")
        else:
            bad("PBIR: нет папки *.Report/definition — отчёт сохранён в формате PBIR-Legacy")
        if (rep / "report.json").exists():
            bad("PBIR: в корне *.Report лежит report.json — это PBIR-Legacy, а не PBIR")
        else:
            ok("PBIR: report.json в корне *.Report отсутствует, как и должно быть")

    visuals = visual_files(project)
    if visuals:
        types = [v for v in visuals if '"visualType"' in read(v)]
        ok(f"PBIR: визуалов на диске {len(visuals)}, из них с visualType {len(types)}")
    else:
        bad("PBIR: не найдено ни одного visual.json — на странице нет визуалов "
            "или PBIR выключен")

    gitignore = project / ".gitignore"
    if gitignore.exists():
        body = read(gitignore)
        missing = [s for s in ("localSettings.json", "cache.abf") if s not in body]
        if missing:
            bad(f".gitignore проекта не покрывает: {', '.join(missing)}")
        else:
            ok(".gitignore проекта выводит из-под версионирования localSettings.json и cache.abf")
    else:
        bad(".gitignore в папке проекта не найден — его создаёт сам Power BI Desktop")

    if tables:
        ok(f"таблиц в модели: {len(tables)}")


EXPECTED_TABLES = {"transactions", "merchants", "mcc_categories", "merchant_plan", "calendar"}
M_CODE_REQUIRED = ("Encoding = 65001", "QuoteStyle = QuoteStyle.Csv", '"en-US"')
EXPECTED_TYPES = {
    "transactions": {"amount_uah": "double", "period_ym": "string"},
    "merchant_plan": {"commission_pct": "double", "period_ym": "string"},
}


def check_step02(project: Path) -> None:
    """Слой 0 решения 22: M-код задан явно, типы не оставлены автоопределению."""
    tables = table_files(project)
    names = {p.stem for p in tables}
    missing = EXPECTED_TABLES - names
    if missing:
        bad(f"в модели нет таблиц: {', '.join(sorted(missing))}")
    else:
        ok(f"пять таблиц модуля на месте: {', '.join(sorted(EXPECTED_TABLES))}")

    for path in tables:
        if path.stem not in EXPECTED_TABLES:
            continue
        body = read(path)
        absent = [s for s in M_CODE_REQUIRED if s not in body]
        if absent:
            bad(f"{path.stem}.tmdl: в M-коде нет {', '.join(absent)}")
        else:
            ok(f"{path.stem}.tmdl: кодировка, QuoteStyle и культура заданы явно")

        for column, want in EXPECTED_TYPES.get(path.stem, {}).items():
            block = body.split(f"column {column}")
            if len(block) < 2:
                bad(f"{path.stem}.tmdl: колонки {column} нет")
                continue
            head = block[1][:400]
            if f"dataType: {want}" in head:
                ok(f"{path.stem}.{column}: тип {want}")
            else:
                bad(f"{path.stem}.{column}: ожидался dataType: {want}, в файле его нет "
                    f"(типичная причина — культура по умолчанию, находка P7 гейта)")


DEFAULTS_MUST_BE_ABSENT = ("crossFilteringBehavior:", "fromCardinality:", "toCardinality:")


def check_step03(project: Path) -> None:
    """Связи. Проверка через отсутствие строки (решение 22, слой 2)."""
    sem = semantic_dir(project)
    path = sem / "relationships.tmdl" if sem else None
    if path is None or not path.exists():
        bad("relationships.tmdl не найден — в модели нет ни одной связи")
        return
    body = read(path)

    blocks = [b for b in body.split("relationship ") if b.strip()]
    if len(blocks) == 5:
        ok("связей в модели: 5")
    else:
        bad(f"связей в модели: {len(blocks)}, ожидалось 5")

    auto = sum(1 for b in blocks if b.startswith("AutoDetected"))
    if len(blocks) - auto >= 4:
        ok(f"связей, созданных вручную: {len(blocks) - auto} (автоопределением: {auto})")
    else:
        bad(f"связей, созданных вручную: {len(blocks) - auto}, ожидалось не менее 4 — "
            f"три случая ограничения C1 автоопределением не строятся")

    inactive = body.count("isActive: false")
    if inactive == 1:
        ok("ровно одна связь неактивна (вторая колонка-кандидат по дате)")
    else:
        bad(f"строк 'isActive: false' в файле: {inactive}, ожидалась ровно одна")

    present = [s for s in DEFAULTS_MUST_BE_ABSENT if s in body]
    if present:
        bad(f"в relationships.tmdl есть строки {', '.join(present)} — это отклонение от "
            f"умолчаний: кардинальность не «многие к одному» либо фильтрация двусторонняя")
    else:
        ok("отклонений от умолчаний нет: кардинальность *:1, фильтрация односторонняя, "
           "связи активны (кроме одной явно неактивной)")

    for want in ("transactions.plan_key", "merchant_plan.plan_key"):
        if want in body:
            ok(f"составной ключ: связь использует {want}")
        else:
            bad(f"составной ключ: в relationships.tmdl нет {want}")


EXPECTED_MEASURES = {
    "Total Amount": ("SUM(",),
    "Settled Amount": ("CALCULATE(",),
    "Tx Count": ("COUNTROWS(",),
    "Decline Rate": ("DIVIDE(",),
    "Commission": ("SUMX(", "RELATED("),
    "Settled YTD": ("TOTALYTD(",),
}


def check_step04(project: Path) -> None:
    """Шесть мер DAX и три визуала."""
    body = "\n".join(read(p) for p in table_files(project))
    for name, fragments in EXPECTED_MEASURES.items():
        marker = f"measure '{name}'" if " " in name else f"measure {name}"
        if marker not in body and f"measure '{name}'" not in body:
            bad(f"меры {name} в модели нет")
            continue
        chunk = body.split(marker, 1)[1][:600]
        absent = [f for f in fragments if f not in chunk]
        if absent:
            bad(f"мера {name}: в выражении нет {', '.join(absent)}")
        else:
            ok(f"мера {name}: выражение содержит {', '.join(fragments)}")

    visuals = visual_files(project)
    banned = ("pieChart", "donutChart", "ribbonChart")
    types: list[str] = []
    for v in visuals:
        text = read(v)
        for token in banned:
            if token in text:
                bad(f"{v.parent.name}: визуал типа {token} — слой 3 решения 22 его запрещает")
        types.append(v.parent.name)
    if len(visuals) >= 3:
        ok(f"визуалов на диске: {len(visuals)}")
    else:
        bad(f"визуалов на диске: {len(visuals)}, ожидалось не менее 3")

    sorted_ones = sum(1 for v in visuals if "sortDefinition" in read(v))
    if sorted_ones >= 3:
        ok(f"визуалов с объявленной сортировкой: {sorted_ones}")
    else:
        bad(f"визуалов с объявленной сортировкой: {sorted_ones}, ожидалось не менее 3 — "
            f"порядок строк эталона проверяется по sortDefinition")


CHECKS = {"01": check_step01, "02": check_step02, "03": check_step03, "04": check_step04}


def main() -> int:
    parser = argparse.ArgumentParser(description="Проверка проекта .pbip по критериям шагов M4")
    parser.add_argument("project", help="папка, в которую сохранён .pbip")
    parser.add_argument("--step", required=True, choices=sorted(CHECKS),
                        help="номер шага M4, чьи критерии проверяются")
    args = parser.parse_args()

    project = Path(args.project)
    if not project.is_dir():
        print(f"[FAIL] папка проекта {project} не найдена")
        return 1

    print(f"Проект: {project.resolve()}  шаг: {args.step}\n")
    CHECKS[args.step](project)

    print()
    if FAILED:
        print(f"НЕ СОШЛОСЬ: {len(FAILED)} проверок. Шаг не закрыт.")
        return 1
    print("ВСЁ СОШЛОСЬ: расхождений 0.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
