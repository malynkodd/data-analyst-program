"""Проверки согласованности между CLAUDE.md, design/blueprint.md и program/.

Запуск: python tools/check_consistency.py
Код возврата: 0, если все проверки прошли; 1, если найдена хотя бы одна
проблема. Ничего не изменяет в репозитории, только читает и печатает отчёт.
"""

from __future__ import annotations

import csv
import fnmatch
import re
import sqlite3
import sys
from pathlib import Path

if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
BLUEPRINT = ROOT / "design" / "blueprint.md"
CLAUDE_MD = ROOT / "CLAUDE.md"
DECISIONS = ROOT / "design" / "decisions.md"
PROGRAM_DIR = ROOT / "program"

DASH = "\u2013"  # en dash, используется в диапазонах часов по всему репозиторию

FORBIDDEN_PHRASES = [
    "понимает", "знает основ", "умеет работать", "имеет представление",
    "освоил", "давайте", "попробуем", "не пугайтесь",
    "главное", "!",
]

# "разбирается" сам по себе — обычный русский глагол («здесь разбирается
# ошибка» = анализируется), запрещена только конструкция про читателя
# («разбирается в X» = невыполнимая формулировка «понимает X»).
FORBIDDEN_PATTERNS = [
    re.compile(r"разбирается\s+в\b", re.IGNORECASE),
]

# POSIX-специфичные инструменты, запрещённые решением 13 (design/decisions.md)
# внутри команд, которые шаг даёт учащемуся. \b границы слов, чтобы не
# зацепить случайные подстроки внутри других слов.
POSIX_COMMAND_PATTERNS = [
    re.compile(r"\bgrep\b"),
    re.compile(r"\bawk\b"),
    re.compile(r"\bsed\b"),
    re.compile(r"stat --format"),
    re.compile(r"\bwc\s+-l\b"),
]

FAILED = False


def fail(msg: str) -> None:
    global FAILED
    FAILED = True
    print(f"[FAIL] {msg}")


def ok(msg: str) -> None:
    print(f"[OK]   {msg}")


def parse_range(text: str) -> tuple[int, int] | None:
    """'7–9' -> (7, 9); '8' -> (8, 8); нечисловое -> None."""
    text = text.strip()
    m = re.fullmatch(rf"(\d+){DASH}(\d+)", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.fullmatch(r"\d+", text)
    if m:
        return int(text), int(text)
    return None


def section(text: str, start_heading: str, end_heading: str | None) -> str:
    start = text.index(start_heading)
    if end_heading:
        end = text.index(end_heading, start + len(start_heading))
    else:
        end = len(text)
    return text[start:end]


def check_hours(blueprint_text: str, claude_text: str) -> None:
    part61 = section(blueprint_text, "## 6.1.", "## 6.2.")
    rows = [
        line for line in part61.splitlines()
        if line.startswith("|") and not re.match(r"^\|[\s:\-|]+\|?$", line)
    ]
    total_low = total_high = 0
    parsed_rows = 0
    for row in rows[1:]:  # первая строка — заголовок таблицы
        cells = [c.strip() for c in row.strip("|").split("|")]
        if len(cells) < 2:
            continue
        rng = parse_range(cells[1])
        if rng is None:
            continue
        total_low += rng[0]
        total_high += rng[1]
        parsed_rows += 1

    if parsed_rows == 0:
        fail("6.1: не удалось распарсить ни одной строки таблицы часов")
        return
    ok(f"6.1: распарсено {parsed_rows} строк, построчная сумма {total_low}{DASH}{total_high}")

    m = re.search(rf"Обучение: (\d+){DASH}(\d+) ч", claude_text)
    if not m:
        fail("CLAUDE.md: не найдена строка 'Обучение: N–M ч'")
    else:
        claude_low, claude_high = int(m.group(1)), int(m.group(2))
        if (claude_low, claude_high) == (total_low, total_high):
            ok(f"CLAUDE.md: {claude_low}{DASH}{claude_high} совпадает с частью 6.1")
        else:
            fail(
                f"CLAUDE.md заявляет {claude_low}{DASH}{claude_high}, "
                f"а часть 6.1 blueprint суммируется в {total_low}{DASH}{total_high}"
            )

    part62 = section(blueprint_text, "## 6.2.", "## 6.3.")
    m = re.search(rf"\*\*Итого\*\* \| \| \*\*(\d+){DASH}(\d+)\*\*", part62)
    if not m:
        fail("6.2: не найдена строка 'Итого' в таблице этапов")
    else:
        it_low, it_high = int(m.group(1)), int(m.group(2))
        if (it_low, it_high) == (total_low, total_high):
            ok(f"6.2 Итого: {it_low}{DASH}{it_high} совпадает с частью 6.1")
        else:
            fail(
                f"6.2 Итого заявляет {it_low}{DASH}{it_high}, "
                f"а часть 6.1 blueprint суммируется в {total_low}{DASH}{total_high}"
            )


SECTION_HEADING = re.compile(r"^## ([A-Z])\. (.+)$", re.MULTILINE)
ID_ROW = re.compile(r"^\| ([A-Z]\d+) \|", re.MULTILINE)
DECLARED_TOTAL = re.compile(r"\*\*Итого: (\d+) умений")
SKILL_HEADER = re.compile(r"^Умение: ([A-Z]\d+)", re.MULTILINE)


def check_skill_ids(blueprint_text: str) -> None:
    """Число умений и деление на "рыночные" (топ-15) и "вне топ-15" секции —
    берётся не из захардкоженного списка букв, а из самого текста части 1:
    заголовок секции содержит "вне топ-15" ровно тогда, когда её ID не входят
    в заявленный итог. Ошибка того же класса, что и с часами: число посчитано
    один раз руками и разошлось с построчной суммой при правках."""
    part1 = section(blueprint_text, "# ЧАСТЬ 1.", "# ЧАСТЬ 2.")

    headings = list(SECTION_HEADING.finditer(part1))
    if not headings:
        fail("часть 1 blueprint: не найдено ни одной секции '## X. ...'")
        return

    in_scope_ids: list[str] = []
    out_of_scope_ids: list[str] = []
    for idx, h in enumerate(headings):
        body_start = h.end()
        body_end = headings[idx + 1].start() if idx + 1 < len(headings) else len(part1)
        body = part1[body_start:body_end]
        ids_here = ID_ROW.findall(body)
        if "вне топ-15" in h.group(2):
            out_of_scope_ids.extend(ids_here)
        else:
            in_scope_ids.extend(ids_here)

    all_ids = sorted(set(in_scope_ids) | set(out_of_scope_ids))
    if not all_ids:
        fail("часть 1 blueprint: не найдено ни одного ID умения внутри секций")
        return

    m = DECLARED_TOTAL.search(part1)
    if not m:
        fail("часть 1: не найдена строка '**Итого: N умений.**'")
    else:
        declared = int(m.group(1))
        actual = len(set(in_scope_ids))
        if declared == actual:
            ok(
                f"часть 1: заявлено {declared} умений, построчный подсчёт по "
                f"секциям без пометки 'вне топ-15' совпадает"
            )
        else:
            fail(
                f"часть 1 заявляет 'Итого: {declared} умений', а построчный "
                f"подсчёт по секциям без пометки 'вне топ-15' даёт {actual} "
                f"(секции 'вне топ-15' дают ещё {len(set(out_of_scope_ids))}: "
                f"{', '.join(sorted(set(out_of_scope_ids)))})"
            )

    ok(
        f"часть 1: всего {len(all_ids)} ID умений во всех секциях "
        f"({all_ids[0]}..{all_ids[-1]}), включая 'вне топ-15'"
    )

    if not PROGRAM_DIR.exists():
        fail("program/ не существует — покрытие умений проверить нечем")
        return

    step_files = list(PROGRAM_DIR.rglob("*.md"))
    header_ids: set[str] = set()
    for f in step_files:
        header_ids.update(SKILL_HEADER.findall(f.read_text(encoding="utf-8")))

    # Считаются только ID из шапки "Умение: <ID>" каждого шага, а не всё
    # тело файла — иначе адреса ячеек Excel (A1, B2, C3...) неотличимы от
    # ID умений и проверка покрытия перестаёт быть проверкой.
    missing = [i for i in all_ids if i not in header_ids]
    if missing:
        fail(f"умения без шапки 'Умение: <ID>' ни в одном шаге program/**/*.md: {', '.join(missing)}")
    else:
        ok(f"все {len(all_ids)} умений закрыты шапкой 'Умение:' хотя бы одного шага program/")


def check_step00(blueprint_text: str) -> None:
    if not PROGRAM_DIR.exists():
        return
    module_dirs = sorted(
        p for p in PROGRAM_DIR.iterdir() if p.is_dir() and re.fullmatch(r"M\d+", p.name)
    )
    if not module_dirs:
        ok("program/: ни один модуль ещё не начат — проверка step-00.md пропущена")
        return
    missing = [d.name for d in module_dirs if not (d / "step-00.md").exists()]
    if missing:
        fail(f"модули без step-00.md: {', '.join(missing)}")
    else:
        ok(f"все {len(module_dirs)} начатых модулей имеют step-00.md")


DECISION_HEADING = re.compile(r"^## (\d+)\. ", re.MULTILINE)


def check_decision_numbering() -> None:
    """Номера решений в design/decisions.md идут подряд, с 1, без пропусков
    и без повторов.

    Дешёвая страховка от уже случившегося: решение 18 (критерий A4) было
    реализовано в program/M3/step-08.md, но в decisions.md отсутствовало —
    файл шёл 15, 16, 17 и сразу «Что осталось нерешённым», и пропуск не
    был виден ниоткуда, потому что следующее решение просто получило бы
    номер 18 второй раз. Проверяются только заголовки уровня `## N.` —
    нумерованные списки внутри разделов (например, в «Что осталось
    нерешённым») под неё не попадают."""
    if not DECISIONS.exists():
        fail("design/decisions.md не найден")
        return

    text = DECISIONS.read_text(encoding="utf-8")
    numbers = [int(m) for m in DECISION_HEADING.findall(text)]
    if not numbers:
        fail("design/decisions.md: не найдено ни одного заголовка вида '## N. ...'")
        return

    duplicates = sorted({n for n in numbers if numbers.count(n) > 1})
    if duplicates:
        fail(
            f"design/decisions.md: номера решений повторяются: "
            f"{', '.join(str(n) for n in duplicates)}"
        )

    expected = list(range(1, len(numbers) + 1))
    if sorted(numbers) != expected:
        missing = [n for n in expected if n not in numbers]
        extra = [n for n in sorted(set(numbers)) if n > len(numbers)]
        parts = []
        if missing:
            parts.append(f"пропущены: {', '.join(str(n) for n in missing)}")
        if extra:
            parts.append(f"за пределами диапазона 1..{len(numbers)}: {', '.join(str(n) for n in extra)}")
        fail(
            f"design/decisions.md: {len(numbers)} решений, нумерация не сплошная "
            f"({'; '.join(parts) if parts else 'порядок номеров не 1..N'})"
        )
        return

    if numbers != expected:
        fail(
            f"design/decisions.md: номера решений идут не по возрастанию: "
            f"{', '.join(str(n) for n in numbers)}"
        )
        return

    if not duplicates:
        ok(f"design/decisions.md: {len(numbers)} решений, нумерация сплошная 1..{len(numbers)}")


DEFERRED = ROOT / "DEFERRED.md"
BACKTICKED = re.compile(r"`([^`]+)`")


def _looks_like_repo_path(token: str) -> bool:
    """Отличает путь от прочего инлайн-кода в той же колонке (`chcp 65001`,
    `core.autocrlf`): путь либо содержит `/`, либо имеет расширение файла
    репозитория."""
    return "/" in token or token.endswith((".md", ".py"))


def check_deferred_paths() -> None:
    """Каждая строка DEFERRED.md называет место в репозитории, и это место
    существует.

    Файл заведён решением 21 ради одного свойства: возврат отложенного
    должен быть проходом по списку, а не поиском по репозиторию. Свойство
    держится только на том, что колонка «Где заложено» указывает на живой
    файл. Строка без пути бесполезна сразу, строка с путём, который
    переименовали, — через несколько заходов и молча; сам файл это правило
    декларирует («Пустая колонка «Где заложено» — дефект строки»), но
    декларация без проверки живёт до первого захода, в котором про неё
    забудут (решение 20). Номера решений в той же колонке не проверяются —
    их сплошность закрывает check_decision_numbering()."""
    if not DEFERRED.exists():
        fail("DEFERRED.md не найден, хотя на него ссылаются CLAUDE.md и решение 21")
        return

    rows = [
        line for line in DEFERRED.read_text(encoding="utf-8").splitlines()
        if line.startswith("|") and not re.match(r"^\|[\s:\-|]+\|?$", line)
    ]
    checked_rows = checked_paths = 0
    broken = False
    for row in rows:
        cells = [c.strip() for c in row.strip("|").split("|")]
        if len(cells) < 2 or cells[1] == "Где заложено":  # заголовок таблицы
            continue
        checked_rows += 1
        label = cells[0][:60]
        paths = [t for t in BACKTICKED.findall(cells[1]) if _looks_like_repo_path(t)]
        if not paths:
            broken = True
            fail(f"DEFERRED.md: строка {label!r} не называет ни одного файла репозитория")
            continue
        for path in paths:
            checked_paths += 1
            if not (ROOT / path).exists():
                broken = True
                fail(f"DEFERRED.md: строка {label!r} ссылается на {path} — такого файла нет")

    if checked_rows == 0:
        fail("DEFERRED.md: не найдено ни одной строки таблицы отложенного")
    elif not broken:
        ok(f"DEFERRED.md: {checked_rows} строк отложенного, все {checked_paths} путей существуют")


README_CHECK_HEADING = "## Проверка строк"
TABLE_ROW = re.compile(r"^\|(.+)\|\s*$")
SQL_AFTER_SPEC = re.compile(r"^(\w+)\s+после\s+(.+)$")


def _parse_readme_check_rows(text: str) -> list[tuple[str, int]]:
    if README_CHECK_HEADING not in text:
        return []
    start = text.index(README_CHECK_HEADING)
    next_heading = text.find("\n## ", start + len(README_CHECK_HEADING))
    section_text = text[start:] if next_heading == -1 else text[start:next_heading]

    rows: list[tuple[str, int]] = []
    for line in section_text.splitlines():
        m = TABLE_ROW.match(line.strip())
        if not m:
            continue
        cells = [c.strip() for c in m.group(1).split("|")]
        if len(cells) != 2:
            continue
        spec, expected = cells
        if not re.fullmatch(r"\d+", expected):
            continue  # строка заголовка/разделителя таблицы, не данные
        rows.append((spec.strip("`"), int(expected)))
    return rows


def _count_csv_rows(path: Path) -> int:
    with path.open(encoding="utf-8", newline="") as f:
        return sum(1 for _ in csv.reader(f)) - 1  # минус заголовок


def _count_sql_table_rows(data_dir: Path, table: str, files: list[str]) -> int:
    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript((data_dir / "schema.sql").read_text(encoding="utf-8"))
        for fname in files:
            conn.executescript((data_dir / fname).read_text(encoding="utf-8"))
        cur = conn.execute(f"SELECT COUNT(*) FROM {table}")
        return cur.fetchone()[0]
    finally:
        conn.close()


def check_data_readme_counts() -> None:
    """Числа, заявленные в program/M*/data/README.md (раздел «Проверка
    строк»), сверяются с фактическими файлами — тот же класс ошибки, что
    рассогласование часов/умений: число один раз посчитано руками и
    разошлось с данными после правки (M3: «17 заказов» осталось в прозе
    после расширения датасета до 19 строк, найдено вручную одной сессией
    ревью, не автоматически — отсюда эта проверка)."""
    if not PROGRAM_DIR.exists():
        return
    readmes = sorted(PROGRAM_DIR.glob("M*/data/README.md"))
    if not readmes:
        ok("program/M*/data/README.md: файлов не найдено — проверка пропущена")
        return

    checked = 0
    for readme in readmes:
        data_dir = readme.parent
        rows = _parse_readme_check_rows(readme.read_text(encoding="utf-8"))
        for spec, expected in rows:
            checked += 1
            m = SQL_AFTER_SPEC.match(spec)
            try:
                if m:
                    table = m.group(1)
                    files = [f.strip().strip("`") for f in m.group(2).split(",")]
                    actual = _count_sql_table_rows(data_dir, table, files)
                    label = f"{readme.relative_to(ROOT)}: {spec}"
                elif spec.endswith(".csv"):
                    csv_path = data_dir / spec
                    if not csv_path.exists():
                        fail(f"{readme.relative_to(ROOT)}: файл {spec} из раздела «Проверка строк» не найден")
                        continue
                    actual = _count_csv_rows(csv_path)
                    label = f"{readme.relative_to(ROOT)}: {spec}"
                else:
                    fail(f"{readme.relative_to(ROOT)}: строка «{spec}» не распознана как .csv или '<таблица> после <файлы>'")
                    continue
            except Exception as exc:  # noqa: BLE001 — любая ошибка чтения/SQL — это FAIL проверки, не крах скрипта
                fail(f"{readme.relative_to(ROOT)}: не удалось проверить «{spec}»: {exc}")
                continue

            if actual != expected:
                fail(f"{label}: README заявляет {expected} строк, фактически {actual}")

    if checked:
        ok(f"program/M*/data/README.md: сверено {checked} строк из раздела «Проверка строк» во всех {len(readmes)} файлах")
    else:
        ok(f"program/M*/data/README.md: найдено {len(readmes)} файлов, ни один не содержит раздел «Проверка строк»")


LOAD_ORDER_HEADING = "## Порядок загрузки"
STEP_CELL = re.compile(r"^`?(step-(\d+)\.md)`?$")
REFERENCE_MARKER = re.compile(
    r"^Эталон:\s+`([^`]+\.csv)`\s+[—-]\s+`(step-\d+\.md)`\.?\s*$", re.MULTILINE
)
SQL_FENCE = re.compile(r"```sql\n(.*?)```", re.DOTALL)

# Что эта проверка заведомо НЕ покрывает. Печатается в [OK]-строке
# дословно: зелёный вывод без этого списка читается как полное покрытие
# эталонов модуля, хотя покрыта только их часть.
UNCOVERED = (
    "эталоны PostgreSQL (step-09..step-12 — нужен поднятый сервер, "
    "числа проверены вручную одним прогоном); activity_log (не "
    "коммитится, миллионы строк — сверяется через sha256 контрольной точки)"
)


def _parse_load_order(readme_text: str) -> dict[str, list[str]] | None:
    """Таблица «Порядок загрузки» из program/M*/data/README.md:
    `<шаг> | <что появляется> | <файлы>`. Возвращает {шаг: [.sql-файлы]}.
    Не-.sql в третьей колонке (генератор activity_log) отбрасывается — он
    создаёт таблицу сам, в накопительную сборку базы не входит."""
    if LOAD_ORDER_HEADING not in readme_text:
        return None
    start = readme_text.index(LOAD_ORDER_HEADING)
    next_heading = readme_text.find("\n## ", start + len(LOAD_ORDER_HEADING))
    body = readme_text[start:] if next_heading == -1 else readme_text[start:next_heading]

    order: dict[str, list[str]] = {}
    for line in body.splitlines():
        m = TABLE_ROW.match(line.strip())
        if not m:
            continue
        cells = [c.strip() for c in m.group(1).split("|")]
        if len(cells) != 3:
            continue
        step_m = STEP_CELL.match(cells[0])
        if not step_m:
            continue  # заголовок таблицы или разделитель
        files = [
            f.strip().strip("`") for f in cells[2].split(",")
            if f.strip().strip("`").endswith(".sql")
        ]
        order[step_m.group(1)] = files
    return order


def _step_number(step: str) -> int:
    return int(re.fullmatch(r"step-(\d+)\.md", step).group(1))


def _cumulative_sql_files(order: dict[str, list[str]], step: str) -> list[str]:
    """Файлы всех шагов с номером ≤ номера `step`, в порядке номеров шагов —
    то состояние базы, в котором учащийся окажется на этом шаге. Шага может
    не быть в таблице вовсе (шаг ничего не загружает, как step-06.md) — это
    нормальный случай, а не ошибка: он работает на состоянии предыдущих."""
    target = _step_number(step)
    files: list[str] = []
    for s in sorted(order, key=_step_number):
        if _step_number(s) <= target:
            files.extend(order[s])
    return files


def _parse_reference_markers(text: str) -> list[tuple[str, str, str]]:
    """Маркер `Эталон: <csv> — <шаг>.` привязывает эталонный CSV к первому
    следующему за ним блоку ```sql. Возвращает [(csv, шаг, запрос)]."""
    out: list[tuple[str, str, str]] = []
    for m in REFERENCE_MARKER.finditer(text):
        fence = SQL_FENCE.search(text, m.end())
        if fence is None:
            out.append((m.group(1), m.group(2), ""))
            continue
        out.append((m.group(1), m.group(2), fence.group(1)))
    return out


def _cell(value: object) -> str:
    return "" if value is None else str(value)


def check_reference_csv_state() -> None:
    """Эталонный CSV шага сверяется с результатом эталонного запроса,
    выполненного на том состоянии базы, которое будет у учащегося именно на
    этом шаге — накопительно по таблице «Порядок загрузки» из
    program/M*/data/README.md.

    Ловит ровно один класс дефекта: эталон посчитан на другом состоянии
    базы, чем то, до которого учащийся дойдёт по инструкциям шагов.
    Реальная находка: a1_task*.csv (13 строк) посчитаны до retention_seed.sql,
    а порядок загрузки в первой редакции step-00.md ставил retention_seed.sql
    в начало модуля — те же запросы дают 360 строк, и все 6 критериев A1
    провалились бы без единой ошибки учащегося.

    Не покрывает — см. UNCOVERED: PostgreSQL-эталоны (нет сервера),
    activity_log (не коммитится), эталоны, не выраженные SQL (M0/M1/M2 —
    вывод скриптов)."""
    if not PROGRAM_DIR.exists():
        return

    local_fails: list[str] = []

    def note(msg: str) -> None:
        """fail() плюс локальный счётчик: [OK]-строка этой проверки не должна
        печататься, когда часть пар не сошлась, а глобальный FAILED для этого
        не годится — он уже True из-за известного [FAIL] по непокрытым умениям."""
        local_fails.append(msg)
        fail(msg)

    data_dirs = sorted(PROGRAM_DIR.glob("M*/data"))
    checked = 0
    modules_with_markers: list[str] = []
    skipped_modules: list[str] = []

    for data_dir in data_dirs:
        module = data_dir.parent.name
        answers = data_dir / "reference_answers.md"
        markers = _parse_reference_markers(answers.read_text(encoding="utf-8")) if answers.exists() else []
        has_schema = (data_dir / "schema.sql").exists()

        if not markers:
            skipped_modules.append(module)
            if has_schema:
                note(
                    f"{module}: в data/ есть schema.sql, но в reference_answers.md "
                    f"нет ни одного маркера «Эталон: <csv> — <шаг>» — эталоны "
                    f"SQL-модуля не сверяются с состоянием базы шага"
                )
            continue

        modules_with_markers.append(module)
        readme = data_dir / "README.md"
        order = _parse_load_order(readme.read_text(encoding="utf-8")) if readme.exists() else None
        if not order:
            note(
                f"{module}: есть маркеры «Эталон:», но в data/README.md нет "
                f"таблицы «Порядок загрузки» — не из чего собрать состояние базы шага"
            )
            continue

        # Эталон без маркера — то же самое, что эталон, никем не проверяемый:
        # проверка обязана падать, а не тихо покрывать только часть файлов.
        marked_csv = {csv for csv, _, _ in markers}
        for csv_path in sorted(data_dir.glob("*.csv")):
            if csv_path.name not in marked_csv:
                note(
                    f"{module}: {csv_path.name} лежит в data/ SQL-модуля, но "
                    f"не привязан маркером «Эталон:» ни к одному запросу"
                )

        for csv_name, step, query in markers:
            checked += 1
            label = f"{module}: {csv_name} на состоянии базы {step}"
            csv_path = data_dir / csv_name
            if not csv_path.exists():
                note(f"{label}: файл эталона не найден")
                continue
            if not query.strip():
                note(f"{label}: после маркера «Эталон:» нет блока ```sql")
                continue
            files_used = _cumulative_sql_files(order, step)
            if "schema.sql" not in files_used:
                note(
                    f"{label}: в накопительном списке файлов до этого шага нет "
                    f"schema.sql — таблиц в базе не будет вовсе, сверять не с чем"
                )
                continue

            try:
                conn = sqlite3.connect(":memory:")
                for fname in files_used:
                    conn.executescript((data_dir / fname).read_text(encoding="utf-8"))
                cur = conn.execute(query)
                got_header = [d[0] for d in cur.description]
                got_rows = [[_cell(v) for v in row] for row in cur.fetchall()]
                conn.close()
            except Exception as exc:  # noqa: BLE001 — любая ошибка SQL — FAIL проверки, не крах скрипта
                note(f"{label}: запрос не выполнился: {exc}")
                continue

            with csv_path.open(encoding="utf-8", newline="") as f:
                csv_rows = list(csv.reader(f))
            if not csv_rows:
                note(f"{label}: эталонный CSV пуст")
                continue
            want_header, want_rows = csv_rows[0], csv_rows[1:]

            if got_header != want_header:
                note(f"{label}: колонки запроса {got_header} против колонок CSV {want_header}")
                continue
            if len(got_rows) != len(want_rows):
                note(
                    f"{label}: CSV содержит {len(want_rows)} строк, запрос на "
                    f"состоянии базы этого шага ({', '.join(files_used)}) дал "
                    f"{len(got_rows)} — эталон посчитан на другом состоянии базы"
                )
                continue
            for i, (got, want) in enumerate(zip(got_rows, want_rows), start=1):
                if got != want:
                    note(f"{label}: строка {i} расходится: запрос {got}, CSV {want}")
                    break

    uncovered = UNCOVERED + (
        f"; модули без SQL-эталонов: {', '.join(skipped_modules)}" if skipped_modules else ""
    )
    if not checked:
        ok(
            "эталоны на состоянии базы своего шага: маркеров «Эталон:» не "
            f"найдено ни в одном модуле — сверять нечего. НЕ покрыто: {uncovered}"
        )
    elif local_fails:
        print(
            f"       (сверялось {checked} пар CSV ↔ запрос в модулях: "
            f"{', '.join(modules_with_markers)}; см. [FAIL] выше)"
        )
    else:
        ok(
            f"эталоны на состоянии базы своего шага: сверено {checked} пар "
            f"(CSV ↔ запрос) в модулях: {', '.join(modules_with_markers)}. "
            f"НЕ покрыто: {uncovered}"
        )


def _load_gitignore_patterns() -> list[str]:
    gi = ROOT / ".gitignore"
    if not gi.exists():
        return []
    return [
        line.strip() for line in gi.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _matches_gitignore(rel_path: Path, patterns: list[str]) -> bool:
    """Упрощённое сопоставление с .gitignore: не полный синтаксис (нет
    отрицаний `!`, нет привязки паттернов с `/` строго к корню) — для
    текущего .gitignore этого репозитория (несколько плоских glob-паттернов)
    этого достаточно; если .gitignore обрастёт вложенными/анкорными
    паттернами, эту функцию придётся расширять, а не просто доверять ей."""
    name = rel_path.name
    posix = rel_path.as_posix()
    for pat in patterns:
        pat = pat.rstrip("/")
        if fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(posix, pat) or fnmatch.fnmatch(posix, f"*/{pat}"):
            return True
    return False


def check_data_dir_no_stray_files() -> None:
    """Файлы в program/M*/data/, не упомянутые ни в README.md той же папки,
    ни покрытые .gitignore, — вероятный случайный артефакт: например, файл
    с именем `--help`, который sqlite3.connect создаёт молча, если аргумент
    argparse не распознан как флаг и попадает в позиционный путь к базе
    (реальная находка при ревью generate_activity_log.py, не гипотетическая).
    Проверка — по названию файла как подстроке текста README, тот же
    формат, в котором все текущие data/README.md перечисляют свои файлы
    (таблица «Файлы»)."""
    if not PROGRAM_DIR.exists():
        return
    data_dirs = sorted(PROGRAM_DIR.glob("M*/data"))
    if not data_dirs:
        ok("program/M*/data/: директорий не найдено — проверка на мусор пропущена")
        return

    patterns = _load_gitignore_patterns()
    checked = 0
    stray: list[str] = []
    for data_dir in data_dirs:
        readme_path = data_dir / "README.md"
        readme_text = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""
        for f in sorted(data_dir.iterdir()):
            if f.is_dir() or f.name == "README.md":
                continue
            checked += 1
            rel = f.relative_to(ROOT)
            if _matches_gitignore(rel, patterns):
                continue
            if f.name in readme_text:
                continue
            stray.append(str(rel))

    if stray:
        for rel in stray:
            fail(f"{rel}: не упомянут в README.md своей папки и не покрыт .gitignore — похоже на случайный артефакт")
    else:
        ok(f"program/M*/data/: проверено {checked} файлов в {len(data_dirs)} папках, ни одного не покрытого README/.gitignore не найдено")


CODE_FENCE = re.compile(r"```.*?\n(.*?)```", re.DOTALL)
INLINE_CODE = re.compile(r"`[^`]*`", re.DOTALL)


def strip_code(text: str) -> str:
    """Убирает блоки кода и `инлайн-код` перед проверкой запрещённых слов —
    она проверяет прозу для читателя, а не код: коды ошибок Excel
    (`#N/A`, `#REF!`) и ссылки на лист (`Sheet!A:A`) не запрещённые
    формулировки, даже когда содержат "!" или подстроку из списка."""
    text = CODE_FENCE.sub("", text)
    text = INLINE_CODE.sub("", text)
    return text


def check_forbidden(text_files: list[Path]) -> None:
    """Запрещённые слова и фразы — только по прозе шага (код исключается,
    см. strip_code). POSIX-команды — только внутри блоков кода: решение 13
    запрещает давать их учащемуся как команду для запуска, а не упоминать в
    прозе (сам файл решения 13 объясняет peek_clients.py как замену
    `grep`+`awk`)."""
    any_hit = False
    for f in text_files:
        rel = f.relative_to(ROOT)
        text = f.read_text(encoding="utf-8")
        prose = strip_code(text)
        for phrase in FORBIDDEN_PHRASES:
            hay = prose.lower() if phrase.isalpha() else prose
            needle = phrase.lower() if phrase.isalpha() else phrase
            if needle in hay:
                any_hit = True
                fail(f"{rel}: запрещённая формулировка/символ {phrase!r}")

        for pattern in FORBIDDEN_PATTERNS:
            for m in pattern.finditer(prose):
                any_hit = True
                fail(f"{rel}: запрещённая формулировка {m.group(0)!r}")

        for block in CODE_FENCE.finditer(text):
            code = block.group(1)
            offset = block.start(1)
            for pattern in POSIX_COMMAND_PATTERNS:
                for m in pattern.finditer(code):
                    any_hit = True
                    line_no = text.count("\n", 0, offset + m.start()) + 1
                    fail(
                        f"{rel}:{line_no}: POSIX-команда {m.group(0)!r} "
                        f"внутри блока кода (решение 13)"
                    )
    if not any_hit:
        ok("program/**/*.md: запрещённых слов и POSIX-команд в коде не найдено")


def main() -> int:
    blueprint_text = BLUEPRINT.read_text(encoding="utf-8")
    claude_text = CLAUDE_MD.read_text(encoding="utf-8")

    check_hours(blueprint_text, claude_text)
    check_skill_ids(blueprint_text)
    check_decision_numbering()
    check_deferred_paths()
    check_step00(blueprint_text)
    check_data_readme_counts()
    check_reference_csv_state()
    check_data_dir_no_stray_files()

    if PROGRAM_DIR.exists():
        step_files = [f for f in PROGRAM_DIR.rglob("*.md") if f.name != "pilot-report.md"]
        check_forbidden(step_files)

    print()
    if FAILED:
        print("Есть проблемы — см. [FAIL] выше.")
        return 1
    print("Все проверки прошли.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
