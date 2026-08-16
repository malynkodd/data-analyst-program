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
import json
import sys
from pathlib import Path

if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent

# Сверка выгрузки с эталоном берётся из compare_csv.py, а не пишется
# заново: у учащегося и у критерия шага обязано быть одно правило разбора
# чисел, иначе «сошлось руками, не сошлось проверкой» становится штатной
# ситуацией.
sys.path.insert(0, str(HERE.parent.parent / "M3" / "data"))
import compare_csv  # noqa: E402

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


def check_gitignore(project: Path) -> None:
    """Покрыт ли локальный мусор проекта — своим `.gitignore` или любым
    родительским. Дефект R4: Power BI Desktop кладёт свой `.gitignore` в
    новую папку вне репозитория, но в папку внутри репозитория не положил
    ни разу из двух проб. Требовать файл именно в проекте — значит
    требовать того, чего инструмент не делает."""
    wanted = ("localSettings.json", "cache.abf")
    here = project.resolve()
    seen = []
    for folder_up in [here, *here.parents]:
        candidate = folder_up / ".gitignore"
        if not candidate.exists():
            continue
        seen.append(candidate)
        body = read(candidate)
        if ".pbi/" in body or all(s in body for s in wanted):
            where = "проекта" if folder_up == here else str(candidate)
            ok(f".pbi/ выведен из-под версионирования: .gitignore {where}")
            return
    if seen:
        bad(f"ни один из {len(seen)} найденных .gitignore не покрывает `.pbi/`: "
            f"нужна строка `**/.pbi/` либо обе — {', '.join(wanted)}")
    else:
        bad("ни одного .gitignore над проектом не найдено; Power BI Desktop свой "
            "кладёт не всегда (R4) — строка `**/.pbi/` пишется в корень репозитория")


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

    check_gitignore(project)

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

# Таблицы, которые заводит настройка «Автоматические дата и время». Их не
# видно ни в панели «Данные», ни на схеме, и учащийся их не создавал.
AUTO_DATE_PREFIXES = ("LocalDateTable_", "DateTableTemplate_")

# Пять связей шага — парами колонок, а не числом и не происхождением.
# Так проверка не зависит ни от настройки автодаты (R12, R30), ни от того,
# провёл ли учащийся связь руками или её предложило автоопределение
# (R21, R22): предметом критерия является модель, а не история кликов.
REQUIRED_LINKS = [
    ("transactions.merchant_id", "merchants.merchant_id"),
    ("transactions.mcc", "mcc_categories.code"),
    ("transactions.tx_date", "calendar.date_key"),
    ("transactions.settled_date", "calendar.date_key"),
    ("transactions.plan_key", "merchant_plan.plan_key"),
]
INACTIVE_LINK = ("transactions.settled_date", "calendar.date_key")


def parse_relationships(body: str) -> list[dict]:
    """relationships.tmdl → список связей с колонками и активностью."""
    blocks: list[dict] = []
    current: dict | None = None
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("relationship "):
            current = {"name": stripped[len("relationship "):].strip(),
                       "from": "", "to": "", "active": True}
            blocks.append(current)
        elif current is None:
            continue
        elif stripped.startswith("fromColumn:"):
            current["from"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("toColumn:"):
            current["to"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("isActive:"):
            current["active"] = stripped.split(":", 1)[1].strip() != "false"
    return blocks


def is_auto_date(link: dict) -> bool:
    return any(side.startswith(AUTO_DATE_PREFIXES)
               for side in (link["from"], link["to"]))


def check_step03(project: Path) -> None:
    """Связи. Проверяются видимые учащемуся связи, поимённо по колонкам.

    Скрытые связи автодаты печатаются справочной строкой и ни на один
    порог не влияют: порог, зависящий от настройки, которую учащийся не
    трогал, непроходим на настройках по умолчанию и проходим после
    действия из следующего шага (дефекты R12, R29, R30 —
    `research/tools-gate.md`, 3.3)."""
    sem = semantic_dir(project)
    path = sem / "relationships.tmdl" if sem else None
    if path is None or not path.exists():
        bad("relationships.tmdl не найден — в модели нет ни одной связи")
        return
    body = read(path)

    links = parse_relationships(body)
    hidden = [l for l in links if is_auto_date(l)]
    visible = [l for l in links if not is_auto_date(l)]

    if hidden:
        print(f"       справочно: скрытых связей автодаты {len(hidden)} — "
              f"на критерий не влияют, в панели «Данные» их не видно")

    if len(visible) == 5:
        ok("видимых связей в модели: 5")
    else:
        bad(f"видимых связей в модели: {len(visible)}, ожидалось 5")

    pairs = [(l["from"], l["to"]) for l in visible]
    for want in REQUIRED_LINKS:
        if want in pairs:
            ok(f"связь на месте: {want[0]} → {want[1]}")
        else:
            bad(f"связи {want[0]} → {want[1]} в модели нет")

    inactive = [l for l in visible if not l["active"]]
    if len(inactive) != 1:
        bad(f"неактивных видимых связей: {len(inactive)}, ожидалась ровно одна "
            f"(вторая колонка-кандидат по дате)")
    elif (inactive[0]["from"], inactive[0]["to"]) != INACTIVE_LINK:
        bad(f"неактивна связь {inactive[0]['from']} → {inactive[0]['to']}, "
            f"а должна быть {INACTIVE_LINK[0]} → {INACTIVE_LINK[1]}: "
            f"активной обязана остаться связь по дате операции")
    else:
        ok("неактивна ровно одна связь, и это связь по дате расчёта")

    deviating = [l for l in visible
                 if any(s in body.split("relationship " + l["name"], 1)[-1].split("relationship ")[0]
                        for s in DEFAULTS_MUST_BE_ABSENT)]
    if deviating:
        bad(f"у видимых связей есть отклонения от умолчаний "
            f"({', '.join(l['name'] for l in deviating)}): кардинальность не «многие "
            f"к одному» либо фильтрация двусторонняя")
    else:
        ok("отклонений от умолчаний нет: кардинальность *:1, фильтрация односторонняя")


EXPECTED_MEASURES = {
    "Total Amount": ("SUM(",),
    "Settled Amount": ("CALCULATE(",),
    "Tx Count": ("COUNTROWS(",),
    "Decline Rate": ("DIVIDE(",),
    "Commission": ("SUMX(", "RELATED("),
    "Settled YTD": ("TOTALYTD(",),
}


# Визуалы шага — поимённо, по составу полей. Порог «визуалов не меньше
# трёх» засчитывал визуалы предыдущего шага и печатал код 0 на модели, где
# из восьми заданий сделаны два (дефект R32, `research/tools-gate.md`).
# Существование файла — не выполнение задания.
REQUIRED_VISUALS = {
    "визуал 1 (категории)": (
        {"mcc_categories.category_name"},
        {"Total Amount", "Settled Amount", "Tx Count", "Decline Rate"},
    ),
    "визуал 2 (месяцы)": (
        {"calendar.year", "calendar.month_no"},
        {"Settled Amount", "Settled YTD"},
    ),
    "визуал 3 (тарифы)": (
        {"merchant_plan.plan_code"},
        {"Commission"},
    ),
    "визуал итогов": (
        set(),
        {"Total Amount", "Settled Amount", "Tx Count", "Decline Rate", "Commission", "Settled YTD"},
    ),
}

# Экспорт — единственная опора критерия на число. Карточка округляет до
# трёх значащих и переопределяет формат меры (R33), поэтому «сходится до
# второго знака» проверяется файлом, а не экраном.
EXPECTED_EXPORTS = {
    "export_by_category.csv": "ref_by_category.csv",
    "export_month_ytd.csv": "ref_month_ytd.csv",
    "export_plan_commission.csv": "ref_plan_commission.csv",
    "export_totals.csv": "ref_totals.csv",
}


def visual_fields(path: Path) -> tuple[set[str], set[str], str]:
    """visual.json → (колонки как 'таблица.поле', имена мер, тип визуала)."""
    try:
        data = json.loads(read(path))
    except json.JSONDecodeError:
        return set(), set(), ""
    visual = data.get("visual", {})
    columns: set[str] = set()
    measures: set[str] = set()
    state = visual.get("query", {}).get("queryState", {})
    for well in state.values():
        for projection in well.get("projections", []):
            field = projection.get("field", {})
            for kind, bucket in (("Column", columns), ("Measure", measures)):
                if kind not in field:
                    continue
                prop = field[kind].get("Property", "")
                entity = field[kind].get("Expression", {}).get("SourceRef", {}).get("Entity", "")
                # мера опознаётся по имени: учащийся вправе писать меры на
                # любой таблице, и таблица-хозяин к критерию отношения не имеет
                bucket.add(prop if kind == "Measure" else f"{entity}.{prop}")
    return columns, measures, visual.get("visualType", "")


def check_step04(project: Path, exports: Path) -> None:
    """Шесть мер, четыре визуала поимённо и четыре сверки экспорта."""
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
    parsed = []
    for v in visuals:
        text = read(v)
        for token in banned:
            if token in text:
                bad(f"{v.parent.name}: визуал типа {token} — слой 3 решения 22 его запрещает")
        parsed.append((v, *visual_fields(v)))

    found: dict[str, Path] = {}
    for label, (want_cols, want_measures) in REQUIRED_VISUALS.items():
        hit = None
        for path, cols, measures, _vt in parsed:
            if want_cols <= cols and want_measures <= measures:
                # визуал итогов не должен нести разрезов: иначе под него
                # подойдёт любая из трёх таблиц с полным набором мер
                if not want_cols and cols:
                    continue
                hit = path
                break
        if hit is not None:
            found[label] = hit
            ok(f"{label}: собран, поля на месте")
        else:
            need = ", ".join(sorted(want_cols | want_measures))
            bad(f"{label}: на странице нет визуала с полями {need}")

    # Раскладку визуалов по страницам скрипт не проверяет намеренно (R35,
    # статус «не чинится»): перекрёстную фильтрацию ловит сверка четырёх
    # выгрузок с эталонами — отфильтрованный визуал даёт [FAIL] на числах.
    # Отдельная страница остаётся требованием текста, задание 3.

    if not exports.is_dir():
        bad(f"папки выгрузок {exports} нет — задания 5–6 не выполнены: "
            f"экспорт визуала и есть артефакт этого шага")
        return

    for name, ref_name in EXPECTED_EXPORTS.items():
        got, want = exports / name, HERE / ref_name
        if not got.exists():
            bad(f"выгрузки {name} нет в {exports} — визуал не экспортирован")
            continue
        if not want.exists():
            bad(f"эталона {ref_name} нет — соберите его: python reference_m4.py")
            continue
        problem = compare_export(got, want)
        if problem:
            bad(f"{name}: {problem}")
        else:
            ok(f"{name}: сходится с {ref_name}, расхождение 0")


def compare_export(got: Path, want: Path) -> str:
    """Сверка выгрузки с эталоном по правилам compare_csv.py.

    Одна реализация на две точки входа: учащийся смотрит расхождение
    подробным выводом `compare_csv.py`, критерий шага получает ту же
    сверку одной строкой."""
    mine, ref = compare_csv.read_csv(got), compare_csv.read_csv(want)
    if not mine:
        return "файл пуст"
    if mine[0] != ref[0]:
        return (f"заголовок не совпал: у вас {','.join(mine[0])}, "
                f"эталон {','.join(ref[0])}")
    if len(mine) - 1 != len(ref) - 1:
        return f"строк {len(mine) - 1}, в эталоне {len(ref) - 1}"
    for i, (got_row, want_row) in enumerate(zip(mine[1:], ref[1:]), start=1):
        for j, (a, b) in enumerate(zip(got_row, want_row)):
            if not compare_csv.same_value(a, b):
                col = mine[0][j] if j < len(mine[0]) else f"колонка {j + 1}"
                return f"строка {i}, колонка '{col}': у вас {a!r}, в эталоне {b!r}"
    return ""


PARAMETER_NAME = "DataFolder"

# Литеральный путь к папке данных в M-коде — ровно то, что параметр
# заменяет. Ищутся обе папки: оставшийся `csv\` означает незаконченный
# перевод запроса, оставшийся `csv_next\` — подмену правкой запроса, а не
# значения параметра. И то и другое — «ручная правка», которой критерий C2
# считает ноль.
LITERAL_FOLDERS = ("data\\csv\\", "data\\csv_next\\")

EXPECTED_NEXT_EXPORTS = {
    "export_next_by_category.csv": "ref_next_by_category.csv",
    "export_next_by_city.csv": "ref_next_by_city.csv",
    "export_next_totals.csv": "ref_next_totals.csv",
}


def check_step05(project: Path, exports: Path) -> None:
    """Умение C2: подмена источника — сменой значения параметра, а не
    правкой пяти запросов; доказательство — файл, а не отсутствие ошибок.

    Первое условие критерия C2 («0 ошибок при Refresh») здесь не
    проверяется намеренно: решение 22 отменило его как самостоятельное —
    прогон дал 0 ошибок на молча испорченной кодировке."""
    sem = semantic_dir(project)
    tmdl = sorted(sem.rglob("*.tmdl")) if sem else []
    tables = [p for p in table_files(project) if p.stem in EXPECTED_TABLES]

    # Параметр ищется по всем .tmdl модели, кроме файлов таблиц: в какой
    # именно файл Desktop кладёт выражения, прогоном не измерено, и
    # завязываться на имя файла — значит проверять догадку.
    defined = [p for p in tmdl if p not in set(table_files(project))
               and PARAMETER_NAME in read(p)]
    if defined:
        ok(f"параметр {PARAMETER_NAME} заведён в модели: {defined[0].name}")
    else:
        bad(f"параметра {PARAMETER_NAME} в модели нет — искали во всех *.tmdl, "
            f"кроме файлов таблиц (задание 3)")

    if len(tables) != len(EXPECTED_TABLES):
        bad(f"таблиц модуля в модели {len(tables)}, а должно быть {len(EXPECTED_TABLES)}")

    for path in tables:
        body = read(path)
        literal = [f for f in LITERAL_FOLDERS if f.lower() in body.lower()]
        if literal:
            bad(f"{path.stem}.tmdl: путь к папке записан в запросе литералом "
                f"({literal[0]}) — источник подменяется значением параметра, "
                f"а не правкой запроса")
        elif PARAMETER_NAME not in body:
            bad(f"{path.stem}.tmdl: запрос не читает файл через {PARAMETER_NAME}")
        else:
            ok(f"{path.stem}.tmdl: источник берётся через {PARAMETER_NAME}, "
               f"литерального пути к папке нет")

    absent = sorted({s for p in tables for s in M_CODE_REQUIRED if s not in read(p)})
    if absent:
        bad(f"перевод на параметр задел разбор файла: в M-коде пропало "
            f"{', '.join(absent)} (четвёртое условие C2)")
    else:
        ok(f"разбор файла не задет: Encoding, QuoteStyle и культура на месте "
           f"во всех {len(tables)} запросах")

    if not exports.is_dir():
        bad(f"папки выгрузок {exports} нет — задание 8 не выполнено")
        return
    for name, ref_name in EXPECTED_NEXT_EXPORTS.items():
        got, want = exports / name, HERE / ref_name
        if not want.exists():
            bad(f"эталона {ref_name} нет — не запущен reference_m4.py --next (задание 2)")
            continue
        if not got.exists():
            bad(f"выгрузки {name} нет в {exports} — визуал не экспортирован")
            continue
        diff = compare_export(got, want)
        if diff:
            bad(f"{name}: не сходится с {ref_name} — {diff}")
        else:
            ok(f"{name}: сходится с {ref_name}, расхождение 0")


CHECKS = {"01": check_step01, "02": check_step02, "03": check_step03,
          "04": check_step04, "05": check_step05}


def main() -> int:
    parser = argparse.ArgumentParser(description="Проверка проекта .pbip по критериям шагов M4")
    parser.add_argument("project", help="папка, в которую сохранён .pbip")
    parser.add_argument("--step", required=True, choices=sorted(CHECKS),
                        help="номер шага M4, чьи критерии проверяются")
    parser.add_argument("--exports", default=None,
                        help="папка с выгрузками визуалов (шаг 04); "
                             "по умолчанию <папка проекта>\\export")
    args = parser.parse_args()

    project = Path(args.project)
    if not project.is_dir():
        print(f"[FAIL] папка проекта {project} не найдена")
        return 1

    exports = Path(args.exports) if args.exports else project / "export"
    print(f"Проект: {project.resolve()}  шаг: {args.step}\n")
    if args.step in ("04", "05"):
        CHECKS[args.step](project, exports)
    else:
        CHECKS[args.step](project)

    print()
    if FAILED:
        print(f"НЕ СОШЛОСЬ: {len(FAILED)} проверок. Шаг не закрыт.")
        return 1
    print("ВСЁ СОШЛОСЬ: расхождений 0.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
