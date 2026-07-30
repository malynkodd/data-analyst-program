"""Проверки согласованности между CLAUDE.md, design/blueprint.md и program/.

Запуск: python tools/check_consistency.py
Код возврата: 0, если все проверки прошли; 1, если найдена хотя бы одна
проблема. Ничего не изменяет в репозитории, только читает и печатает отчёт.
"""

from __future__ import annotations

import re
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
    "освоил", "разбирается", "давайте", "попробуем", "не пугайтесь",
    "главное", "!",
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


def check_skill_coverage(blueprint_text: str) -> None:
    part1 = section(blueprint_text, "# ЧАСТЬ 1.", "# ЧАСТЬ 2.")
    ids = sorted(set(re.findall(r"^\| ([A-J]\d) \|", part1, re.MULTILINE)))
    if not ids:
        fail("часть 1 blueprint: не найдено ни одного ID умения")
        return
    ok(f"часть 1: найдено {len(ids)} умений ({ids[0]}..{ids[-1]})")

    if not PROGRAM_DIR.exists():
        fail("program/ не существует — покрытие умений проверить нечем")
        return

    step_files = list(PROGRAM_DIR.rglob("*.md"))
    corpus = "\n".join(f.read_text(encoding="utf-8") for f in step_files)

    missing = [i for i in ids if not re.search(rf"\b{re.escape(i)}\b", corpus)]
    if missing:
        fail(f"умения без единого упоминания в program/**/*.md: {', '.join(missing)}")
    else:
        ok(f"все {len(ids)} умений упомянуты хотя бы в одном файле program/")


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


CODE_FENCE = re.compile(r"```.*?\n(.*?)```", re.DOTALL)


def check_forbidden(text_files: list[Path]) -> None:
    """Запрещённые слова — по всему тексту шага (решение из SKILL.md).
    POSIX-команды — только внутри блоков кода: решение 13 запрещает давать
    их учащемуся как команду для запуска, а не упоминать в прозе (сам файл
    решения 13 объясняет peek_clients.py как замену `grep`+`awk`)."""
    any_hit = False
    for f in text_files:
        rel = f.relative_to(ROOT)
        text = f.read_text(encoding="utf-8")
        for phrase in FORBIDDEN_PHRASES:
            hay = text.lower() if phrase.isalpha() else text
            needle = phrase.lower() if phrase.isalpha() else phrase
            if needle in hay:
                any_hit = True
                fail(f"{rel}: запрещённая формулировка/символ {phrase!r}")

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
    check_skill_coverage(blueprint_text)
    check_step00(blueprint_text)

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
