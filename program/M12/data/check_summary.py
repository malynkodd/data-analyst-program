"""Проверка executive summary (умение H1, `program/M12/step-01.md`).

**Зачем скрипт вместо самопроверки.** Прежний критерий шага требовал
прочитать собственный текст, закрыть его и сформулировать рекомендацию —
она «обязана совпасть». Она совпадёт всегда: автор помнит, что написал.
Внешний аудит `audit/independent-audit-2026-08-24.md` назвал это дефектом
CG-8 — «проверка H1 не является проверкой».

Скрипт не заменяет живого читателя (он остаётся в критерии шага и
проверяет то, чего машина не видит: понятно ли). Он снимает с самооценки
всё, что можно померить, и оставляет человеку только суждение:

1. **длина** — не больше 200 слов;
2. **число** — хотя бы одно, и не в виде года;
3. **рекомендация ровно одна** — считаются предложения с формой действия
   («рекомендую», «стоит», «нужно», «предлагаю», «следует», «рекомендация:»);
4. **рекомендация стоит в первых двух предложениях** — то самое, что
   проверяет тест 60 секунд: вывод, похороненный в середине, читатель не
   найдёт;
5. **нет размытых оборотов** — «возможно», «вероятно, стоит», «в целом»,
   «как правило» рядом с рекомендацией превращают её в наблюдение;
6. **есть отметка о живом читателе** — строка вида
   `Читатель: <кто>, <дата>, рекомендация воспроизведена: да|нет`.
   Отсутствие строки — не отказ, а статус «сдано условно»: шаг закрыт с
   пометкой, и она печатается.

Запуск из корня репозитория:

    .venv\\Scripts\\python.exe program\\M12\\data\\check_summary.py program\\M12\\work\\executive_summary.md

Код возврата 0 — критерий сошёлся (возможно, условно), 1 — нет.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

MAX_WORDS = 200
RECOMMENDATION_HEAD = 2

ACTION = re.compile(
    r"\b(рекомендую|рекомендация|рекомендуем|стоит|нужно|необходимо|предлагаю|"
    r"предлагается|следует|надо)\b",
    re.IGNORECASE,
)
HEDGE = re.compile(
    r"\b(возможно|вероятно|наверное|скорее всего|в целом|как правило|в принципе)\b",
    re.IGNORECASE,
)
NUMBER = re.compile(r"\d[\d\s.,]*")
YEAR_ONLY = re.compile(r"^(19|20)\d{2}$")
READER = re.compile(
    r"^Читатель:\s*(.+?),\s*(\d{4}-\d{2}-\d{2}),\s*рекомендация воспроизведена:\s*"
    r"(да|нет)\s*$",
    re.MULTILINE | re.IGNORECASE,
)

failures: list[str] = []


def fail(message: str) -> None:
    failures.append(message)
    print("[FAIL]", message)


def ok(message: str) -> None:
    print("[OK]  ", message)


def sentences(text: str) -> list[str]:
    body = READER.sub("", text)
    body = re.sub(r"^\s*#.*$", "", body, flags=re.MULTILINE)  # заголовки
    body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)  # комментарии
    parts = re.split(r"(?<=[.!?])\s+", body.strip())
    return [s.strip() for s in parts if s.strip()]


def main() -> int:
    if len(sys.argv) != 2:
        print("нужен один аргумент: путь к executive summary")
        return 1
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"нет файла {path}")
        return 1
    text = path.read_text(encoding="utf-8")

    body = READER.sub("", text)
    words = [w for w in re.findall(r"[^\s]+", body) if re.search(r"\w", w)]
    if len(words) <= MAX_WORDS:
        ok(f"длина: {len(words)} слов из {MAX_WORDS}")
    else:
        fail(f"длина: {len(words)} слов, порог {MAX_WORDS}")

    numbers = [
        n.strip() for n in NUMBER.findall(body)
        if n.strip() and not YEAR_ONLY.match(n.strip())
    ]
    if numbers:
        ok(f"чисел (не годов): {len(numbers)}, первое — {numbers[0]}")
    else:
        fail("ни одного числа: без числа это мнение, а не summary")

    items = sentences(text)
    recs = [i for i, s in enumerate(items) if ACTION.search(s)]
    if len(recs) == 1:
        ok(f"рекомендация ровно одна, предложение {recs[0] + 1} из {len(items)}")
    elif not recs:
        fail("рекомендации нет: ни одного предложения с формой действия")
    else:
        fail(
            f"рекомендаций {len(recs)} (предложения "
            f"{', '.join(str(i + 1) for i in recs)}) — читателю придётся выбирать"
        )

    if recs and recs[0] < RECOMMENDATION_HEAD:
        ok(f"рекомендация в первых {RECOMMENDATION_HEAD} предложениях")
    elif recs:
        fail(
            f"рекомендация в предложении {recs[0] + 1}: за 60 секунд читатель "
            f"до неё не дойдёт — вынесите её в начало"
        )

    hedged = [i + 1 for i in recs if HEDGE.search(items[i])]
    if hedged:
        fail(
            f"размытый оборот в предложении с рекомендацией "
            f"({', '.join(map(str, hedged))}): «возможно стоит» — это наблюдение"
        )
    elif recs:
        ok("в предложении с рекомендацией нет размытых оборотов")

    reader = READER.search(text)
    print()
    if failures:
        print(f"НЕ СОШЛОСЬ: {len(failures)} проверок")
        return 1
    if reader and reader.group(3).lower() == "да":
        print(f"СОВПАДАЕТ: шаг сдан, живой читатель — {reader.group(1)}, {reader.group(2)}")
        return 0
    if reader:
        fail(
            f"живой читатель ({reader.group(1)}) рекомендацию не воспроизвёл — "
            f"переписывайте текст, а не отметку"
        )
        print("НЕ СОШЛОСЬ: 1 проверка")
        return 1
    print(
        "СДАНО УСЛОВНО: машинная часть сошлась, строки «Читатель: …» нет.\n"
        "Шаг закрыт до появления живого читателя; отметка дописывается тем же\n"
        "файлом, когда человек найдётся. Условная сдача записывается в\n"
        "research/self.md и снимается только реальным прочтением."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
