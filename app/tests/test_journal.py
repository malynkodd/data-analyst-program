"""Дозапись в `research/self.md` не портит существующие строки.

Журнал самопрохождения — единственный файл программы, в который пишет
приложение, и единственное, что калибрует 19 часовых вилок части 6.1
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


def test_appended_row_has_seven_fields_of_the_file_format(journal_copy) -> None:
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
    assert len(fields) == 7             # седьмая колонка — решение 44
    assert fields[0] == "2026-08-23"
    assert fields[2] == "6–8"          # план — дословно из шапки «Время:»
    assert fields[3] == "3.75"         # факт — вниз до 0.25 (правило 1 файла)
    assert fields[4] == "—"            # «из них задания» не введено — не выдумывается
    assert fields[5] == "—" and fields[6] == "—"
    assert journal_copy.read_text(encoding="utf-8").splitlines()[-1] == row


def test_tasks_hours_are_written_and_capped_by_fact(journal_copy) -> None:
    """Правило 1a: задания — часть факта, не добавка к нему."""
    row = journal.append_session(
        theme="M3.04",
        plan="5–6",
        fact_seconds=2 * 3600,
        fact_tasks="1,25",             # запятая как разделитель — тоже число
        day=date(2026, 8, 24),
        path=journal_copy,
    )
    assert [f.strip() for f in row.split("|")][4] == "1.25"

    # Больше факта записать нельзя: это описка, а по колонке считают вилки.
    assert journal.clamp_tasks("9", "2") == "2"
    assert journal.clamp_tasks("", "2") is None       # пустое поле законно
    assert journal.clamp_tasks("много", "2") is None  # нечисловой ввод — не число
    assert journal.clamp_tasks(None, "2") is None


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
    assert len([f for f in row.split("|")]) == 7


def test_notes_go_into_stuck_column_one_by_one(journal_copy) -> None:
    """Правило 6: отдельная пометка на каждое обращение, а не сводка."""
    row = journal.compose_row(
        theme="M5.03",
        plan="6–8",
        fact="2.5",
        stuck="pandas merge по двум ключам",
        notes=[
            "[сторона] ассистент: чем how='left' отличается от how='inner'",
            "[проверка] вердикт ИИ по критерию 1.5 (не скрипт): задание 7 → не сошлось",
        ],
    )
    stuck = row.split("|")[5]
    # Решение 45: два разных события, а не одно. Фальсификатор решения 28
    # считает только «[сторона]».
    assert stuck.count("[сторона]") == 1
    assert stuck.count("[проверка]") == 1
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
               "[проверка] вердикт ИИ по критерию 1.5 (не скрипт): задание 13 → не сошлось"],
        day=date(2026, 8, 24),
        path=journal_copy,
    )
    last = journal.records(path=journal_copy)[-1]
    assert last["parsed"] and last["date"] == "2026-08-24"
    assert last["plan"] == "6–8" and last["fact"] == "2"
    assert last["notes"] == 1, "пометки правила 6 не сосчитаны"
    assert last["checks"] == 1, "пометки проверки считаются отдельно (решение 45)"
    assert last["useless"] == "—"


def test_six_field_rows_written_before_decision_44_still_parse(tmp_path) -> None:
    """Старый формат читается, но «Факт: задания» ему не приписывается."""
    f = tmp_path / "self.md"
    f.write_text(
        "## Записи\n\n2026-07-29 | Фаза 1 | — | — | — | —\n",
        encoding="utf-8",
    )
    row = journal.records(path=f)[0]
    assert row["parsed"] and row["fact_tasks"] == "—"
    assert row["stuck"] == "—" and row["useless"] == "—"


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
