"""Запуск существующих `check_*.py` как есть.

Скрипты не переписываются и не импортируются: приложение запускает тот же
файл тем же интерпретатором из той же рабочей папки, что и терминал, и
показывает дословный вывод. Требование проверяется тестом
`tests/test_runner.py`: результат из приложения совпадает с прямым
запуском.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass

from repo import ROOT, CheckCommand

TIMEOUT_SEC = 120


@dataclass
class CheckResult:
    command: str  # то, что реально запущено, с подставленным интерпретатором
    cwd: str  # рабочая папка относительно корня репозитория
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False
    error: str | None = None


def run(cmd: CheckCommand) -> CheckResult:
    if cmd.cwd is None:
        return CheckResult(
            command=cmd.raw,
            cwd="—",
            returncode=-1,
            stdout="",
            stderr="",
            error=(
                f"скрипт {cmd.argv[0] if cmd.argv else '?'} не найден ни от корня "
                f"репозитория, ни в data/ модуля — запускать нечего"
            ),
        )

    workdir = (ROOT / cmd.cwd).resolve()
    argv = [sys.executable, *cmd.argv]

    # Вывод скриптов — кириллица; без этого дочерний python на Windows
    # берёт кодовую страницу консоли и роняется на печати (тот же класс,
    # что решение 17 программы).
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")

    try:
        proc = subprocess.run(
            argv,
            cwd=str(workdir),
            capture_output=True,
            timeout=TIMEOUT_SEC,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        return CheckResult(
            command=" ".join(argv),
            cwd=cmd.cwd,
            returncode=-1,
            stdout=_decode(exc.stdout),
            stderr=_decode(exc.stderr),
            timed_out=True,
            error=f"скрипт не завершился за {TIMEOUT_SEC} с",
        )
    except OSError as exc:
        return CheckResult(
            command=" ".join(argv),
            cwd=cmd.cwd,
            returncode=-1,
            stdout="",
            stderr="",
            error=str(exc),
        )

    return CheckResult(
        command=" ".join(argv),
        cwd=cmd.cwd,
        returncode=proc.returncode,
        stdout=_decode(proc.stdout),
        stderr=_decode(proc.stderr),
    )


def _decode(raw: bytes | None) -> str:
    if not raw:
        return ""
    return raw.decode("utf-8", errors="replace")
