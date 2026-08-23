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


@app.get("/api/tree")
def api_tree():
    states = state.all_states()
    out = []
    for module in repo.modules():
        items = []
        done = 0
        for st in repo.steps(module):
            sid = st.step_id
            status = states.get(sid, {}).get("status", state.NOT_STARTED)
            if status == state.DONE and not st.is_declaration:
                done += 1
            items.append(
                {
                    "step_id": sid,
                    "module": module,
                    "number": st.number,
                    "title": st.title,
                    "declaration": st.is_declaration,
                    "status": status,
                    "has_checks": bool(
                        repo.check_commands(module, st.path.read_text(encoding="utf-8"))
                    ),
                    "deferred": bool(repo.deferred_for(module, st.number)),
                }
            )
        total = sum(1 for i in items if not i["declaration"])
        out.append({"module": module, "steps": items, "done": done, "total": total})
    return jsonify({"modules": out, "assistant": assistant.available()})


@app.get("/api/step/<module>/<int:number>")
def api_step(module: str, number: int):
    try:
        st = repo.step(module, number)
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    text = st.path.read_text(encoding="utf-8")
    secs = repo.sections(text)
    checks = repo.check_commands(module, text)
    return jsonify(
        {
            "step_id": st.step_id,
            "module": module,
            "number": number,
            "title": st.title,
            "rel_path": st.rel_path,
            "header": st.header,
            "plan_hours": repo.plan_hours(st.header),
            "declaration": st.is_declaration,
            "html": _render(text),
            "checks": [{"index": c.index, "raw": c.raw, "cwd": c.cwd} for c in checks],
            "deferred": repo.deferred_for(module, number),
            "has_criterion": "1.5" in secs,
            "state": state.get(st.step_id),
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
