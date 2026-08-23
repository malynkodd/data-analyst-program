"""Ассистент на Claude API: чат по тексту шага и вердикт по критерию.

Два режима (`app/PLAN.md`, раздел 5):

* `ask()` — вопрос по текущему шагу. Контекст — полный текст того же
  `step-*.md`, собранный в момент запроса и никуда не сохраняемый.
* `verdict()` — оценка письменного ответа по разделам `1.5. Критерий
  готовности` и `1.6. Типичные ошибки` того же файла. Возвращается вместе
  с полем `source`, которое приложение проставляет само: это **оценка ИИ,
  а не результат скрипта**, и в интерфейсе и в `research/self.md` они
  помечаются по-разному.

Ключ — `ANTHROPIC_API_KEY` из `app/.env` (файл в `.gitignore`, образец —
`app/.env.example`).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import repo

APP_DIR = Path(__file__).resolve().parent
ENV_FILE = APP_DIR / ".env"

MODEL = "claude-opus-5"
MAX_TOKENS_CHAT = 16000
MAX_TOKENS_VERDICT = 8000

# Приложение проставляет это поле само, а не берёт из ответа модели:
# надёжность вердикта не должна зависеть от того, что модель о себе
# написала.
VERDICT_SOURCE = "вердикт ИИ по критерию (не скрипт)"

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {
            "type": "string",
            "enum": ["сошлось", "не сошлось", "недостаточно данных"],
        },
        "matched": {"type": "array", "items": {"type": "string"}},
        "missing": {"type": "array", "items": {"type": "string"}},
        "errors_hit": {"type": "array", "items": {"type": "string"}},
        "replaces_manual_run": {"type": "boolean"},
        "explanation": {"type": "string"},
    },
    "required": [
        "verdict",
        "matched",
        "missing",
        "errors_hit",
        "replaces_manual_run",
        "explanation",
    ],
    "additionalProperties": False,
}

CHAT_RULES = """Вы отвечаете на вопрос по одному шагу учебной программы.

Правила:
- Отвечайте по тексту шага, приведённому ниже. Если ответа в шаге нет —
  скажите это прямо и назовите, чего в шаге не хватает, вместо того чтобы
  достраивать своё.
- Критерий готовности шага не смягчайте и своего не придумывайте.
- Тон программы: без воды, без мотивационных вставок, без «давайте вместе
  погрузимся». Числа — со ссылкой на место в шаге, откуда они взяты.
- Отвечайте по-русски."""

VERDICT_RULES = """Вы проверяете письменный ответ учащегося по одному шагу
учебной программы.

Правила:
- Судить разрешено только по приведённым разделам «1.5. Критерий
  готовности» и «1.6. Типичные ошибки». Своих требований не добавлять,
  требований шага не смягчать.
- Каждый пункт в `matched`, `missing` и `errors_hit` обязан ссылаться на
  конкретный пункт 1.5 или на конкретную ошибку из 1.6 и цитировать его
  коротко, а не пересказывать.
- Если критерий требует прогона скрипта, работы в Power BI Desktop,
  Tableau Public, Looker Studio или сверки выгрузки с эталоном — скажите
  прямо в `explanation`, что вердикт по тексту этого не заменяет, и
  оставьте `replaces_manual_run` равным false.
- `verdict`: «сошлось» — ответ закрывает всё, что вообще проверяемо по
  тексту; «не сошлось» — есть пропущенный пункт 1.5 или попадание в
  ошибку из 1.6; «недостаточно данных» — ответ пуст или не относится к
  заданию.
- `explanation` — не более пяти предложений, по-русски, без мотивационных
  вставок."""


class AssistantUnavailable(RuntimeError):
    """Ключа нет или SDK не установлен — вызов не делается."""


# ------------------------------------------------------------------ ключ


def load_env(path: Path | None = None) -> None:
    """Читает `app/.env` в `os.environ`, не затирая уже заданное снаружи."""
    target = path or ENV_FILE
    if not target.is_file():
        return
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def api_key() -> str | None:
    load_env()
    return os.environ.get("ANTHROPIC_API_KEY") or None


def available() -> bool:
    if not api_key():
        return False
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


def _client():
    key = api_key()
    if not key:
        raise AssistantUnavailable(
            "ANTHROPIC_API_KEY не найден — заполните app/.env по образцу app/.env.example"
        )
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover — зависимость из requirements.txt
        raise AssistantUnavailable("пакет anthropic не установлен") from exc
    return anthropic.Anthropic(api_key=key)


def _create(client, **kwargs):
    """Запрос к Messages API с серверным fallback, если он доступен.

    Fallback снимает случай, когда классификатор отклоняет запрос
    (`stop_reason == "refusal"`). Если бета не поддержана — тот же запрос
    уходит обычным путём, без него.
    """
    try:
        return client.beta.messages.create(
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            **kwargs,
        )
    except Exception:
        return client.messages.create(**kwargs)


def _text_of(response) -> str:
    parts = [b.text for b in response.content if getattr(b, "type", None) == "text"]
    return "\n".join(p for p in parts if p).strip()


# ------------------------------------------------------------------- чат


def build_chat_system(module: str, number: int) -> str:
    """Контекст шага для чата: шапка и полный текст файла, как он лежит."""
    st = repo.step(module, number)
    text = st.path.read_text(encoding="utf-8")
    header = "   ".join(f"{k}: {v}" for k, v in st.header.items() if k in ("Умение", "Время"))
    return (
        f"{CHAT_RULES}\n\n"
        f"Шаг: {st.rel_path}\n"
        f"Заголовок: {st.title}\n"
        f"{header}\n\n"
        f"--- полный текст шага ---\n{text}"
    )


def ask(module: str, number: int, question: str, history: list[dict] | None = None, client=None) -> str:
    client = client or _client()
    messages = list(history or [])
    messages.append({"role": "user", "content": question})
    response = _create(
        client,
        model=MODEL,
        max_tokens=MAX_TOKENS_CHAT,
        system=build_chat_system(module, number),
        thinking={"type": "adaptive"},
        messages=messages,
    )
    if getattr(response, "stop_reason", None) == "refusal":
        return "Модель отклонила запрос (stop_reason: refusal). Переформулируйте вопрос."
    return _text_of(response) or "Пустой ответ модели."


# --------------------------------------------------------------- вердикт


def build_verdict_prompt(module: str, number: int, answer: str, task: str = "") -> str:
    """Разделы 1.4, 1.5, 1.6 и 1.8 шага дословно плюс ответ автора."""
    st = repo.step(module, number)
    secs = repo.sections(st.path.read_text(encoding="utf-8"))
    wanted = [n for n in ("1.4", "1.5", "1.6", "1.8") if n in secs]
    if "1.5" not in secs:
        raise ValueError(f"{st.rel_path}: нет раздела 1.5 — вердикт по критерию невозможен")
    blocks = "\n\n".join(secs[n] for n in wanted)
    return (
        f"Шаг: {st.rel_path}\n"
        f"Заголовок: {st.title}\n"
        f"Что проверяется: {task or 'письменный ответ по критерию шага'}\n\n"
        f"--- разделы шага (дословно) ---\n{blocks}\n\n"
        f"--- ответ учащегося ---\n{answer.strip() or '(пусто)'}"
    )


def parse_verdict(raw: str) -> dict:
    """Разбор структурного ответа и простановка пометки о происхождении."""
    data = json.loads(raw)
    data["source"] = VERDICT_SOURCE
    data["replaces_manual_run"] = bool(data.get("replaces_manual_run", False))
    return data


def verdict(module: str, number: int, answer: str, task: str = "", client=None) -> dict:
    client = client or _client()
    response = _create(
        client,
        model=MODEL,
        max_tokens=MAX_TOKENS_VERDICT,
        system=VERDICT_RULES,
        messages=[{"role": "user", "content": build_verdict_prompt(module, number, answer, task)}],
        output_config={"format": {"type": "json_schema", "schema": VERDICT_SCHEMA}},
    )
    if getattr(response, "stop_reason", None) == "refusal":
        raise AssistantUnavailable("модель отклонила запрос (stop_reason: refusal)")
    return parse_verdict(_text_of(response))


# ------------------------------------------- пометки правила 6 self.md


def note_for_question(question: str) -> str:
    """`[сторона] ассистент: ...` — правило 6 `research/self.md`.

    Решение 40: обращение к встроенному ассистенту считается обращением на
    сторону наравне с внешним поиском, иначе фальсификатор решения 28
    перестаёт что-либо мерить.
    """
    text = " ".join(question.split())
    if len(text) > 120:
        text = text[:117] + "..."
    return f"[сторона] ассистент: {text}"


def note_for_verdict(task: str, result: str) -> str:
    """`[проверка] ...` — правило 6 `research/self.md`, абзац решения 45.

    Не `[сторона]`: вердикт по уже написанному ответу — самопроверка, а не
    признак того, что текста шага не хватило. Пометки `[проверка]` в
    фальсификатор решения 28 не входят и считаются отдельно (решение 45,
    2026-08-24). До этого обе пометки были одной, и единственный механизм,
    закрывающий слабую самопроверку концептуальных умений (blueprint,
    часть 7, п. 7), учитывался журналом как слабость учащегося.
    """
    label = " ".join((task or "письменный ответ").split())
    if len(label) > 80:
        label = label[:77] + "..."
    return f"[проверка] вердикт ИИ по критерию 1.5 (не скрипт): {label} → {result}"
