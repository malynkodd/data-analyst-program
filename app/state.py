"""Собственное состояние приложения: статусы шагов, таймер, буфер пометок.

Единственный файл, который приложение пишет для себя, —
`app/state/progress.json` (в `.gitignore`). Учебного текста в нём нет:
только идентификатор шага, отметки времени и накопленные пометки правила 6
`research/self.md`. Удаление папки не меняет ни одного экрана, кроме
отметок «начал/закончил» (`app/PLAN.md`, раздел 0).

Перерывы не считаются (правило 1 `research/self.md`): часы копятся только
между «Начал»/«Продолжил» и «Пауза»/«Закончил».
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
STATE_DIR = APP_DIR / "state"
STATE_FILE = STATE_DIR / "progress.json"

NOT_STARTED = "not_started"
RUNNING = "running"
PAUSED = "paused"
DONE = "done"

_EMPTY = {"status": NOT_STARTED, "accumulated_sec": 0.0, "resumed_at": None, "notes": []}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load(path: Path | None = None) -> dict:
    target = path or STATE_FILE
    if not target.is_file():
        return {"steps": {}}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"steps": {}}
    data.setdefault("steps", {})
    return data


def _save(data: dict, path: Path | None = None) -> None:
    target = path or STATE_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    # Запись через временный файл: питание может пропасть на любом тике
    # таймера, и половина JSON стоила бы всей истории прогресса.
    fd, tmp = tempfile.mkstemp(dir=str(target.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def get(step_id: str, path: Path | None = None) -> dict:
    entry = dict(_EMPTY) | _load(path)["steps"].get(step_id, {})
    entry.setdefault("notes", [])
    entry["elapsed_sec"] = elapsed(entry)
    return entry


def all_states(path: Path | None = None) -> dict[str, dict]:
    data = _load(path)["steps"]
    return {k: (dict(_EMPTY) | v) for k, v in data.items()}


def elapsed(entry: dict) -> float:
    """Накопленные секунды, включая идущий отрезок."""
    total = float(entry.get("accumulated_sec", 0.0))
    resumed = entry.get("resumed_at")
    if entry.get("status") == RUNNING and resumed:
        total += (_now() - datetime.fromisoformat(resumed)).total_seconds()
    return max(total, 0.0)


def _mutate(step_id: str, fn, path: Path | None = None) -> dict:
    data = _load(path)
    entry = dict(_EMPTY) | data["steps"].get(step_id, {})
    entry.setdefault("notes", [])
    fn(entry)
    data["steps"][step_id] = entry
    _save(data, path)
    out = dict(entry)
    out["elapsed_sec"] = elapsed(entry)
    return out


def start(step_id: str, path: Path | None = None) -> dict:
    def fn(entry: dict) -> None:
        if entry["status"] == RUNNING:
            return
        entry.setdefault("first_started_at", _now().isoformat())
        entry["status"] = RUNNING
        entry["resumed_at"] = _now().isoformat()

    return _mutate(step_id, fn, path)


def pause(step_id: str, path: Path | None = None) -> dict:
    def fn(entry: dict) -> None:
        if entry["status"] != RUNNING:
            return
        entry["accumulated_sec"] = elapsed(entry)
        entry["status"] = PAUSED
        entry["resumed_at"] = None

    return _mutate(step_id, fn, path)


def resume(step_id: str, path: Path | None = None) -> dict:
    return start(step_id, path)


def add_note(step_id: str, note: str, path: Path | None = None) -> dict:
    """Пометка правила 6 копится до конца сессии этого шага."""

    def fn(entry: dict) -> None:
        entry["notes"] = list(entry.get("notes", [])) + [note]

    return _mutate(step_id, fn, path)


def finish(step_id: str, path: Path | None = None) -> dict:
    """Закрывает сессию: возвращает секунды и пометки, чистит буфер.

    Строку в `research/self.md` пишет `journal.py` — здесь только состояние.
    """
    captured: dict = {}

    def fn(entry: dict) -> None:
        entry["accumulated_sec"] = elapsed(entry)
        entry["status"] = DONE
        entry["resumed_at"] = None
        entry["finished_at"] = _now().isoformat()
        captured["seconds"] = entry["accumulated_sec"]
        captured["notes"] = list(entry.get("notes", []))
        entry["notes"] = []
        entry["accumulated_sec"] = 0.0

    _mutate(step_id, fn, path)
    return captured


def reopen(step_id: str, path: Path | None = None) -> dict:
    """Снимает отметку «закончен» — шаг можно проходить снова."""

    def fn(entry: dict) -> None:
        entry["status"] = NOT_STARTED
        entry["resumed_at"] = None
        entry["accumulated_sec"] = 0.0

    return _mutate(step_id, fn, path)
