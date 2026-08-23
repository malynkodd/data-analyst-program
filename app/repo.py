"""Чтение репозитория программы: дерево модулей, шаги, команды проверок,
строки отложенного.

Единственный источник содержания — файлы `program/**/step-*.md`,
`DEFERRED.md` и `research/self.md` в том виде, в каком они лежат на диске.
Ничего из них в собственный формат приложения не переносится: каждая
функция здесь читает файл в момент вызова и отдаёт разобранное
представление, которое нигде не сохраняется (`app/PLAN.md`, раздел 0).
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "program"
DEFERRED = ROOT / "DEFERRED.md"

# Порядок разделов дерева: модули натуральной сортировкой, затем проекты,
# затем блок «Выход». Тот же порядок, что в части 6.1 blueprint.
CAREER = "career"

STEP_FILE = re.compile(r"^step-(\d+)\.md$")
HEADER_FIELD = re.compile(r"^(Умение|Модуль|Требуется до этого|Время):\s*(.*)$")
SECTION = re.compile(r"^##\s+(\d+\.\d+)\.\s*(.*)$", re.MULTILINE)
BACKTICKED = re.compile(r"`([^`]+)`")

# Команда проверки внутри блока кода шага. Приглашающая `> ` (M4, M14,
# M15, M16, career) и `$ ` (M0) — часть оформления примеров, снимается.
CHECK_LINE = re.compile(r"^\s*(?:[>$]\s+)?(python3?)\s+(\S*check_\w+\.py.*)$")


def _natural_key(name: str) -> tuple[int, int, str]:
    """M0..M16 перед P1..P6, `career` последним; числа — числами."""
    if name == CAREER:
        return (2, 0, name)
    m = re.fullmatch(r"([MP])(\d+)", name)
    if not m:
        return (3, 0, name)
    return (0 if m.group(1) == "M" else 1, int(m.group(2)), name)


@dataclass
class CheckCommand:
    """Команда `check_*.py`, найденная в тексте шага."""

    index: int
    raw: str  # как написано в шаге, без приглашающей `> `
    argv: list[str]  # разобранные аргументы без слова `python`
    cwd: str | None  # рабочая папка относительно корня; None — не нашлась


@dataclass
class Step:
    module: str
    number: int
    path: Path
    title: str
    header: dict[str, str] = field(default_factory=dict)
    is_declaration: bool = False

    @property
    def step_id(self) -> str:
        return f"{self.module}/step-{self.number:02d}"

    @property
    def rel_path(self) -> str:
        return self.path.relative_to(ROOT).as_posix()


def modules() -> list[str]:
    """Папки `program/`, в которых есть хотя бы один `step-NN.md`."""
    found = []
    for d in PROGRAM.iterdir():
        if d.is_dir() and any(STEP_FILE.match(f.name) for f in d.iterdir() if f.is_file()):
            found.append(d.name)
    return sorted(found, key=_natural_key)


def steps(module: str) -> list[Step]:
    d = PROGRAM / module
    out = []
    for f in sorted(d.iterdir()):
        m = STEP_FILE.match(f.name)
        if not m:
            continue
        out.append(_read_step(module, int(m.group(1)), f))
    return sorted(out, key=lambda s: s.number)


def step(module: str, number: int) -> Step:
    path = PROGRAM / module / f"step-{number:02d}.md"
    if not path.is_file():
        raise FileNotFoundError(f"нет файла {path.relative_to(ROOT)}")
    return _read_step(module, number, path)


def _read_step(module: str, number: int, path: Path) -> Step:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    title = lines[0].lstrip("# ").strip() if lines else path.name
    header: dict[str, str] = {}
    # Шапка — первые строки до первого раздела `## `. Значение поля может
    # переноситься на следующую строку (`Время:` в M0), поэтому строка без
    # двоеточия приклеивается к последнему полю.
    last = None
    for line in lines[1:]:
        if line.startswith("## "):
            break
        m = HEADER_FIELD.match(line)
        if m:
            last = m.group(1)
            header[last] = m.group(2).strip()
        elif last and line.strip():
            header[last] = f"{header[last]} {line.strip()}"
        elif not line.strip():
            last = None
    return Step(
        module=module,
        number=number,
        path=path,
        title=title,
        header=header,
        is_declaration=(number == 0),
    )


def step_text(module: str, number: int) -> str:
    return step(module, number).path.read_text(encoding="utf-8")


def sections(text: str) -> dict[str, str]:
    """Разделы вида `## 1.5. Критерий готовности` → дословный текст.

    Ключ — номер (`1.5`), значение — заголовок и тело до следующего `## `.
    """
    out: dict[str, str] = {}
    marks = list(SECTION.finditer(text))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out[m.group(1)] = text[m.start():end].rstrip()
    return out


def plan_hours(header: dict[str, str]) -> str:
    """План часов — дословно из шапки `Время:`, без пересчёта.

    `Время: 6–8 ч` → `6–8`; `Время: 3 ч` → `3`; пояснение в скобках
    («оценка проектная, не измерена») отбрасывается — оно не число.
    """
    raw = header.get("Время", "").strip()
    if not raw:
        return "—"
    m = re.match(r"^([\d.,]+(?:\s*[–—-]\s*[\d.,]+)?)\s*ч", raw)
    if not m:
        return "—"
    return re.sub(r"\s*([–—-])\s*", r"\1", m.group(1))


def check_commands(module: str, text: str) -> list[CheckCommand]:
    """Команды `check_*.py` из блоков кода шага, в порядке появления.

    Приложение выполняет только то, что написано в самом шаге: клиент
    присылает номер команды, а не строку (`app/PLAN.md`, раздел 3).
    """
    out: list[CheckCommand] = []
    seen: set[str] = set()
    in_fence = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            continue
        m = CHECK_LINE.match(line)
        if not m:
            continue
        raw = f"{m.group(1)} {m.group(2)}".strip()
        if raw in seen:
            continue
        seen.add(raw)
        argv = [a.strip('"') for a in shlex.split(m.group(2), posix=False)]
        out.append(CheckCommand(index=len(out), raw=raw, argv=argv, cwd=_resolve_cwd(module, argv)))
    return out


def _resolve_cwd(module: str, argv: list[str]) -> str | None:
    """Рабочая папка команды: корень репозитория или `program/<модуль>/data`.

    Два правила и ни одного третьего (`app/PLAN.md`, раздел 3). Путь в
    шагах M4/M14/M15/M16/career написан от корня; в M0 — относительный,
    потому что шаг велит перейти в папку скрипта.
    """
    if not argv:
        return None
    script = argv[0].replace("\\", "/")
    if (ROOT / script).is_file():
        return "."
    data_dir = PROGRAM / module / "data"
    if (data_dir / Path(script).name).is_file():
        return (data_dir.relative_to(ROOT)).as_posix()
    return None


# ---------------------------------------------------------------- DEFERRED


@dataclass
class DeferredRow:
    section: str
    what: str
    where: str
    paths: list[str]


@lru_cache(maxsize=1)
def _deferred_rows_cached(mtime: float) -> tuple[DeferredRow, ...]:
    text = DEFERRED.read_text(encoding="utf-8")
    rows: list[DeferredRow] = []
    section_name = ""
    for line in text.splitlines():
        if line.startswith("## "):
            section_name = line[3:].strip()
            continue
        if not line.startswith("|") or re.match(r"^\|[\s:\-|]+\|?$", line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2 or cells[1] == "Где заложено":
            continue
        paths = [t for t in BACKTICKED.findall(cells[1]) if "/" in t or t.endswith((".md", ".py"))]
        rows.append(DeferredRow(section=section_name, what=cells[0], where=cells[1], paths=paths))
    return tuple(rows)


def deferred_rows() -> list[DeferredRow]:
    return list(_deferred_rows_cached(DEFERRED.stat().st_mtime))


def manual_run_rows() -> list[DeferredRow]:
    """Строки об отложенных **ручных прогонах** — разделы «Проверка ...».

    Именно они означают, что вердикт ИИ по критерию реального прогона на
    Desktop/Tableau/Looker не заменяет.
    """
    return [r for r in deferred_rows() if r.section.startswith("Проверка")]


def deferred_for(module: str, number: int | None = None) -> list[dict]:
    """Строки отложенного, привязанные к модулю или к конкретному шагу.

    Привязка — по путям из колонки «Где заложено»: `program/M15/...` даёт
    модуль, `program/M15/step-01.md` — ещё и шаг.
    """
    out = []
    step_name = f"step-{number:02d}.md" if number is not None else None
    for row in manual_run_rows():
        hit_module = False
        hit_step = False
        for p in row.paths:
            parts = p.replace("\\", "/").split("/")
            if len(parts) >= 2 and parts[0] == "program" and parts[1] == module:
                hit_module = True
                if step_name and parts[-1] == step_name:
                    hit_step = True
        if hit_module:
            out.append(
                {
                    "section": row.section,
                    "what": row.what,
                    "where": row.where,
                    "scope": "step" if hit_step else "module",
                }
            )
    return out
