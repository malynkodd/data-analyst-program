"""Проверка GitHub-профиля портфолио и английского резюме анализа
(program/career/step-02.md, умение K2).

Читает три файла из program\\career\\work:

    portfolio_readme.md  — карточки шести проектов P1–P6
    summary_ru.md        — резюме одного анализа на русском
    summary_en.md        — оно же на английском

Главная проверка — вторая половина критерия K2 части 1 blueprint:
«Обратный перевод не теряет ни одного числа и ни одного вывода».
Числа сравниваются как мультимножества: 14.7 дважды в русском тексте и
один раз в английском — расхождение, а не совпадение. Это то немногое в
переводе, что проверяется механически, без второго человека.

Запуск:
    python program\\career\\data\\check_portfolio.py
    python program\\career\\data\\check_portfolio.py <папка с тремя файлами>

Код возврата 0 — все проверки прошли, 1 — есть [FAIL].
"""
import re
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DIR = ROOT / "program" / "career" / "work"

PROJECTS = ["P1", "P2", "P3", "P4", "P5", "P6"]
CARD_FIELDS = ["Задача:", "Данные:", "Что сделал я:", "Результат:"]

# 150 слов — формулировка умения K2, и она про **английский** текст.
# Допуск ±10 слов: точное попадание в 150 не проверяет ничего, кроме
# терпения, а порядок объёма — проверяет.
WORDS_MIN, WORDS_MAX = 140, 160

# Русскому исходнику тот же коридор не задаётся: измерено на эталонной
# паре — 127 слов по-русски против 165 по-английски при одном и том же
# содержании и одних и тех же 14 числах. Русский плотнее, и общий коридор
# заставлял бы дописывать воду в один из двух текстов. От исходника
# требуется только, чтобы он был полноценным текстом, а не подстрочником.
RU_WORDS_MIN = 90

# Доля слов латиницей в английском тексте. Не 100%: имя реестра ЄДР и
# названия украинских источников в английском тексте остаются кириллицей —
# это не русский текст, а термин, который не переводится.
LATIN_SHARE_MIN = 0.90

PATH_TOKEN = re.compile(r"program[\\/][^\s,;)`*]+")
NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
THOUSAND_GAP = re.compile(r"(?<=\d)[  ](?=\d)")
LATIN_WORD = re.compile(r"^[A-Za-z][A-Za-z'\-]*$")
WORD = re.compile(r"[^\W\d_]+", re.UNICODE)

FAILED = False


def ok(msg: str) -> None:
    print(f"[OK]   {msg}")


def bad(msg: str) -> None:
    global FAILED
    FAILED = True
    print(f"[FAIL] {msg}")


def numbers(text: str) -> Counter:
    """Мультимножество чисел текста. Пробел между цифрами — разделитель
    разрядов (100 889 609.46), а не граница двух чисел."""
    flat = THOUSAND_GAP.sub("", text)
    return Counter(n.replace(",", ".") for n in NUMBER.findall(flat))


def word_count(text: str) -> int:
    return len(WORD.findall(text))


def read(path: Path) -> str | None:
    if not path.exists():
        bad(f"файла нет: {path}")
        return None
    return path.read_text(encoding="utf-8")


def check_cards(text: str) -> None:
    """Шесть карточек проектов, у каждой — четыре поля, число в
    «Результат» и существующий путь к артефакту."""
    blocks: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            head = line[3:].strip()
            current = next((p for p in PROJECTS if head.startswith(p)), None)
            if current:
                blocks[current] = []
        elif current is not None:
            blocks[current].append(line)

    missing = [p for p in PROJECTS if p not in blocks]
    if missing:
        bad(f"нет карточек проектов: {', '.join(missing)}")
    else:
        ok(f"все {len(PROJECTS)} карточек проектов на месте")

    for name in PROJECTS:
        body = "\n".join(blocks.get(name, []))
        if not body.strip():
            continue
        absent = [f for f in CARD_FIELDS if f not in body]
        if absent:
            bad(f"{name}: нет полей карточки: {', '.join(absent)}")
            continue
        result_line = next(
            (ln for ln in body.splitlines() if ln.strip().startswith("Результат:")), ""
        )
        if not NUMBER.search(result_line):
            bad(f"{name}: в поле «Результат» нет числа — назван факт без величины")
        paths = PATH_TOKEN.findall(body)
        existing = [p for p in paths if (ROOT / p.replace("\\", "/")).exists()]
        if not existing:
            bad(f"{name}: карточка не ссылается ни на один существующий файл")

    done = [
        p for p in PROJECTS
        if p in blocks and all(f in "\n".join(blocks[p]) for f in CARD_FIELDS)
    ]
    if len(done) == len(PROJECTS):
        ok(f"у всех {len(PROJECTS)} карточек заполнены поля {', '.join(CARD_FIELDS)}")


def check_volume_en(text: str) -> None:
    n = word_count(text)
    if WORDS_MIN <= n <= WORDS_MAX:
        ok(f"summary_en.md: {n} слов, укладывается в {WORDS_MIN}{chr(0x2013)}{WORDS_MAX}")
    else:
        bad(f"summary_en.md: {n} слов, нужно {WORDS_MIN}{chr(0x2013)}{WORDS_MAX}")


def check_volume_ru(text: str) -> None:
    n = word_count(text)
    if n >= RU_WORDS_MIN:
        ok(f"summary_ru.md: {n} слов при минимуме {RU_WORDS_MIN}")
    else:
        bad(
            f"summary_ru.md: {n} слов, минимум {RU_WORDS_MIN} — исходник короче "
            f"перевода означает, что переводился не он"
        )


def check_latin(text: str) -> None:
    words = WORD.findall(text)
    if not words:
        bad("summary_en.md: ни одного слова")
        return
    latin = sum(1 for w in words if LATIN_WORD.match(w))
    share = latin / len(words)
    if share >= LATIN_SHARE_MIN:
        ok(f"summary_en.md: доля слов латиницей {share:.0%} при пороге {LATIN_SHARE_MIN:.0%}")
    else:
        bad(
            f"summary_en.md: доля слов латиницей {share:.0%}, порог "
            f"{LATIN_SHARE_MIN:.0%} — текст не переведён целиком"
        )


def check_numbers(ru: str, en: str) -> None:
    a, b = numbers(ru), numbers(en)
    lost = a - b
    added = b - a
    for value, count in sorted(lost.items()):
        bad(f"число {value} есть в summary_ru.md ({count} раз) и потеряно в summary_en.md")
    for value, count in sorted(added.items()):
        bad(f"число {value} есть в summary_en.md ({count} раз), но не в summary_ru.md")
    if not lost and not added:
        ok(f"числа сходятся: {sum(a.values())} вхождений, расхождение 0")


def check_recommendation(ru: str, en: str) -> None:
    """«Не теряет ни одного вывода» проверяется тем, что вывод помечен и
    есть в обоих текстах. Помечен — значит его нельзя потерять молча."""
    has_ru = "Рекомендация:" in ru
    has_en = "Recommendation:" in en
    if has_ru and has_en:
        ok("вывод помечен в обоих текстах: «Рекомендация:» и «Recommendation:»")
        return
    if not has_ru:
        bad("summary_ru.md: нет строки, начинающейся с «Рекомендация:»")
    if not has_en:
        bad("summary_en.md: нет строки, начинающейся с «Recommendation:»")


def main() -> int:
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DIR
    print(f"Папка: {base}\n")

    readme = read(base / "portfolio_readme.md")
    ru = read(base / "summary_ru.md")
    en = read(base / "summary_en.md")

    if readme is not None:
        check_cards(readme)
    if ru is not None:
        check_volume_ru(ru)
    if en is not None:
        check_volume_en(en)
        check_latin(en)
    if ru is not None and en is not None:
        check_numbers(ru, en)
        check_recommendation(ru, en)

    print()
    if FAILED:
        print("НЕ СОШЛОСЬ. Шаг не закрыт.")
        return 1
    print("ВСЁ СОШЛОСЬ: расхождений 0.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
