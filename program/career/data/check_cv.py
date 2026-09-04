"""Проверка резюме (program/career/step-01.md).

Читает program\\career\\work\\cv.md и проверяет ровно то, что объявлено
критерием готовности шага 01: объём, наличие пяти разделов, опора каждой
строки раздела «Работы» на существующий файл репозитория, число в каждой
такой строке, отсутствие формулировок без порога и подтверждение каждого
инструмента из раздела «Инструменты» строкой раздела «Работы».

Смысл главной проверки — «инструмент подтверждён работой». Утверждение
«SQL» в списке инструментов проверяется не тем, что слово написано, а
тем, что оно встречается в строке, которая ссылается на существующий
файл. Требование взято из research/access.md, §4: при оценке кандидатов
спрашивают «що саме зробив ТИ», а не какими инструментами он владеет.

Запуск:
    python program\\career\\data\\check_cv.py
    python program\\career\\data\\check_cv.py <путь к другому cv.md>

Код возврата 0 — все проверки прошли, 1 — есть [FAIL].
"""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CV = ROOT / "program" / "career" / "work" / "cv.md"

# Пять разделов резюме в том порядке, в котором их объявляет шаг 01.
REQUIRED_SECTIONS = [
    "Чем могу быть полезен",
    "Инструменты",
    "Работы",
    "Английский",
    "Контакты",
]

# Верхняя граница объёма: одна страница. 450 слов — не круглое число «на
# глаз», а замер: шаблон шага 01 с шестью строками «Работ» и заполненными
# разделами даёт 268 слов (см. reference_answers.md), запас — на седьмую
# и восьмую строку и на более длинные названия проектов.
MAX_WORDS = 450

# Минимум строк в разделе «Работы»: шесть проектов портфолио P1–P6.
MIN_WORK_LINES = 6

# Формулировки, которые нельзя проверить порогом. Первые шесть — список
# раздела 5 скилла curriculum-design (там он запрещает их в тексте шага;
# в резюме они запрещены по той же причине). Последние три — оценочные
# самохарактеристики: они не опираются ни на какой артефакт и потому
# противоречат самой конструкции этого резюме.
UNCHECKABLE = [
    "понимает", "понимаю", "знает основ", "знаю основ",
    "умеет работать", "умею работать", "имею представление",
    "имеет представление", "освоил", "разбираюсь в", "разбирается в",
    "ответственный", "коммуникабельный", "стрессоустойчив",
]

# Инструменты, которые резюме может назвать. Ключ — как пишется в разделе
# «Инструменты», значения — формы, по которым инструмент засчитывается
# найденным в разделе «Работы» (регистр не важен).
TOOL_FORMS = {
    "SQL": ["sql", "postgres", "sqlite", "запрос"],
    "Python": ["python", "pandas", ".py"],
    "Power BI": ["power bi", "powerbi", "dax", "power query", "pbix", "pbip"],
    "Excel": ["excel", "sheets", "сводн"],
    "BigQuery": ["bigquery", "bq"],
    "Tableau": ["tableau", "twb"],
    "Looker Studio": ["looker"],
    "Git": ["git", "коммит", "ветк"],
}

NUMBER = re.compile(r"\d")
# Путь к артефакту: program\... или program/... до пробела, запятой или
# обрамления markdown (обратная кавычка, звёздочка). Без исключения кавычки
# путь внутри `program\P1\data\reference_answers.md` захватывает её в конец и
# «не находится» при существующем файле.
PATH_TOKEN = re.compile(r"program[\\/][^\s,;)`*]+")
CEFR = re.compile(r"\b(A1|A2|B1|B2|C1|C2)\b")

FAILED = False


def ok(msg: str) -> None:
    print(f"[OK]   {msg}")


def bad(msg: str) -> None:
    global FAILED
    FAILED = True
    print(f"[FAIL] {msg}")


def split_sections(text: str) -> dict[str, list[str]]:
    """Разбор по заголовкам '## '. Возвращает заголовок -> строки тела."""
    out: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            out[current] = []
        elif current is not None:
            out[current].append(line)
    return out


def check_volume(text: str) -> None:
    words = len([w for w in re.split(r"\s+", text) if w])
    if words <= MAX_WORDS:
        ok(f"объём {words} слов при пороге {MAX_WORDS} (одна страница)")
    else:
        bad(
            f"объём {words} слов, порог {MAX_WORDS}: резюме длиннее одной "
            f"страницы — резать раздел «Чем могу быть полезен», не «Работы»"
        )


def check_sections(sections: dict[str, list[str]]) -> None:
    missing = [s for s in REQUIRED_SECTIONS if s not in sections]
    if missing:
        bad(f"нет разделов: {', '.join(missing)}")
    else:
        ok(f"все {len(REQUIRED_SECTIONS)} разделов на месте")


def work_lines(sections: dict[str, list[str]]) -> list[str]:
    """Одна запись — один пункт списка вместе с его продолжениями.

    Пункт резюме переносится на вторую строку сплошь и рядом, и путь к
    артефакту чаще всего оказывается именно на ней. Проверка построчно
    объявляла бы такой пункт «без ссылки на файл» при наличии ссылки:
    измерено на эталонном резюме — 5 ложных [FAIL] из 6 пунктов."""
    entries: list[str] = []
    for line in sections.get("Работы", []):
        stripped = line.strip()
        if stripped.startswith("-"):
            entries.append(stripped)
        elif stripped and entries:
            entries[-1] += " " + stripped
    return entries


def check_works(lines: list[str]) -> set[str]:
    """Проверяет строки раздела «Работы» и возвращает их текст в нижнем
    регистре — по нему потом проверяются инструменты."""
    if len(lines) < MIN_WORK_LINES:
        bad(
            f"в разделе «Работы» {len(lines)} строк, нужно {MIN_WORK_LINES} — "
            f"по одной на проект портфолио P1–P6"
        )
    else:
        ok(f"в разделе «Работы» {len(lines)} строк при минимуме {MIN_WORK_LINES}")

    no_number = [ln for ln in lines if not NUMBER.search(ln)]
    for ln in no_number:
        bad(f"строка «Работ» без единого числа: {ln[:70]}")
    if lines and not no_number:
        ok(f"во всех {len(lines)} строках «Работ» есть число")

    checked_paths = 0
    absent_paths = 0
    for ln in lines:
        paths = PATH_TOKEN.findall(ln)
        if not paths:
            bad(f"строка «Работ» не ссылается ни на один файл: {ln[:70]}")
            continue
        for raw in paths:
            rel = raw.replace("\\", "/")
            if (ROOT / rel).exists():
                checked_paths += 1
            else:
                absent_paths += 1
                bad(f"файла нет в репозитории: {raw}")
    # Слово «все» обязано означать все. До 2026-09-04 счётчик рос только на
    # существующих путях, и строка печаталась при любом ненулевом их числе:
    # три [FAIL] «файла нет» и следом [OK] «все названные артефакты
    # существуют, проверено путей: 3» (audit/final-audit-2026-09-03.md, F3).
    if checked_paths and not absent_paths:
        ok(f"все названные артефакты существуют, проверено путей: {checked_paths}")

    return {ln.lower() for ln in lines}


def check_tools(sections: dict[str, list[str]], works: set[str]) -> None:
    body = " ".join(sections.get("Инструменты", [])).lower()
    named = [name for name, forms in TOOL_FORMS.items() if forms[0] in body]
    if not named:
        bad(
            "раздел «Инструменты» не назвал ни одного инструмента из списка "
            f"{', '.join(TOOL_FORMS)}"
        )
        return
    haystack = " ".join(works)
    unconfirmed = []
    for name in named:
        if not any(form in haystack for form in TOOL_FORMS[name]):
            unconfirmed.append(name)
    for name in unconfirmed:
        bad(
            f"инструмент «{name}» назван, но ни одна строка «Работ» его не "
            f"подтверждает: назвать работу, где он применён, или убрать из списка"
        )
    if not unconfirmed:
        ok(f"все {len(named)} названных инструментов подтверждены строкой «Работ»")


def check_english(sections: dict[str, list[str]]) -> None:
    body = "\n".join(sections.get("Английский", []))
    level = CEFR.search(body)
    if not level:
        bad("раздел «Английский» не называет уровень по шкале CEFR (A1..C2)")
    paths = PATH_TOKEN.findall(body)
    existing = [p for p in paths if (ROOT / p.replace("\\", "/")).exists()]
    if not existing:
        bad(
            "уровень английского не подкреплён артефактом: раздел обязан "
            "ссылаться на существующий файл (summary_en.md шага 02)"
        )
    if level and existing:
        ok(f"английский: уровень {level.group(1)}, подтверждение — {existing[0]}")


def check_unverifiable(text: str) -> None:
    low = text.lower()
    hits = [p for p in UNCHECKABLE if p in low]
    for p in hits:
        bad(f"формулировка без порога: {p!r} — заменить строкой с числом и артефактом")
    if not hits:
        ok(f"формулировок без порога не найдено, проверено {len(UNCHECKABLE)} форм")


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CV
    if not path.exists():
        bad(f"файла нет: {path}")
        print("\nНЕ СОШЛОСЬ: 1 проверка. Шаг не закрыт.")
        return 1

    text = path.read_text(encoding="utf-8")
    print(f"Резюме: {path}\n")

    sections = split_sections(text)
    check_volume(text)
    check_sections(sections)
    works = check_works(work_lines(sections))
    check_tools(sections, works)
    check_english(sections)
    check_unverifiable(text)

    print()
    if FAILED:
        print("НЕ СОШЛОСЬ. Шаг не закрыт.")
        return 1
    print("ВСЁ СОШЛОСЬ: расхождений 0.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
