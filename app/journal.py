"""Дозапись строки сессии в `research/self.md`.

Формат берётся из самого файла — его шапка объявляет
`Дата | Тема | План (ч) | Факт (ч) | Факт: задания (ч) | Где застрял |
Что оказалось лишним`, и приложение пишет ровно эти семь полей.
Единственная операция с файлом —
добавление строки в конец: существующие строки не читаются на предмет
правки, не перенумеровываются и не переформатируются
(`app/PLAN.md`, раздел 4; тест `tests/test_journal.py`).

Часы приложение не придумывает: «План» — дословно из шапки `Время:` шага
(`repo.plan_hours`), «Факт» — из таймера сессии (`state.py`), округлённый
вниз до 0.25 ч по правилу 1 самого файла.

«Факт: задания» таймером не измеряется и не выводится из него: приложение
не знает, читал человек теорию или правил свой код. Число вводится
автором в форме завершения сессии и не может превышать «Факт» — правило
1a файла называет его частью факта, а не добавкой. Колонка добавлена
2026-08-24 (решение 44); строки из шести полей — записи до этой даты,
`records()` читает их как есть и «Факт: задания» им не приписывает.
"""

from __future__ import annotations

import re
from datetime import date as _date
from pathlib import Path

from repo import ROOT

SELF_MD = ROOT / "research" / "self.md"

# Пустое поле в файле обозначено длинным тире — так выглядит единственная
# существующая запись, и приложение пишет так же.
EMPTY = "—"

# Разделитель колонок. Вертикальная черта внутри текста автора сломала бы
# разбор строки на шесть полей, поэтому в полях она заменяется дробью.
SEP = " | "


def floor_quarter(seconds: float) -> float:
    """Часы из секунд, вниз до 0.25 — правило 1 `research/self.md`.

    Вниз, а не к ближайшему: правило прямо требует округления в меньшую
    сторону, потому что восстановленное время систематически завышается.
    """
    return int(seconds / 900.0) * 0.25


def format_hours(hours: float) -> str:
    """`2.75`, `3`, `0` — без хвостовых нулей, точкой как в файле."""
    text = f"{hours:.2f}".rstrip("0").rstrip(".")
    return text or "0"


def _cell(value: str | None) -> str:
    if value is None:
        return EMPTY
    text = " ".join(str(value).replace("|", "/").split())
    return text or EMPTY


def clamp_tasks(value: str | None, fact: str) -> str | None:
    """«Факт: задания» как число, не больше «Факта». Иначе — None.

    Правило 1a `research/self.md`: задания — часть факта. Значение больше
    факта означает описку, и записывать её нельзя: калибровка вилок
    считает по этой колонке. Нечисловой ввод отбрасывается так же молча —
    поле необязательное, пустое поле законно.
    """
    if value is None:
        return None
    text = str(value).strip().replace(",", ".")
    if not text:
        return None
    try:
        hours_value = float(text)
    except ValueError:
        return None
    if hours_value < 0:
        return None
    try:
        limit = float(fact)
    except (TypeError, ValueError):
        limit = None
    if limit is not None and hours_value > limit:
        hours_value = limit
    return format_hours(hours_value)


def compose_row(
    *,
    theme: str,
    plan: str,
    fact: str,
    fact_tasks: str | None = None,
    stuck: str | None = None,
    useless: str | None = None,
    notes: list[str] | None = None,
    day: _date | None = None,
) -> str:
    """Собирает строку журнала, не касаясь файла.

    `notes` — пометки правила 6 («обращение на сторону»), накопленные за
    сессию. Они идут в начало поля «Где застрял», по одной, перед текстом
    автора: правило требует отдельной пометки на каждое обращение, а не
    сводки.

    `fact_tasks` — правило 1a: часть факта, ушедшая на задания. Пустое
    поле пишется как «—»: пропуск законен, выдумывать число нельзя.
    """
    day = day or _date.today()
    parts = [_cell(n) for n in (notes or [])]
    if stuck and stuck.strip():
        parts.append(_cell(stuck))
    stuck_cell = "; ".join(parts) if parts else EMPTY
    return SEP.join(
        [
            day.isoformat(),
            _cell(theme),
            _cell(plan),
            _cell(fact),
            _cell(clamp_tasks(fact_tasks, fact)),
            stuck_cell,
            _cell(useless),
        ]
    )


def append_row(row: str, path: Path | None = None) -> str:
    """Дописывает готовую строку в конец файла и возвращает её.

    Файл читается целиком только чтобы узнать, заканчивается ли он
    переводом строки. Ничего, кроме дописанного хвоста, не меняется.
    """
    target = path or SELF_MD
    old = target.read_text(encoding="utf-8")
    tail = "" if old.endswith("\n") else "\n"
    with target.open("a", encoding="utf-8", newline="") as fh:
        fh.write(f"{tail}{row}\n")
    return row


def append_session(
    *,
    theme: str,
    plan: str,
    fact_seconds: float,
    fact_tasks: str | None = None,
    stuck: str | None = None,
    useless: str | None = None,
    notes: list[str] | None = None,
    day: _date | None = None,
    path: Path | None = None,
) -> str:
    row = compose_row(
        theme=theme,
        plan=plan,
        fact=format_hours(floor_quarter(fact_seconds)),
        fact_tasks=fact_tasks,
        stuck=stuck,
        useless=useless,
        notes=notes,
        day=day,
    )
    return append_row(row, path=path)


def tail(lines: int = 12, path: Path | None = None) -> list[str]:
    """Последние строки журнала — подтверждение записи в интерфейсе."""
    target = path or SELF_MD
    return target.read_text(encoding="utf-8").splitlines()[-lines:]


RECORDS_HEADING = "## Записи"


def records(path: Path | None = None) -> list[dict]:
    """Строки раздела «Записи» — только чтение, для экрана журнала.

    Разбор нужен, чтобы показать план против факта; сам файл при этом не
    меняется и не переписывается. Строка, не разбирающаяся ни на семь, ни
    на шесть полей, отдаётся как есть — файл ведёт человек, и приложение
    не вправе решать, что его запись неправильная.

    Шесть полей — формат до решения 44 (2026-08-24). Такие строки читаются
    без «Факт: задания»: приписать им число задним числом нельзя, его
    никто не мерил.
    """
    target = path or SELF_MD
    text = target.read_text(encoding="utf-8")
    if RECORDS_HEADING not in text:
        return []
    body = text.split(RECORDS_HEADING, 1)[1]
    out: list[dict] = []
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) == 7:
            fact_tasks, stuck, useless = parts[4], parts[5], parts[6]
        elif len(parts) == 6:
            # Формат до решения 44: колонки «Факт: задания» в строке нет.
            fact_tasks, stuck, useless = EMPTY, parts[4], parts[5]
        else:
            out.append({"raw": line, "parsed": False})
            continue
        out.append(
            {
                "raw": line,
                "parsed": True,
                "date": parts[0],
                "theme": parts[1],
                "plan": parts[2],
                "fact": parts[3],
                "fact_tasks": fact_tasks,
                "stuck": stuck,
                "useless": useless,
                "notes": stuck.count("[сторона]"),
                "checks": stuck.count("[проверка]"),
            }
        )
    return out


def hours(value: str) -> float | None:
    """`3.75` → 3.75; `6–8` → среднее; `—` → None.

    Середина вилки — не «настоящий план», а способ сложить столбец. Там,
    где это важно, интерфейс показывает саму вилку, а не это число.
    """
    value = (value or "").strip().replace(",", ".")
    if not value or value == EMPTY:
        return None
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", value)]
    if not nums:
        return None
    return sum(nums) / len(nums)
