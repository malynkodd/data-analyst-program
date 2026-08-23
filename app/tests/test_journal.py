"""Дозапись в `research/self.md` не портит существующие строки.

Журнал самопрохождения — единственный файл программы, в который пишет
приложение, и единственное, что калибрует 17 часовых вилок части 6.1
blueprint. Испорченная им строка — потерянное измерение, восстановить
которое нечем: повторно пройти шаг «в первый раз» нельзя.

Проверяется на копии настоящего файла: всё содержимое до последней строки
обязано совпасть побайтно, а прибавиться обязана ровно одна строка.
"""

from __future__ import annotations

import shutil
from datetime import date

import pytest

import journal


@pytest.fixture()
def journal_copy(tmp_path):
    """Копия настоящего research/self.md — со всеми правилами и записями."""
    target = tmp_path / "self.md"
    shutil.copy2(journal.SELF_MD, target)
    return target


def test_append_keeps_every_existing_line(journal_copy) -> None:
    before = journal_copy.read_text(encoding="utf-8")
    before_lines = before.splitlines()

    journal.append_session(
        theme="M4.05 подмена источника параметром",
        plan="6–8",
        fact_seconds=3 * 3600 + 50 * 60,
        stuck="параметр не подхватился в пятом запросе",
        useless="повторная генерация датасета",
        notes=["[сторона] ассистент: где в TMDL живут выражения запросов"],
        day=date(2026, 8, 23),
        path=journal_copy,
    )

    after_lines = journal_copy.read_text(encoding="utf-8").splitlines()
    assert after_lines[: len(before_lines)] == before_lines
    assert len(after_lines) == len(before_lines) + 1


def test_appended_row_has_six_fields_of_the_file_format(journal_copy) -> None:
    row = journal.append_session(
        theme="M4.05",
        plan="6–8",
        fact_seconds=3 * 3600 + 50 * 60,
        stuck=None,
        useless=None,
        notes=None,
        day=date(2026, 8, 23),
        path=journal_copy,
    )
    fields = [f.strip() for f in row.split("|")]
    assert len(fields) == 6
    assert fields[0] == "2026-08-23"
    assert fields[2] == "6–8"          # план — дословно из шапки «Время:»
    assert fields[3] == "3.75"         # факт — вниз до 0.25 (правило 1 файла)
    assert fields[4] == "—" and fields[5] == "—"
    assert journal_copy.read_text(encoding="utf-8").splitlines()[-1] == row


def test_hours_are_floored_to_quarter_not_rounded() -> None:
    """Правило 1 файла: округление вниз, потому что память завышает время."""
    assert journal.floor_quarter(3599) == 0.75      # 59:59 — не час
    assert journal.floor_quarter(900) == 0.25
    assert journal.floor_quarter(899) == 0.0
    assert journal.format_hours(journal.floor_quarter(2 * 3600)) == "2"


def test_pipe_in_free_text_cannot_break_the_row(journal_copy) -> None:
    row = journal.append_session(
        theme="M3.04",
        plan="4–5",
        fact_seconds=3600,
        stuck="запрос с | в тексте",
        useless=None,
        day=date(2026, 8, 23),
        path=journal_copy,
    )
    assert len([f for f in row.split("|")]) == 6


def test_notes_go_into_stuck_column_one_by_one(journal_copy) -> None:
    """Правило 6: отдельная пометка на каждое обращение, а не сводка."""
    row = journal.compose_row(
        theme="M5.03",
        plan="6–8",
        fact="2.5",
        stuck="pandas merge по двум ключам",
        notes=[
            "[сторона] ассистент: чем how='left' отличается от how='inner'",
            "[сторона] вердикт ИИ по критерию 1.5 (не скрипт): задание 7 → не сошлось",
        ],
    )
    stuck = row.split("|")[4]
    assert stuck.count("[сторона]") == 2
    assert "pandas merge" in stuck


def test_records_read_the_file_without_touching_it(journal_copy) -> None:
    """Экран журнала только читает: файл после разбора байт в байт тот же."""
    before = journal_copy.read_bytes()
    rows = journal.records(path=journal_copy)
    assert journal_copy.read_bytes() == before

    assert rows, "раздел «Записи» не разобран"
    first = rows[0]
    assert first["parsed"] and first["date"] == "2026-07-29"
    assert first["plan"] == "—" and first["fact"] == "—"


def test_records_see_a_row_written_by_the_app(journal_copy) -> None:
    journal.append_session(
        theme="M4.05 подмена источника",
        plan="6–8",
        fact_seconds=2 * 3600,
        stuck="параметр не подхватился",
        useless=None,
        notes=["[сторона] ассистент: где живут выражения запросов",
               "[сторона] вердикт ИИ по критерию 1.5 (не скрипт): задание 13 → не сошлось"],
        day=date(2026, 8, 24),
        path=journal_copy,
    )
    last = journal.records(path=journal_copy)[-1]
    assert last["parsed"] and last["date"] == "2026-08-24"
    assert last["plan"] == "6–8" and last["fact"] == "2"
    assert last["notes"] == 2, "пометки правила 6 не сосчитаны"
    assert last["useless"] == "—"


def test_hours_folds_a_range_but_keeps_a_number(journal_copy) -> None:
    assert journal.hours("6–8") == 7.0
    assert journal.hours("3.75") == 3.75
    assert journal.hours("2,5") == 2.5
    assert journal.hours("—") is None
    assert journal.hours("") is None


def test_unparsable_line_is_returned_as_is(tmp_path) -> None:
    """Журнал ведёт человек: приложение не решает, что его строка неверна."""
    f = tmp_path / "self.md"
    f.write_text("## Записи\n\nсвободная заметка без колонок\n", encoding="utf-8")
    rows = journal.records(path=f)
    assert rows == [{"raw": "свободная заметка без колонок", "parsed": False}]
