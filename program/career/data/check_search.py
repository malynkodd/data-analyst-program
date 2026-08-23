"""Проверка режима поиска (program/career/step-03.md, умение K1 и первое
условие критерия J3).

Две независимые части.

**K1** — «Читает документацию и текст вакансии без словаря; пересказывает
требования вакансии на русском, не потеряв ни одного из 2 ключевых
пунктов эталона» (часть 1 blueprint). Эталон не выдуман для шага: это
колонка «Обязательные требования» той же вакансии в research/market.md,
заполненная на Фазе 0 чтением её английского текста. Скрипт находит строку
по названию, раскладывает эталонную ячейку и пересказ учащегося на один и
тот же управляемый словарь требований и требует пересечения ≥2.

**J3, первое условие** — «трекер заполнен ≥4 недели». Считаются только
строки реальных откликов: пять учебных строк шага M14.01 помечены
статусом «приклад» и в счёт недель не идут. Эта часть до реального
поиска работы не сходится по построению — так и задумано, см. 1.7
шага 03.

Запуск:
    python program\\career\\data\\check_search.py
    python program\\career\\data\\check_search.py <vacancy_notes.md> [tracker.csv]

Код возврата 0 — все проверки прошли, 1 — есть [FAIL].
"""
import csv
import re
import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_NOTES = ROOT / "program" / "career" / "work" / "vacancy_notes.md"
MARKET = ROOT / "research" / "market.md"
TRACKER = ROOT / "program" / "M14" / "work" / "tracker.csv"

VACANCIES_REQUIRED = 5
OVERLAP_REQUIRED = 2
RETELLING_MIN_WORDS = 30
WEEKS_REQUIRED = 4

# Управляемый словарь требований. Ключ — требование, значения — формы, по
# которым оно узнаётся и в эталонной ячейке research/market.md, и в
# пересказе учащегося. Словарь закрытый намеренно: свободное сравнение
# двух текстов «на похожесть» — это не проверка с порогом.
VOCABULARY = {
    "SQL": ["sql"],
    "Python": ["python", "pandas"],
    "Power BI": ["power bi", "powerbi"],
    "Tableau": ["tableau"],
    "Excel": ["excel"],
    "Looker": ["looker"],
    "облачный DWH": ["bigquery", "snowflake", "redshift", "databricks"],
    "dbt": ["dbt"],
    "статистика": ["статист", "statistic", "регресс", "regression", "hypothesis"],
    "A/B": ["a/b", "a-b", "а/б", "ab-test", "champion-challenger"],
    "дашборды": ["дашборд", "dashboard", "визуализац"],
    "коммуникация": [
        "коммуникац", "communication", "стейкхолдер", "stakeholder", "client-facing",
    ],
    "диплом": ["bachelor", "master", "degree", "диплом", "quant"],
    "опыт в годах": ["год", "лет", "year"],
    "ML": ["scikit", "machine learning", "ml-"],
}

HEADER_CELL = "Обязательные требования"
LINK_TITLE = re.compile(r"\[([^\]]+)\]\(")
WORD = re.compile(r"[^\W\d_]+", re.UNICODE)

FAILED = False


def ok(msg: str) -> None:
    print(f"[OK]   {msg}")


def bad(msg: str) -> None:
    global FAILED
    FAILED = True
    print(f"[FAIL] {msg}")


def tokens(text: str) -> set[str]:
    low = text.lower()
    return {name for name, forms in VOCABULARY.items() if any(f in low for f in forms)}


def market_requirements() -> dict[str, str]:
    """Название вакансии -> ячейка «Обязательные требования». Разбирается
    любая таблица research/market.md, у которой есть такая колонка: их
    несколько, и номер колонки в них разный."""
    out: dict[str, str] = {}
    idx: int | None = None
    for line in MARKET.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            idx = None
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if HEADER_CELL in cells:
            idx = cells.index(HEADER_CELL)
            continue
        if idx is None or len(cells) <= idx:
            continue
        title = LINK_TITLE.search(cells[1] if len(cells) > 1 else "")
        if title:
            out[title.group(1).strip()] = cells[idx]
    return out


def parse_notes(text: str) -> list[tuple[str, str, str]]:
    """Блоки '## <название>' с полями «Ключевые пункты:» и «Пересказ:»."""
    blocks: list[tuple[str, str, str]] = []
    title = None
    points: list[str] = []
    retelling: list[str] = []
    field: str | None = None

    def flush() -> None:
        if title:
            blocks.append((title, " ".join(points), " ".join(retelling)))

    for line in text.splitlines():
        if line.startswith("## "):
            flush()
            title, points, retelling, field = line[3:].strip(), [], [], None
        elif line.startswith("Ключевые пункты:"):
            field = "p"
            points.append(line.split(":", 1)[1])
        elif line.startswith("Пересказ:"):
            field = "r"
            retelling.append(line.split(":", 1)[1])
        elif line.strip() and field == "p":
            points.append(line)
        elif line.strip() and field == "r":
            retelling.append(line)
    flush()
    return blocks


def check_k1(path: Path) -> None:
    if not path.exists():
        bad(f"файла нет: {path}")
        return
    blocks = parse_notes(path.read_text(encoding="utf-8"))
    if len(blocks) < VACANCIES_REQUIRED:
        bad(
            f"разобрано вакансий: {len(blocks)}, нужно {VACANCIES_REQUIRED} "
            f"(блок '## <название>' на каждую)"
        )
    else:
        ok(f"разобрано вакансий: {len(blocks)} при минимуме {VACANCIES_REQUIRED}")

    reference = market_requirements()
    ok(f"эталон: research/market.md, вакансий с колонкой «{HEADER_CELL}»: {len(reference)}")

    for title, points, retelling in blocks:
        cell = reference.get(title)
        if cell is None:
            bad(
                f"«{title}»: такой вакансии нет в research/market.md — "
                f"название блока пишется дословно, как текст ссылки в таблице"
            )
            continue
        words = len(WORD.findall(retelling))
        if words < RETELLING_MIN_WORDS:
            bad(f"«{title}»: пересказ {words} слов, минимум {RETELLING_MIN_WORDS}")
        shared = tokens(points) & tokens(cell)
        if len(shared) >= OVERLAP_REQUIRED:
            ok(f"«{title}»: совпало с эталоном {len(shared)} требований — {', '.join(sorted(shared))}")
        else:
            bad(
                f"«{title}»: совпало {len(shared)} требований при пороге "
                f"{OVERLAP_REQUIRED}; эталон называет: "
                f"{', '.join(sorted(tokens(cell))) or 'ни одного из словаря'}"
            )


def check_j3(tracker: Path) -> None:
    if not tracker.exists():
        bad(
            f"трекера нет: {tracker} — он заводится шагом M14.01, а этот шаг "
            f"его продолжает, а не создаёт заново"
        )
        return
    with tracker.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))

    real = [r for r in rows if (r.get("статус") or "").strip().lower() != "приклад"]
    if not real:
        bad(
            f"в трекере {len(rows)} строк, все учебные (статус «приклад»): "
            f"реальных откликов 0 — условие «заполнен ≥{WEEKS_REQUIRED} недели» "
            f"закрывается временем поиска, а не правкой файла"
        )
        return

    weeks = set()
    broken = []
    for r in real:
        raw = (r.get("дата") or "").strip()
        try:
            y, w, _ = date.fromisoformat(raw).isocalendar()
            weeks.add((y, w))
        except ValueError:
            broken.append(raw or "<пусто>")
    for raw in broken:
        bad(f"дата не в формате ГГГГ-ММ-ДД: {raw}")

    if len(weeks) >= WEEKS_REQUIRED:
        ok(f"трекер: {len(real)} реальных откликов в {len(weeks)} разных неделях")
    else:
        bad(
            f"трекер: {len(real)} реальных откликов в {len(weeks)} неделях, "
            f"нужно {WEEKS_REQUIRED}"
        )

    closed = [
        r for r in real
        if (r.get("geo_open") or "").strip().lower() in {"ні", "нет", "no", "ні."}
    ]
    if closed:
        bad(
            f"откликов в заведомо закрытую географию: {len(closed)} при пороге 0 "
            f"(критерий J3) — гео-фильтр M13 применяется до отклика, не после"
        )
    else:
        ok("откликов в заведомо закрытую географию: 0 при пороге 0")


def main() -> int:
    notes = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_NOTES
    tracker = Path(sys.argv[2]) if len(sys.argv) > 2 else TRACKER
    print(f"Разбор вакансий: {notes}\nТрекер: {tracker}\n")
    check_k1(notes)
    print()
    check_j3(tracker)

    print()
    if FAILED:
        print("НЕ СОШЛОСЬ. Шаг не закрыт.")
        return 1
    print("ВСЁ СОШЛОСЬ: расхождений 0.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
