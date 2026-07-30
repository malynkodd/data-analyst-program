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
    check_step00(blueprint_text)
    check_data_readme_counts()
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
