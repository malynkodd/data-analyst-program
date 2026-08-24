"""Объём практики: сколько заданий в разделе 1.4 каждого шага.

Метрика заимствована у Karpov.Courses (`research/competitors.md`, 3.4,
п. 9): «830+ задач» вместо «X часов контента» — часы измеряют, сколько
потрачено, задания измеряют, сколько сделано. Вторая величина честнее
и, в отличие от часов, проверяется без прохождения.

Считается верхний уровень нумерованного списка в разделе `## 1.4`
каждого содержательного шага (`step-00.md` — служебный, не считается).
Вложенные пункты и маркированные списки не считаются: задание — это то,
что сдаётся, а не то, из скольких движений оно состоит.

Раздел 1.4 без нумерованного списка, но с текстом — одно задание,
написанное прозой (`program/M1/step-01.md`, `program/M3/step-07.md`).
Это не дефект структуры: задание там одно, и нумеровать нечего.
Пустой раздел 1.4 — дефект, и он печатается как `[WARN]`.

Прогон: `.venv\\Scripts\\python.exe tools\\count_tasks.py`
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROGRAM = ROOT / "program"

TASK_HEADING = re.compile(r"^## 1\.4\.")
# Возвратные точки (program/review/) — не шаги: восьми разделов шага у них
# нет, и раздел заданий стоит под своим номером (решение 49). Заголовок
# ищется по слову, а не по номеру, потому что номер раздела отличается от
# точки к точке — у R3 перед заданиями есть раздел «Что точка сознательно
# не проверяет», у остальных нет.
REVIEW_TASK_HEADING = re.compile(r"^## \d+\. Задания")
REVIEW_DIR = "review"
NEXT_HEADING = re.compile(r"^## ")
TASK_ITEM = re.compile(r"^(\d+)\. ")

# Порядок прохождения, часть 6.2 blueprint, а не алфавит каталогов.
ORDER = [
    "M0", "M1", "M13", "M2", "M3", "M10", "P1", "P2",
    "M4", "M15", "M16", "M12", "P3", "M5", "M6", "M7", "P4",
    "M8", "M9", "M11", "P5", "M14", "P6", "career", "review",
]


def tasks_in(path: Path) -> tuple[int, bool]:
    """(сколько заданий, прозой ли). Прозой — значит одно, без нумерации."""
    heading = (
        REVIEW_TASK_HEADING if path.parent.name == REVIEW_DIR else TASK_HEADING
    )
    inside = False
    count = 0
    body = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if heading.match(line):
            inside = True
            continue
        if inside and NEXT_HEADING.match(line):
            break
        if inside:
            if TASK_ITEM.match(line):
                count += 1
            elif line.strip():
                body += 1
    if count:
        return count, False
    return (1, True) if body else (0, False)


def main() -> int:
    per_module: dict[str, list[tuple[str, int, bool]]] = {}
    for path in sorted(PROGRAM.glob("*/step-[0-9][0-9].md")):
        if path.name == "step-00.md":
            continue
        count, prose = tasks_in(path)
        per_module.setdefault(path.parent.name, []).append((path.name, count, prose))

    total = 0
    steps = 0
    prose_steps: list[str] = []
    unknown = sorted(set(per_module) - set(ORDER))
    if unknown:
        print(f"[WARN] каталоги вне порядка части 6.2: {', '.join(unknown)}")

    print(f"{'Модуль':<8} {'Шагов':>6} {'Заданий':>8}  Разбивка по шагам")
    for module in ORDER + unknown:
        rows = per_module.get(module)
        if not rows:
            continue
        n = sum(c for _, c, _ in rows)
        total += n
        steps += len(rows)
        breakdown = " ".join(f"{c}*" if p else str(c) for _, c, p in rows)
        print(f"{module:<8} {len(rows):>6} {n:>8}  {breakdown}")
        for name, c, p in rows:
            if c == 0:
                print(f"         [WARN] {module}/{name}: раздел 1.4 пуст")
            elif p:
                prose_steps.append(f"{module}/{name}")

    print()
    print(f"Всего: {steps} содержательных шагов, {total} заданий")
    if steps:
        print(f"В среднем на шаг: {total / steps:.1f}")
    if prose_steps:
        print(f"* одно задание прозой, без нумерации: {', '.join(prose_steps)}")
    print(
        "Проекты P1–P6 сюда не входят: у них нет шагов, приёмка — "
        "acceptance criteria в project.md (решение 3)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
