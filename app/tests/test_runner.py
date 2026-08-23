"""Запуск check-скрипта из приложения даёт то же, что запуск напрямую.

Требование архитектуры: приложение не переписывает и не импортирует
проверки программы, а запускает те же файлы (`app/PLAN.md`, раздел 3).
Сломать это можно молча — подменив интерпретатор, рабочую папку или
кодировку вывода, — и тогда `[OK]` в интерфейсе перестанет означать `[OK]`
в терминале. Тест сверяет обе половины дословно.

Взяты два случая разного класса разбора пути:
* `M0/step-01` — путь относительный, шаг велит перейти в `data/`;
* `career/step-01` — путь от корня репозитория.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

import repo
import runner

CASES = [("M0", 1), ("career", 1)]


def _direct(cmd: repo.CheckCommand) -> tuple[int, str, str]:
    """Прямой запуск: так же, как это делает человек в терминале."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    proc = subprocess.run(
        [sys.executable, *cmd.argv],
        cwd=str(repo.ROOT / cmd.cwd),
        capture_output=True,
        env=env,
    )
    return (
        proc.returncode,
        proc.stdout.decode("utf-8", errors="replace"),
        proc.stderr.decode("utf-8", errors="replace"),
    )


def _commands(module: str, number: int) -> list[repo.CheckCommand]:
    text = repo.step_text(module, number)
    return repo.check_commands(module, text)


@pytest.mark.parametrize("module,number", CASES)
def test_step_has_commands(module: str, number: int) -> None:
    assert _commands(module, number), f"{module}/step-{number:02d}: команда проверки не найдена"


@pytest.mark.parametrize("module,number", CASES)
def test_runner_matches_direct_run(module: str, number: int) -> None:
    for cmd in _commands(module, number):
        assert cmd.cwd is not None, f"не нашлась рабочая папка для {cmd.raw}"
        expected_code, expected_out, expected_err = _direct(cmd)
        got = runner.run(cmd)

        assert got.returncode == expected_code, cmd.raw
        assert got.stdout == expected_out, cmd.raw
        assert got.stderr == expected_err, cmd.raw
        assert got.error is None and not got.timed_out, cmd.raw


def test_runner_reports_missing_script_instead_of_guessing() -> None:
    """Несошедшийся путь — ошибка в интерфейсе, а не выдуманная папка."""
    cmd = repo.CheckCommand(index=0, raw="python check_nothing.py", argv=["check_nothing.py"], cwd=None)
    result = runner.run(cmd)
    assert result.returncode == -1
    assert "не найден" in (result.error or "")
