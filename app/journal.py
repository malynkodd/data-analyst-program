"""Дозапись строки сессии в `research/self.md`.

Формат берётся из самого файла — его шапка объявляет
`Дата | Тема | План (ч) | Факт (ч) | Где застрял | Что оказалось лишним`,
и приложение пишет ровно эти шесть полей. Единственная операция с файлом —
добавление строки в конец: существующие строки не читаются на предмет
правки, не перенумеровываются и не переформатируются
(`app/PLAN.md`, раздел 4; тест `tests/test_journal.py`).

Часы приложение не придумывает: «План» — дословно из шапки `Время:` шага
(`repo.plan_hours`), «Факт» — из таймера сессии (`state.py`), округлённый
вниз до 0.25 ч по правилу 1 самого файла.
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


def compose_row(
    *,
    theme: str,
    plan: str,
    fact: str,
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
    меняется и не переписывается. Строка, не разбирающаяся на шесть полей,
    отдаётся как есть — файл ведёт человек, и приложение не вправе решать,
    что его запись неправильная.
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
        if len(parts) != 6:
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
                "stuck": parts[4],
                "useless": parts[5],
                "notes": parts[4].count("[сторона]"),
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
