"""Вердикт ИИ: сборка промпта, пометка происхождения, различие вердиктов.

Три разных требования:

1. В промпт уходят дословные разделы 1.5 и 1.6 **того же файла шага** —
   иначе вердикт судит по чему-то, чего в программе нет.
2. Вердикт всегда помечен как оценка ИИ, а не результат скрипта. Поле
   `source` проставляет приложение, а не модель: иначе надёжность пометки
   зависела бы от того, что модель о себе написала.
3. На заведомо неверном ответе вердикт отличается от вердикта на верном.
   Обе половины берутся из `program/career/data/reference_answers.md`,
   раздел «Обе половины примера — шаг 01»: отрицательная — незаполненный
   шаблон `cv_template.md`, положительная — `reference/cv.md`.

Пункт 3 обращается к настоящему API и пропускается, если ключа нет:
подставной ответ доказал бы только то, что тест сам себе его и написал.
"""

from __future__ import annotations

import json
import types

import pytest

import assistant
import repo

NEGATIVE = repo.ROOT / "program" / "career" / "data" / "cv_template.md"
POSITIVE = repo.ROOT / "program" / "career" / "data" / "reference" / "cv.md"


# ------------------------------------------------ 1. промпт из файла шага


def test_prompt_carries_criterion_and_typical_errors_verbatim() -> None:
    text = repo.step_text("M4", 5)
    secs = repo.sections(text)
    prompt = assistant.build_verdict_prompt("M4", 5, answer="ответ учащегося", task="задание 13")

    assert secs["1.5"] in prompt, "раздел 1.5 подан не дословно"
    assert secs["1.6"] in prompt, "раздел 1.6 подан не дословно"
    assert "program/M4/step-05.md" in prompt
    assert "ответ учащегося" in prompt


def test_chat_context_is_the_whole_step_file() -> None:
    system = assistant.build_chat_system("M4", 5)
    assert repo.step_text("M4", 5) in system


# ---------------------------------------- 2. пометка «это не скрипт»


class _StubMessages:
    """Подставной клиент: проверяет разбор ответа, а не саму модель."""

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def create(self, **kwargs):
        self.kwargs = kwargs
        block = types.SimpleNamespace(type="text", text=json.dumps(self._payload, ensure_ascii=False))
        return types.SimpleNamespace(content=[block], stop_reason="end_turn")


class _StubClient:
    def __init__(self, payload: dict) -> None:
        self.messages = _StubMessages(payload)
        self.beta = types.SimpleNamespace(messages=self.messages)


def test_verdict_is_always_marked_as_ai_not_script() -> None:
    payload = {
        "verdict": "сошлось",
        "matched": ["пункт 1.5: объём не больше страницы"],
        "missing": [],
        "errors_hit": [],
        "replaces_manual_run": True,  # модель ошиблась — приложение не обязано верить
        "explanation": "…",
    }
    result = assistant.verdict("career", 1, "текст резюме", client=_StubClient(payload))
    assert result["source"] == assistant.VERDICT_SOURCE
    assert "не скрипт" in result["source"]


def test_journal_note_names_the_channel_and_the_kind() -> None:
    # Решение 45: вердикт по уже написанному ответу — самопроверка, а не
    # «текста шага не хватило». Пометки разные, и считаются они отдельно.
    note = assistant.note_for_verdict("задание 13", "не сошлось")
    assert note.startswith("[проверка]")
    assert not note.startswith("[сторона]")
    assert "не скрипт" in note
    assert "не сошлось" in note

    ask_note = assistant.note_for_question("почему Refresh без ошибок ничего не доказывает")
    assert ask_note.startswith("[сторона] ассистент:")


# -------------------------- 3. неверный ответ ≠ верный (настоящий API)


@pytest.mark.skipif(not assistant.available(), reason="нет ANTHROPIC_API_KEY в app/.env")
def test_wrong_answer_gets_a_different_verdict_than_the_right_one() -> None:
    task = "резюме по критерию шага career/step-01"
    wrong = assistant.verdict("career", 1, NEGATIVE.read_text(encoding="utf-8"), task)
    right = assistant.verdict("career", 1, POSITIVE.read_text(encoding="utf-8"), task)

    assert wrong["verdict"] != right["verdict"], (
        f"вердикт не различает половины примера: {wrong['verdict']!r} на незаполненном "
        f"шаблоне и {right['verdict']!r} на заполненном резюме"
    )
    assert wrong["verdict"] == "не сошлось"
    assert wrong["missing"] or wrong["errors_hit"], "непройденный критерий не назван ни одним пунктом"
    assert wrong["source"] == right["source"] == assistant.VERDICT_SOURCE
