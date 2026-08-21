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
import subprocess
import sys
from pathlib import Path

if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
BLUEPRINT = ROOT / "design" / "blueprint.md"
CLAUDE_MD = ROOT / "CLAUDE.md"
DECISIONS = ROOT / "design" / "decisions.md"
PROGRAM_DIR = ROOT / "program"
TOOLS_GATE = ROOT / "research" / "tools-gate.md"
UI_LABELS = ROOT / "research" / "pbi-ui-labels.md"

EM_DASH = "—"  # em dash: разделитель в заголовке дефекта и в статусе «не чинится»

# Заголовок дефекта гейта: **R12 — ...**, **D1 — ...** или **S3 — ...** с
# начала строки. Буквы даны явным перечислением [RDS], а не общим классом
# [A-Z]: разделы 1–2 tools-gate.md используют тот же рисунок «**<буква><N> —
# ...**» под B1..B6 и P1..P9 для находок, сделанных до решения 27 и не
# несущих строки 'Статус:' — общий класс задним числом потребовал бы её от
# них и дал бы ложные [FAIL] (решение 32).
DEFECT_HEADING = re.compile(r"^\*\*([RDS]\d+) " + EM_DASH + r" ")

# Три разрешённые формы учётной строки (решение 27, часть 2). Набор
# закрытый намеренно: свободная формулировка ломает проверку опечаткой,
# а спотыкающуюся проверку обходят первой же правкой.
STATUS_FORMS = {
    "открыт": re.compile(r"^Статус: открыт$"),
    "закрыт": re.compile(r"^Статус: закрыт \d{4}-\d{2}-\d{2}, [0-9a-f]{7,40}, \S.*$"),
    "не чинится": re.compile(r"^Статус: не чинится " + EM_DASH + r" \S.*$"),
}

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


def warn(msg: str) -> None:
    """Предупреждение: печатается, но прогон не роняет. Для случаев, где
    факт возможен и честен, но обязан быть замечен, а не принят за успех
    (решение 24: сумма часов, совпавшая с вилкой по обеим границам).
    [FAIL] здесь был бы вреден — он создаёт стимул подвинуть честное
    число ради зелёного вывода, то есть ровно ту подгонку, против которой
    проверка и заводится."""
    print(f"[WARN] {msg}")


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
# Инфраструктурный шаг (решение 23): установка инструмента, перенос данных
# между движками, настройка окружения. Умения не несёт и в покрытии не
# участвует, но пометка обязательна — шаг без строки "Умение:" вовсе
# считается дефектом, а не третьим, молчаливым вариантом.
INFRA_HEADER = re.compile(r"^Умение:\s*[—–-]\s*\(инфраструктура\)", re.MULTILINE)
STEP_FILE = re.compile(r"^step-(\d+)\.md$")


def _content_steps() -> list[Path]:
    """Содержательные шаги: program/[MP]*/step-NN.md с NN > 0. step-00.md —
    служебная декларация модуля, а не шаг, и строки 'Умение:' не имеет."""
    out: list[Path] = []
    for f in sorted(PROGRAM_DIR.glob("[MP]*/step-*.md")):
        m = STEP_FILE.match(f.name)
        if m and int(m.group(1)) > 0:
            out.append(f)
    return out


def check_step_skill_header() -> None:
    """Каждый содержательный шаг объявляет, к какому из двух видов он
    относится: несёт умение (ID из части 1 blueprint) или инфраструктурный
    (решение 23). Молчание — [FAIL].

    До решения 23 отсутствие ID означало, что шага не должно существовать,
    и инфраструктурный шаг приходилось приписывать к умению: step-09.md
    (установка PostgreSQL и перенос данных) был объявлен «частью 6 из 7»
    умения A2, после чего пять шагов из семи продолжали писать «часть N из
    5», а два шага одновременно называли себя финальной частью A2."""
    if not PROGRAM_DIR.exists():
        return
    steps = _content_steps()
    if not steps:
        ok("program/[MP]*/step-NN.md: содержательных шагов не найдено — проверка пропущена")
        return

    infra: list[str] = []
    silent: list[str] = []
    with_skill = 0
    for f in steps:
        text = f.read_text(encoding="utf-8")
        if INFRA_HEADER.search(text):
            infra.append(f.relative_to(ROOT).as_posix())
        elif SKILL_HEADER.search(text):
            with_skill += 1
        else:
            silent.append(f.relative_to(ROOT).as_posix())

    for rel in silent:
        fail(
            f"{rel}: нет строки 'Умение: <ID>' и нет пометки "
            f"'Умение: — (инфраструктура)' — шаг не объявил, несёт он умение "
            f"или нет (решение 23)"
        )
    if not silent:
        tail = f"инфраструктурные: {', '.join(infra)}" if infra else "инфраструктурных нет"
        ok(
            f"program/[MP]*/step-NN.md: все {len(steps)} шагов объявили вид — "
            f"{with_skill} с умением, {len(infra)} без; {tail}"
        )


# Фраза-утверждение о факте прогона — не заголовок и не пример вывода
# скрипта, поэтому не FORBIDDEN_PHRASES, а отдельный факт-чек (решение 33).
RUN_DATE = re.compile(r"[Пп]рогон[^\n]*?автора\s+(\d{4}-\d{2}-\d{2})")


def _file_commit_date(path: Path) -> str | None:
    """Дата (ГГГГ-ММ-ДД) последнего коммита, тронувшего файл. None, если
    файл ещё не закоммичен — сравнивать заявленную дату прогона не с чем."""
    result = subprocess.run(
        ["git", "log", "-1", "--format=%ad", "--date=short", "--", str(path)],
        cwd=ROOT, capture_output=True, text=True,
    )
    return result.stdout.strip() or None


def check_run_dates() -> None:
    """Дата в строке «Прогон ... на машине автора ГГГГ-ММ-ДД» обязана быть
    датой реального события — прогон не может случиться позже коммита,
    который принёс в репозиторий его же результат (решение 33).

    Найдено внешним аудитом: `SEED` в `program/M9/data/traps_*.py`
    (20260823…20260826, выбор датасета, не дата) и порядковый номер модуля
    в последовательности M8→M13 были по ошибке приняты за календарные даты
    прогона — текст утверждал дни вплоть до 2026-08-27, хотя `git log`
    показывает один и тот же коммит-день для всех, 2026-08-20. Проверка не
    ловит будущую ошибку того же класса без даты git — если файл ещё не
    закоммичен, сравнивать не с чем, он пропускается."""
    if not PROGRAM_DIR.exists():
        return
    problems: list[str] = []
    checked = 0
    for f in sorted(PROGRAM_DIR.rglob("*.md")):
        text = f.read_text(encoding="utf-8")
        for m in RUN_DATE.finditer(text):
            claimed = m.group(1)
            commit_date = _file_commit_date(f)
            if commit_date is None:
                continue
            checked += 1
            if claimed > commit_date:
                rel = f.relative_to(ROOT).as_posix()
                problems.append(
                    f"{rel}: заявлен прогон {claimed}, но коммит, принёсший файл, "
                    f"датирован {commit_date} — прогон не может быть позже своего коммита"
                )
    for p in problems:
        fail(p)
    if not problems:
        ok(
            f"program/**/*.md: {checked} упоминаний 'Прогон ... на машине автора' — "
            f"ни одно не позже своего коммита"
        )


# Вторая граница необязательна: точечная оценка ("Время: 3 ч") законна,
# когда объём задан внешним фактом, а не диапазоном (M13 — "объём задан
# 40 вакансиями", часть 4 blueprint, решение 1; часть 6.1 несёт для него
# точку "8", а не диапазон, и parse_range() уже поддерживает эту форму
# для таблиц — здесь то же допущение для строки шага).
STEP_HOURS = re.compile(rf"^Время:\s*([\d.]+)(?:{DASH}([\d.]+))?\s*ч", re.MULTILINE)
MODULE_ROW_ID = re.compile(r"^(M\d+)\b")

# Пометка в строке модуля части 6.1: вилка не оценена, а поставлена по
# построчной сумме уже написанных шагов (решение 28, потом решение 31).
# Номер решения не фиксирован — каждый следующий модуль, чья вилка
# правится тем же способом, заводит свою пометку с новым номером. Меняет
# текст [WARN] при совпадении суммы с вилкой по обеим границам — см.
# check_module_hours.
BY_FACT_RE = re.compile(r"вилка по факту \(решение \d+\)")


def _fmt(x: float) -> str:
    return f"{x:g}"


def check_module_hours(blueprint_text: str) -> None:
    """Построчная сумма часов шагов модуля против вилки части 6.1 blueprint.

    Решение 24: сумма шагов — факт, вилка — оценка; при расхождении
    правится вилка, а не часы в шагах. Отсюда две ситуации, которые
    проверка обязана называть вслух, и обе — [WARN], не [FAIL]: обе
    возможны честно, но обе обязаны быть замечены.

    (а) Сумма совпала с вилкой по **обеим** границам. Независимые оценки в
    заданный интервал обеими границами не попадают: M0 дал 7.0–9.0 при
    вилке 7–9, M1 — 8.0–10.0 при 8–10, M2 — 30.0–40.0 при 30–40, и метод
    был назван в самих файлах («без запаса на обеих границах», «тот же
    стиль сведения»). Подогнанная сумма уничтожает данные для калибровки
    по research/self.md до того, как они появятся.

    (б) Сумма целиком вне вилки — то, что случилось с M3 (37–47 при
    60–80). Это сигнал сначала искать недостающее содержание (там его и
    нашли: шаги 09–12 довели сумму до 60–77), и только потом править
    вилку.

    (в) Случай (а) бывает двух разных происхождений, и различить их обязан
    вывод, а не память читателя. У M0/M1/M2 сумму шагов подвели под
    известную вилку; у M4 и M5 наоборот — вилку поставили по посчитанной
    сумме (решения 28 и 31 соответственно). После правки вилки M4
    одинаковую строку «признак подгонки» печатали четыре модуля из пяти, и
    два из них означали противоположное. Одинаковые предупреждения, часть
    которых означает разное, — это шум, а шум перестают читать. Поэтому
    строка части 6.1 может нести пометку «вилка по факту (решение N)» с
    номером решения, которое её завело, и для таких модулей печатается
    другое сообщение — с тем же номером, не захардкоженным 28-м."""
    if not PROGRAM_DIR.exists():
        return

    part61 = section(blueprint_text, "## 6.1.", "## 6.2.")
    brackets: dict[str, tuple[int, int]] = {}
    by_fact: dict[str, str] = {}
    for line in part61.splitlines():
        if not line.startswith("|") or re.match(r"^\|[\s:\-|]+\|?$", line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        m = MODULE_ROW_ID.match(cells[0].strip("*"))
        rng = parse_range(cells[1])
        if m and rng:
            brackets[m.group(1)] = rng
            mark = BY_FACT_RE.search(line)
            if mark:
                by_fact[m.group(1)] = mark.group(0)

    module_dirs = sorted(
        (p for p in PROGRAM_DIR.iterdir() if p.is_dir() and re.fullmatch(r"M\d+", p.name)),
        key=lambda p: int(p.name[1:]),
    )
    if not module_dirs:
        return

    reported = 0
    for d in module_dirs:
        steps = [f for f in _content_steps() if f.parent == d]
        pairs: list[tuple[float, float]] = []
        no_hours: list[str] = []
        for f in steps:
            m = STEP_HOURS.search(f.read_text(encoding="utf-8"))
            if m:
                low = float(m.group(1))
                high = float(m.group(2)) if m.group(2) is not None else low
                pairs.append((low, high))
            else:
                no_hours.append(f.name)
        if no_hours:
            fail(f"{d.name}: шаги без разбираемой строки 'Время: N{DASH}M ч': {', '.join(no_hours)}")
            continue
        if not pairs:
            continue
        low = sum(p[0] for p in pairs)
        high = sum(p[1] for p in pairs)
        bracket = brackets.get(d.name)
        if bracket is None:
            fail(f"{d.name}: в части 6.1 blueprint нет строки с вилкой часов для этого модуля")
            continue
        b_low, b_high = bracket
        reported += 1
        label = (
            f"{d.name}: сумма {len(pairs)} шагов {_fmt(low)}{DASH}{_fmt(high)} ч "
            f"при вилке 6.1 {b_low}{DASH}{b_high}"
        )
        if low == b_low and high == b_high and d.name in by_fact:
            warn(
                f"{label} — вилка выставлена по сумме шагов «{by_fact[d.name]}», "
                f"прохождением не подтверждена: калибровать её нечем, пока "
                f"модуль никто не прошёл"
            )
        elif low == b_low and high == b_high:
            warn(
                f"{label} — совпадение по обеим границам: признак подгонки суммы "
                f"под вилку, а не подтверждение оценок (решение 24)"
            )
        elif d.name in by_fact:
            warn(
                f"{label} — вилка помечена «{by_fact[d.name]}», но сумма шагов с ней "
                f"уже расходится: пометка устарела — править вилку или снимать пометку"
            )
        elif high < b_low or low > b_high:
            warn(
                f"{label} — сумма целиком вне вилки: сначала искать недостающее "
                f"содержание, потом править вилку в blueprint (решение 24)"
            )
        else:
            ok(label)

    if reported == 0:
        ok("часы по модулям: ни одного модуля с разобранными часами шагов")


PART2_TOTAL_ROW = re.compile(r"^Итого (ядро|обвязка)$")
PART2_HEADING_RANGE = re.compile(rf"(\d+){DASH}(\d+) ч")


def check_part2_hours(blueprint_text: str) -> None:
    """Часы в частях 2.1 и 2.2 blueprint против части 6.1.

    Те же числа стоят в двух таблицах, и однажды они уже разъехались: итоги
    ядра и обвязки в части 2 остались в редакции до решения 14 (253–360 и
    109–136), пока CLAUDE.md и часть 6.1 полтора месяца несли 252–359 и
    110–137. Нашлось это не скриптом, а глазами — при правке вилки M4
    (решение 28). Проверка сверяет три вещи в каждой части: вилку каждого
    модуля против 6.1, строку «Итого» против построчной суммы своей же
    таблицы и число в заголовке раздела против той же суммы."""
    part61 = section(blueprint_text, "## 6.1.", "## 6.2.")
    ref: dict[str, tuple[int, int]] = {}
    for line in part61.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        m = MODULE_ROW_ID.match(cells[0].strip("*"))
        rng = parse_range(cells[1])
        if m and rng:
            ref[m.group(1)] = rng

    parts = (("2.1", "## 2.1.", "## 2.2."), ("2.2", "## 2.2.", "## 2.3."))
    checked = 0
    for name, start, end in parts:
        text = section(blueprint_text, start, end)
        heading = text.splitlines()[0] if text else ""
        low = high = 0
        rows = 0
        problems = 0
        declared: tuple[int, int] | None = None
        for line in text.splitlines():
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 3:
                continue
            label = cells[0].strip("*")
            rng = parse_range(cells[2].strip("*"))
            if rng and PART2_TOTAL_ROW.match(label):
                declared = rng
                continue
            m = MODULE_ROW_ID.match(label)
            if not (m and rng):
                continue
            rows += 1
            low += rng[0]
            high += rng[1]
            expected = ref.get(m.group(1))
            if expected is None:
                fail(f"часть {name}: модуль {m.group(1)} есть в части 2, но не в части 6.1")
                problems += 1
            elif expected != rng:
                fail(
                    f"часть {name}: {m.group(1)} заявляет {rng[0]}{DASH}{rng[1]} ч, "
                    f"а часть 6.1 — {expected[0]}{DASH}{expected[1]}"
                )
                problems += 1
            checked += 1

        if rows == 0:
            fail(f"часть {name}: не удалось распарсить ни одной строки модуля")
            continue
        if declared is None:
            fail(f"часть {name}: в таблице нет строки «Итого» с вилкой часов")
            problems += 1
        elif declared != (low, high):
            fail(
                f"часть {name}: строка «Итого» заявляет {declared[0]}{DASH}{declared[1]}, "
                f"а построчная сумма таблицы — {low}{DASH}{high}"
            )
            problems += 1
        m = PART2_HEADING_RANGE.search(heading)
        if not m:
            fail(f"часть {name}: в заголовке раздела нет числа часов вида «N{DASH}M ч»")
            problems += 1
        elif (int(m.group(1)), int(m.group(2))) != (low, high):
            fail(
                f"часть {name}: заголовок раздела заявляет {m.group(1)}{DASH}{m.group(2)} ч, "
                f"а построчная сумма таблицы — {low}{DASH}{high}"
            )
            problems += 1
        if problems == 0:
            ok(f"часть {name}: {rows} модулей, сумма {low}{DASH}{high} ч — "
               f"совпадает с заголовком, строкой «Итого» и вилками части 6.1")

    if checked == 0:
        fail("части 2.1/2.2: ни одной строки модуля не сверено с частью 6.1")


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
    # ID умений и проверка покрытия перестаёт быть проверкой. Шаги с
    # пометкой "Умение: — (инфраструктура)" сюда не попадают по построению
    # регулярного выражения: они не закрывают ничего (решение 23).
    missing = [i for i in all_ids if i not in header_ids]
    if missing:
        fail(f"умения без шапки 'Умение: <ID>' ни в одном шаге program/**/*.md: {', '.join(missing)}")
    else:
        ok(f"все {len(all_ids)} умений закрыты шапкой 'Умение:' хотя бы одного шага program/")


def check_step00(blueprint_text: str) -> None:
    if not PROGRAM_DIR.exists():
        return
    module_dirs = sorted(
        p for p in PROGRAM_DIR.iterdir() if p.is_dir() and re.fullmatch(r"[MP]\d+", p.name)
    )
    if not module_dirs:
        ok("program/: ни один модуль или проект ещё не начат — проверка step-00.md пропущена")
        return
    missing = [d.name for d in module_dirs if not (d / "step-00.md").exists()]
    if missing:
        fail(f"модули/проекты без step-00.md: {', '.join(missing)}")
    else:
        ok(f"все {len(module_dirs)} начатых модулей и проектов имеют step-00.md")


DECISION_HEADING = re.compile(r"^## (\d+)\. ", re.MULTILINE)


def check_calendar_covers_settled() -> None:
    """Календарь датасета обязан покрывать максимальную дату расчёта:
    max(settled_date) <= max(date_key), по каждой папке данных.

    Это дефект D1 (`research/tools-gate.md`, 3.8), найденный прогоном
    гейта: календарь резался по границе периода операций, а `settled_date`
    её переступает на 1–5 дней. Тридцать операций на 47482.23 (0.46%
    оборота) проваливались в строку с пустым измерением на том самом
    разрезе, который требует задание 5 `step-03.md`, — и проваливались
    тихо: итог сходился.

    Проверка написана поперёк папок и колонок, а не под M4: любая пара
    «календарь + факт с датой» в program/*/data/ попадает под неё. Папки
    в .gitignore (решение 22: в репозитории генератор, а не данные),
    поэтому отсутствие папки — не ошибка, а «нечего проверять»: датасет
    собирается запуском генератора."""
    if not PROGRAM_DIR.exists():
        return

    checked = 0
    problems = False
    for cal_path in sorted(PROGRAM_DIR.glob("[MP]*/data/*/calendar.csv")):
        tx_path = cal_path.parent / "transactions.csv"
        if not tx_path.exists():
            continue
        try:
            with cal_path.open(encoding="utf-8", newline="") as f:
                max_key = max(r["date_key"] for r in csv.DictReader(f))
            with tx_path.open(encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
            max_settled = max(r["settled_date"] for r in rows)
            outside = [r for r in rows if r["settled_date"] > max_key]
        except (KeyError, ValueError) as exc:
            fail(f"{cal_path.parent.relative_to(ROOT)}: не удалось проверить покрытие календаря: {exc}")
            problems = True
            continue

        checked += 1
        if outside:
            lost = sum(float(r["amount_uah"]) for r in outside)
            fail(
                f"{cal_path.parent.relative_to(ROOT)}: календарь кончается {max_key}, "
                f"а max(settled_date) = {max_settled} — {len(outside)} операций на {lost:.2f} "
                f"уйдут в строку с пустым измерением (дефект D1)"
            )
            problems = True

    if checked and not problems:
        ok(f"program/[MP]*/data/: календарь покрывает дату расчёта, сверено папок: {checked}")
    elif not checked:
        ok("program/[MP]*/data/: папок с calendar.csv и transactions.csv нет — датасет не собран, проверка пропущена")


def check_defect_status() -> None:
    """У каждого дефекта гейта в research/tools-gate.md ровно одна строка
    статуса из трёх разрешённых форм (решение 27, часть 2).

    Зачем закрытый набор значений: свободная формулировка означает, что
    проверка спотыкается на опечатках, а спотыкающуюся проверку обходят
    первой же правкой. Зачем вообще: без учёта закрытость 36 дефектов
    гейта в аудите Фазы 4 недоказуема — отчёт о заходе не является
    доказательством, он является утверждением.

    Проверяется три вещи: заголовок дефекта не остался без статуса,
    статус ровно один и написан по грамматике, нумерация каждой буквенной
    серии (R, D, S) сплошная с 1 внутри себя. Серия S заведена решением 32
    для дефектов проверочных скриптов вне гейта Power BI (M4), который
    единолично занимает серию R. Отрицательный пример к этой проверке
    прогнан при её заведении — research/tools-gate.md, 5.5; отрицательный
    пример к серии S — там же, 5.13."""
    if not TOOLS_GATE.exists():
        fail("research/tools-gate.md не найден — учёт дефектов гейта проверить нечем")
        return

    lines = TOOLS_GATE.read_text(encoding="utf-8").split("\n")
    blocks: list[tuple[str, int, int]] = []  # (id, начало, конец)
    for i, line in enumerate(lines):
        m = DEFECT_HEADING.match(line)
        if m:
            if blocks:
                blocks[-1] = (blocks[-1][0], blocks[-1][1], i)
            blocks.append((m.group(1), i, len(lines)))
    if not blocks:
        fail("research/tools-gate.md: не найдено ни одного заголовка дефекта '**R<NN> — '")
        return

    # блок дефекта кончается следующим дефектом или ближайшим заголовком
    # раздела — иначе последний дефект секции 3.3 захватил бы разделы 3.4–3.7
    bounded = []
    for did, start, end in blocks:
        stop = end
        for j in range(start + 1, end):
            if lines[j].startswith("#"):
                stop = j
                break
        bounded.append((did, start, stop))

    problems = False
    counts = {"открыт": 0, "закрыт": 0, "не чинится": 0}
    for did, start, stop in bounded:
        found = [ln for ln in lines[start:stop] if ln.startswith("Статус:")]
        if not found:
            fail(f"research/tools-gate.md: дефект {did} без строки 'Статус:' (решение 27)")
            problems = True
            continue
        if len(found) > 1:
            fail(f"research/tools-gate.md: у дефекта {did} строк 'Статус:' {len(found)}, нужна ровно одна")
            problems = True
            continue
        line = found[0]
        for name, pattern in STATUS_FORMS.items():
            if pattern.match(line):
                counts[name] += 1
                break
        else:
            fail(
                f"research/tools-gate.md: дефект {did} — статус не по формату решения 27: {line!r}. "
                f"Разрешено: 'Статус: открыт', "
                f"'Статус: закрыт ГГГГ-ММ-ДД, <коммит>, <файл:раздел>', "
                f"'Статус: не чинится {EM_DASH} <обоснование>'"
            )
            problems = True

    stray = sum(1 for ln in lines if ln.startswith("Статус:")) - sum(
        1 for did, start, stop in bounded for ln in lines[start:stop] if ln.startswith("Статус:")
    )
    if stray:
        fail(
            f"research/tools-gate.md: строк 'Статус:' вне блоков дефектов: {stray} — "
            f"слово зарезервировано под учёт дефектов (решение 27)"
        )
        problems = True

    # Нумерация проверяется отдельно по каждой букве-серии (R, D, S, ...) —
    # не только по R, как было до решения 32: каждая серия обязана идти
    # подряд с 1 внутри себя, независимо от других серий.
    by_prefix: dict[str, list[int]] = {}
    for d, _, _ in bounded:
        by_prefix.setdefault(d[0], []).append(int(d[1:]))

    for prefix in sorted(by_prefix):
        numbers = sorted(by_prefix[prefix])
        expected = list(range(1, len(numbers) + 1))
        if numbers != expected:
            missing = sorted(set(expected) - set(numbers))
            dupes = sorted({n for n in numbers if numbers.count(n) > 1})
            fail(
                f"research/tools-gate.md: нумерация дефектов {prefix} не сплошная — "
                f"пропущены: {missing or 'нет'}, повторяются: {dupes or 'нет'}"
            )
            problems = True

    if not problems:
        series = ", ".join(
            f"{prefix}1..{prefix}{max(numbers)}" if len(numbers) > 1 else f"{prefix}{numbers[0]}"
            for prefix, numbers in sorted(by_prefix.items())
        )
        ids = ", ".join(f"{n}: {c}" for n, c in counts.items())
        ok(f"research/tools-gate.md: {len(bounded)} дефектов со статусом ({series}) — {ids}")


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
    """Числа, заявленные в program/[MP]*/data/README.md (раздел «Проверка
    строк»), сверяются с фактическими файлами — тот же класс ошибки, что
    рассогласование часов/умений: число один раз посчитано руками и
    разошлось с данными после правки (M3: «17 заказов» осталось в прозе
    после расширения датасета до 19 строк, найдено вручную одной сессией
    ревью, не автоматически — отсюда эта проверка)."""
    if not PROGRAM_DIR.exists():
        return
    readmes = sorted(PROGRAM_DIR.glob("[MP]*/data/README.md"))
    if not readmes:
        ok("program/[MP]*/data/README.md: файлов не найдено — проверка пропущена")
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
        ok(f"program/[MP]*/data/README.md: сверено {checked} строк из раздела «Проверка строк» во всех {len(readmes)} файлах")
    else:
        ok(f"program/[MP]*/data/README.md: найдено {len(readmes)} файлов, ни один не содержит раздел «Проверка строк»")


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
    """Таблица «Порядок загрузки» из program/[MP]*/data/README.md:
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
    program/[MP]*/data/README.md.

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

    data_dirs = sorted(PROGRAM_DIR.glob("[MP]*/data"))
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
    """Файлы в program/[MP]*/data/, не упомянутые ни в README.md той же папки,
    ни покрытые .gitignore, — вероятный случайный артефакт: например, файл
    с именем `--help`, который sqlite3.connect создаёт молча, если аргумент
    argparse не распознан как флаг и попадает в позиционный путь к базе
    (реальная находка при ревью generate_activity_log.py, не гипотетическая).
    Проверка — по названию файла как подстроке текста README, тот же
    формат, в котором все текущие data/README.md перечисляют свои файлы
    (таблица «Файлы»)."""
    if not PROGRAM_DIR.exists():
        return
    data_dirs = sorted(PROGRAM_DIR.glob("[MP]*/data"))
    if not data_dirs:
        ok("program/[MP]*/data/: директорий не найдено — проверка на мусор пропущена")
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
        ok(f"program/[MP]*/data/: проверено {checked} файлов в {len(data_dirs)} папках, ни одного не покрытого README/.gitignore не найдено")


CODE_FENCE = re.compile(r"```.*?\n(.*?)```", re.DOTALL)
INLINE_CODE = re.compile(r"`[^`]*`", re.DOTALL)


def _registry_rows(heading: str) -> list[list[str]]:
    """Строки таблицы из раздела реестра надписей: ячейки без обрамления."""
    text = UI_LABELS.read_text(encoding="utf-8")
    start = text.index(heading) + len(heading)
    end = text.find("\n## ", start)
    body = text[start:] if end < 0 else text[start:end]
    rows = []
    for line in body.split("\n"):
        line = line.strip()
        if not line.startswith("|") or set(line) <= set("|- "):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cells and cells[0].lower().startswith("запрещено"):
            continue
        if cells and cells[0].startswith("Надпись"):
            continue
        rows.append(cells)
    return rows


def check_ui_labels() -> None:
    """Надписи интерфейса, измеренные как неверные, не должны возвращаться
    в шаги. Гейт дал шесть дефектов одного класса (R2, R9, R10, R16, R18,
    R28, R31): текст называет вкладку по смыслу действия, а не по надписи
    на ленте. Правка шести мест ничего не гарантирует — гарантирует
    реестр `research/pbi-ui-labels.md` плюс эта проверка.

    Поиск идёт по сырому тексту с \\s+ между словами надписи: перенос
    строки посреди «Инструменты для\\nмер» её не прячет."""
    if not UI_LABELS.exists():
        fail(f"нет реестра надписей {UI_LABELS.relative_to(ROOT)} — проверка шагов невозможна")
        return

    banned = []
    for cells in _registry_rows("## 2. Запрещённые формы"):
        if len(cells) < 3:
            continue
        label = cells[0].strip("`")
        if label:
            banned.append((label, cells[1].strip("`"), cells[2]))

    if not banned:
        fail(f"{UI_LABELS.relative_to(ROOT)}: раздел 2 пуст — читать нечего")
        return

    hits = 0
    for f in sorted(PROGRAM_DIR.rglob("*.md")):
        text = f.read_text(encoding="utf-8")
        rel = f.relative_to(ROOT)
        for label, replacement, defect in banned:
            pattern = re.compile(r"\s+".join(re.escape(w) for w in label.split()))
            for m in pattern.finditer(text):
                hits += 1
                line_no = text.count("\n", 0, m.start()) + 1
                fail(
                    f"{rel}:{line_no}: надпись {label!r} измерена как неверная "
                    f"({defect}); в интерфейсе — {replacement}"
                )
    if not hits:
        ok(
            f"program/**/*.md: ни одной из {len(banned)} надписей, измеренных "
            f"как неверные ({UI_LABELS.relative_to(ROOT)}, раздел 2)"
        )

    unconfirmed = len(_registry_rows("## 3. Надписи, прогоном не подтверждённые"))
    if unconfirmed:
        warn(
            f"{UI_LABELS.relative_to(ROOT)}: {unconfirmed} надписи взяты не с экрана "
            f"— подтвердить или опровергнуть на первом прогоне M4 (раздел 3)"
        )


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
    check_part2_hours(blueprint_text)
    check_module_hours(blueprint_text)
    check_skill_ids(blueprint_text)
    check_step_skill_header()
    check_run_dates()
    check_decision_numbering()
    check_defect_status()
    check_calendar_covers_settled()
    check_deferred_paths()
    check_step00(blueprint_text)
    check_data_readme_counts()
    check_reference_csv_state()
    check_data_dir_no_stray_files()
    check_ui_labels()

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
