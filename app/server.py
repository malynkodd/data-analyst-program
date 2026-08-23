"""Flask-сервер приложения: один процесс, один порт, localhost.

Маршруты — по `app/PLAN.md`, раздел 2. Содержание нигде не кэшируется:
каждый запрос читает `program/**/step-*.md` и `DEFERRED.md` с диска.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import markdown  # noqa: E402
from flask import Flask, jsonify, request, send_from_directory  # noqa: E402
from pygments.formatters import HtmlFormatter  # noqa: E402

import assistant  # noqa: E402
import journal  # noqa: E402
import repo  # noqa: E402
import runner  # noqa: E402
import state  # noqa: E402

APP_DIR = Path(__file__).resolve().parent
app = Flask(__name__, static_folder=str(APP_DIR / "static"), static_url_path="/static")

MD_EXTENSIONS = ["tables", "fenced_code", "codehilite", "sane_lists", "attr_list"]
MD_CONFIG = {"codehilite": {"guess_lang": False, "linenums": False}}


def _render(text: str) -> str:
    return markdown.markdown(text, extensions=MD_EXTENSIONS, extension_configs=MD_CONFIG)


def _step_id(module: str, number: int) -> str:
    return f"{module}/step-{number:02d}"


def _split_id(step_id: str) -> tuple[str, int]:
    module, _, name = step_id.partition("/")
    return module, int(name.replace("step-", ""))


# ------------------------------------------------------------- страница


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/pygments.css")
def pygments_css():
    css = HtmlFormatter(style="friendly").get_style_defs(".codehilite")
    return app.response_class(css, mimetype="text/css")


# ----------------------------------------------------------------- API


def _short_title(module: str, number: int, title: str) -> str:
    """`M4.05. Переносит модель…` → `Переносит модель…`.

    Код шага показывается отдельной меткой, дублировать его в названии
    незачем — в списке из пяти шагов подряд он съедает половину строки.
    Номер в заголовках написан и с ведущим нулём (`M4.05`, `P1.00`), и без
    него (`M0.1`, `M3.11`) — снимаются оба вида.
    """
    for prefix in (f"{module}.{number:02d}.", f"{module}.{number}."):
        if title.startswith(prefix):
            return title[len(prefix):].strip()
    return title


def _module_block(module: str, states: dict) -> dict:
    meta = repo.catalog().get(module, {})
    items = []
    done = 0
    for st in repo.steps(module):
        status = states.get(st.step_id, {}).get("status", state.NOT_STARTED)
        if status == state.DONE and not st.is_declaration:
            done += 1
        items.append(
            {
                "step_id": st.step_id,
                "module": module,
                "number": st.number,
                "title": _short_title(module, st.number, st.title),
                "full_title": st.title,
                "declaration": st.is_declaration,
                "status": status,
                "plan_hours": repo.plan_hours(st.header),
                "skill": st.header.get("Умение", ""),
                "has_checks": bool(repo.check_commands(module, st.path.read_text(encoding="utf-8"))),
                "deferred": bool(repo.deferred_for(module, st.number)),
            }
        )
    total = sum(1 for i in items if not i["declaration"])
    return {
        "module": module,
        "name": meta.get("name", ""),
        "hours": meta.get("hours", ""),
        "kind": "проект" if module.startswith("P") else ("блок" if module == repo.CAREER else "модуль"),
        "steps": items,
        "done": done,
        "total": total,
    }


@app.get("/api/tree")
def api_tree():
    """Дерево в порядке прохождения: шесть этапов части 6.2 blueprint."""
    states = state.all_states()
    blocks: dict[str, dict] = {}
    placed: set[str] = set()
    out_stages = []
    for stage in repo.stages():
        codes = [c for c in stage["codes"] if (repo.PROGRAM / c).is_dir() and c not in placed]
        placed.update(codes)
        for code in codes:
            blocks[code] = _module_block(code, states)
        out_stages.append(
            {
                "number": stage["number"],
                "name": stage["name"],
                "hours": stage["hours"],
                "weeks_10": stage["weeks_10"],
                "weeks_25": stage["weeks_25"],
                "raw": stage["raw"],
                "modules": [blocks[c] for c in codes],
                "done": sum(blocks[c]["done"] for c in codes),
                "total": sum(blocks[c]["total"] for c in codes),
            }
        )

    # Первый незакрытый содержательный шаг в порядке этапов — это и есть
    # ответ на вопрос «что делать сейчас».
    next_step = None
    for stage in out_stages:
        for mod in stage["modules"]:
            for item in mod["steps"]:
                if item["declaration"] or item["status"] == state.DONE:
                    continue
                if next_step is None:
                    next_step = dict(item, module_name=mod["name"], stage=stage["name"])
                break
            if next_step:
                break
        if next_step:
            break

    done = sum(s["done"] for s in out_stages)
    total = sum(s["total"] for s in out_stages)
    return jsonify(
        {
            "stages": out_stages,
            "next_step": next_step,
            "done": done,
            "total": total,
            "assistant": assistant.available(),
        }
    )


def _neighbours(module: str, number: int) -> dict:
    """Предыдущий и следующий шаг — внутри модуля, затем по этапам."""
    order = repo.stage_order()
    flat: list[dict] = []
    for code in order:
        for st in repo.steps(code):
            flat.append({"step_id": st.step_id, "module": code, "number": st.number,
                         "title": _short_title(code, st.number, st.title),
                         "declaration": st.is_declaration})
    here = next((i for i, s in enumerate(flat) if s["step_id"] == f"{module}/step-{number:02d}"), None)
    if here is None:
        return {"prev": None, "next": None, "position": None, "of": None}
    in_module = [s for s in flat if s["module"] == module and not s["declaration"]]
    position = next((i + 1 for i, s in enumerate(in_module) if s["number"] == number), None)
    return {
        "prev": flat[here - 1] if here > 0 else None,
        "next": flat[here + 1] if here + 1 < len(flat) else None,
        "position": position,
        "of": len(in_module),
    }


@app.get("/api/step/<module>/<int:number>")
def api_step(module: str, number: int):
    try:
        st = repo.step(module, number)
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    text = st.path.read_text(encoding="utf-8")
    secs = repo.sections(text)
    checks = repo.check_commands(module, text)
    meta = repo.catalog().get(module, {})
    sections_out = [
        {
            "num": s["num"],
            "title": s["title"],
            "hint": s["hint"],
            "key": s["key"],
            "html": _render(s["body"]),
        }
        for s in repo.ordered_sections(text)
    ]
    return jsonify(
        {
            "step_id": st.step_id,
            "module": module,
            "module_name": meta.get("name", ""),
            "module_hours": meta.get("hours", ""),
            "number": number,
            "title": _short_title(module, number, st.title),
            "code": f"{module}.{number:02d}",
            "rel_path": st.rel_path,
            "header": st.header,
            "plan_hours": repo.plan_hours(st.header),
            "declaration": st.is_declaration,
            "preamble_html": _render(repo.preamble(text)),
            "sections": sections_out,
            "checks": [{"index": c.index, "raw": c.raw, "cwd": c.cwd} for c in checks],
            "deferred": repo.deferred_for(module, number),
            "has_criterion": "1.5" in secs,
            "state": state.get(st.step_id),
            **_neighbours(module, number),
        }
    )


@app.post("/api/check/run")
def api_check_run():
    data = request.get_json(force=True)
    module, number = _split_id(data["step_id"])
    index = int(data["index"])
    text = repo.step(module, number).path.read_text(encoding="utf-8")
    commands = repo.check_commands(module, text)
    if index < 0 or index >= len(commands):
        return jsonify({"error": "такой команды в шаге нет"}), 400
    result = runner.run(commands[index])
    return jsonify(
        {
            "command": result.command,
            "cwd": result.cwd,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timed_out": result.timed_out,
            "error": result.error,
            "source": "результат скрипта",
        }
    )


@app.post("/api/session/<action>")
def api_session(action: str):
    data = request.get_json(force=True)
    step_id = data["step_id"]
    if action == "start":
        return jsonify(state.start(step_id))
    if action == "pause":
        return jsonify(state.pause(step_id))
    if action == "resume":
        return jsonify(state.resume(step_id))
    if action == "reopen":
        return jsonify(state.reopen(step_id))
    if action == "finish":
        module, number = _split_id(step_id)
        st = repo.step(module, number)
        closed = state.finish(step_id)
        row = journal.append_session(
            theme=data.get("theme") or f"{module}.{number:02d} {st.title}",
            plan=data.get("plan") or repo.plan_hours(st.header),
            fact_seconds=float(closed.get("seconds", 0.0)),
            stuck=data.get("stuck"),
            useless=data.get("useless"),
            notes=closed.get("notes", []),
        )
        return jsonify({"row": row, "state": state.get(step_id), "tail": journal.tail()})
    return jsonify({"error": f"неизвестное действие: {action}"}), 400


@app.get("/api/journal/tail")
def api_journal_tail():
    return jsonify({"lines": journal.tail()})


@app.post("/api/assistant/ask")
def api_assistant_ask():
    data = request.get_json(force=True)
    module, number = _split_id(data["step_id"])
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "пустой вопрос"}), 400
    try:
        answer = assistant.ask(module, number, question, data.get("history") or [])
    except assistant.AssistantUnavailable as exc:
        return jsonify({"error": str(exc)}), 503
    note = assistant.note_for_question(question)
    state.add_note(data["step_id"], note)
    return jsonify({"answer": answer, "note": note})


@app.post("/api/assistant/verdict")
def api_assistant_verdict():
    data = request.get_json(force=True)
    module, number = _split_id(data["step_id"])
    answer = (data.get("answer") or "").strip()
    task = (data.get("task") or "").strip()
    if not answer:
        return jsonify({"error": "пустой ответ"}), 400
    try:
        result = assistant.verdict(module, number, answer, task)
    except assistant.AssistantUnavailable as exc:
        return jsonify({"error": str(exc)}), 503
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    note = assistant.note_for_verdict(task, result["verdict"])
    state.add_note(data["step_id"], note)
    result["note"] = note
    return jsonify(result)


def main() -> None:
    ap = argparse.ArgumentParser(description="Локальное приложение для прохождения программы")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()
    assistant.load_env()
    print(f"program: {repo.ROOT}")
    print(f"ассистент: {'ключ найден' if assistant.available() else 'ключа нет (app/.env)'}")
    print(f"открыть: http://{args.host}:{args.port}/")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
