"""Интерфейс проверяется тем же способом, что и всё остальное, — прогоном.

Тестов на статику до редизайна не было ни одного, и цена этого известна
поимённо: экран умений полгода печатал «36 умений», когда их стало 46;
стартовый — «73 шага» при 90; журнал — «17 из 24 вилок» при 22 из 25.
Числа стояли строкой в HTML, никакой скрипт их не читал, и разошлись они
молча — тот же класс ошибки, что `check_calibration_count()` ловит в
blueprint.

Здесь проверяется то, что проверяется без браузера:
1. каждый `$("id")` из `app.js` существует в разметке;
2. каждый значок `#i-…` объявлен в спрайте;
3. ни один внешний адрес не подключён — приложение работает офлайн;
4. каждая переменная `var(--…)` объявлена, и тёмная тема не забыла ни
   одной;
5. чисел программы в разметке нет: они приходят из API.
"""

from __future__ import annotations

import re
from pathlib import Path

import repo

STATIC = Path(repo.__file__).resolve().parent / "static"
HTML = (STATIC / "index.html").read_text(encoding="utf-8")
JS = (STATIC / "app.js").read_text(encoding="utf-8")
CSS = (STATIC / "style.css").read_text(encoding="utf-8")
FONTS_CSS = (STATIC / "fonts.css").read_text(encoding="utf-8")
SPRITE = (STATIC / "icons.svg").read_text(encoding="utf-8")


def _html_ids() -> set[str]:
    return set(re.findall(r'\bid="([^"]+)"', HTML))


def test_every_id_the_script_asks_for_exists_in_the_markup() -> None:
    """`$("chat-hint")` без такого id в разметке — молчаливый `null`.

    Скрипт не падает целиком: падает один обработчик, и экран остаётся
    наполовину живым. Ловится только чтением обоих файлов сразу.
    """
    static_ids = _html_ids()
    # id, создаваемые самим скриптом на лету, — их в разметке нет и быть
    # не должно; список закрытый, чтобы опечатка в нём тоже была видна.
    built_by_js = {
        "btn-go", "mod-go", "next-go", "btn-verdict", "v-task", "v-answer",
        "verdict-out", "tree-retry", "mod-retry", "step-retry",
        "skills-retry", "journal-retry", "session-error-retry",
        "finish-error-retry",
    }
    asked = set(re.findall(r'\$\("([a-z0-9-]+)"\)', JS))
    missing = sorted(asked - static_ids - built_by_js)
    assert not missing, f"скрипт обращается к несуществующим id: {missing}"


def test_screens_and_their_containers_are_all_present() -> None:
    """Пять экранов и контейнер под каждое видимое состояние."""
    ids = _html_ids()
    for screen in ("home", "step-body", "module-body", "skills-body", "journal-body"):
        assert screen in ids, f"нет экрана {screen}"
    # Контейнеры, в которые пишутся «загружается», «пусто» и «не вышло».
    for box in ("tree-body", "home-hero", "sections", "mod-steps",
                "skills-list", "journal-records", "session-error", "finish-error"):
        assert box in ids, f"нет контейнера состояния {box}"


def test_every_icon_used_is_declared_in_the_sprite() -> None:
    """Значок без символа в спрайте рисуется пустым местом, без ошибки."""
    declared = set(re.findall(r'<symbol id="i-([a-z-]+)"', SPRITE))
    used_html = set(re.findall(r'icons\.svg#i-([a-z-]+)', HTML))
    used_js = set(re.findall(r'ic\("([a-z-]+)"', JS))
    missing = sorted((used_html | used_js) - declared)
    assert not missing, f"значки, которых нет в icons.svg: {missing}"
    # Часть значков выбирается не литералом, а по таблице: `STATUS_ICON`,
    # набор состояний в `stateBox`, подписи реплик в `bubble`, аргумент
    # `link()` в навигации по шагам. Поэтому «мёртвым» символ считается
    # только если его имени нет в скрипте вообще.
    quoted = set(re.findall(r'"([a-z-]+)"', JS))
    unused = sorted(declared - used_html - used_js - quoted)
    assert not unused, f"символы в спрайте, которые никто не использует: {unused}"


def test_nothing_is_loaded_from_the_network() -> None:
    """Без CDN и без внешних шрифтов: приложение работает офлайн.

    `app/PLAN.md`, раздел 1: единственное обращение наружу — Claude API,
    и оно идёт с сервера, а не со страницы. `<link>` на чужой домен
    ломается молча — текст просто перерисовывается системным шрифтом.
    """
    for name, text in (("index.html", HTML), ("style.css", CSS),
                       ("fonts.css", FONTS_CSS), ("app.js", JS)):
        urls = re.findall(r'(?:href|src|url)\s*[=(]\s*["\']?(https?://[^"\')\s]+)', text)
        assert not urls, f"{name} тянет внешний ресурс: {urls}"


def test_vendored_fonts_are_actually_in_the_repository() -> None:
    """Каждый файл, объявленный в `fonts.css`, лежит рядом."""
    srcs = re.findall(r"url\('(/static/fonts/[^']+)'\)", FONTS_CSS)
    assert srcs, "в fonts.css не объявлено ни одного шрифта"
    for src in srcs:
        path = STATIC / src.replace("/static/", "")
        assert path.is_file(), f"{src} объявлен, но файла нет"
    assert "SIL Open Font License" in FONTS_CSS, "не указана лицензия шрифта"
    assert "Лицензия" in SPRITE or "лицензи" in SPRITE.lower(), \
        "в icons.svg не сказано, чей это рисунок"


def test_every_css_variable_used_is_declared() -> None:
    declared = set(re.findall(r"^\s*(--[a-z0-9-]+):", CSS, re.MULTILINE))
    used = set(re.findall(r"var\((--[a-z0-9-]+)", CSS))
    missing = sorted(used - declared)
    assert not missing, f"в CSS используются необъявленные переменные: {missing}"


def test_dark_theme_redefines_every_colour_the_light_one_declares() -> None:
    """Цвет, забытый в тёмной теме, остаётся светлым на тёмном фоне.

    Проверяется, что оба тёмных блока — системный (`prefers-color-scheme`)
    и ручной (`[data-theme="dark"]`) — перекрывают один и тот же набор.
    """
    root = re.search(r":root \{(.*?)\n\}", CSS, re.S).group(1)
    colours = {
        name for name, value in re.findall(r"(--[a-z0-9-]+):\s*([^;]+);", root)
        if re.match(r"^\s*(#|rgba?\()", value)
        # Цвета вывода терминала (`--term-*`) темы не меняют намеренно:
        # блок вывода `check_*.py` подражает консоли, а консоль не
        # перекрашивается вслед за страницей. Они объявлены один раз.
        and not name.startswith("--term-")
    }
    assert len(colours) > 20, "палитра неожиданно мала — тест смотрит не туда"

    system = re.search(r'@media \(prefers-color-scheme: dark\) \{\s*'
                       r':root:not\(\[data-theme="light"\]\) \{(.*?)\n  \}', CSS, re.S).group(1)
    manual = re.search(r':root\[data-theme="dark"\] \{(.*?)\n\}', CSS, re.S).group(1)

    for label, block in (("системная", system), ("ручная", manual)):
        got = set(re.findall(r"(--[a-z0-9-]+):", block))
        missing = sorted(colours - got)
        assert not missing, f"{label} тёмная тема не переопределяет: {missing}"


def test_programme_numbers_are_not_written_into_the_markup() -> None:
    """Ни одного числа программы строкой в HTML.

    Именно так разъехались «36 умений», «73 шага» и «17 из 24 вилок»:
    число стояло в разметке, а росло в blueprint. Теперь все они
    приходят из `/api/tree` и `/api/skills`.
    """
    text = re.sub(r"<!--.*?-->", "", HTML, flags=re.S)
    forbidden = re.findall(
        r"\b\d+\s+(?:шаг\w*|умен\w+|проект\w*|вилок)\b|\b\d+\s+из\s+\d+\b", text)
    assert not forbidden, f"число программы вписано в разметку: {forbidden}"


def test_the_two_verdict_plates_stay_distinguishable() -> None:
    """Результат скрипта и вердикт ИИ — разные по надёжности вещи.

    `app/PLAN.md`, 5.2 требует, чтобы они были помечены по-разному и не
    смешивались. Проверяется, что у плашек разные классы и разные цвета.
    """
    assert ".tag.script" in CSS and ".tag.ai" in CSS
    script_rule = re.search(r"\.tag\.script \{([^}]+)\}", CSS).group(1)
    ai_rule = re.search(r"\.tag\.ai \{([^}]+)\}", CSS).group(1)
    assert script_rule != ai_rule, "плашки скрипта и ИИ оформлены одинаково"
    assert "РЕЗУЛЬТАТ СКРИПТА" in JS
    assert "ВЕРДИКТ ИИ ПО КРИТЕРИЮ" in JS


def _luminance(hex_colour: str) -> float:
    channels = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(fg: str, bg: str) -> float:
    a, b = _luminance(fg), _luminance(bg)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def _palette(pattern: str) -> dict[str, str]:
    body = re.search(pattern, CSS, re.S).group(1)
    return dict(re.findall(r"(--[a-z0-9-]+):\s*(#[0-9a-fA-F]{6});", body))


# Пара «что читаем — на чём читаем» и порог WCAG 2.1: 4.5 для текста,
# 3.0 для подписей мелким кеглем, которые ничего не решают в одиночку.
CONTRAST_PAIRS = [
    ("основной текст на странице", "--ink", "--bg", 4.5),
    ("основной текст на карточке", "--ink", "--bg-raised", 4.5),
    ("вторичный текст на странице", "--ink-soft", "--bg", 4.5),
    ("вторичный текст на панели", "--ink-soft", "--bg-soft", 4.5),
    ("приглушённый текст", "--ink-faint", "--bg-soft", 3.0),
    ("акцент на странице", "--accent", "--bg", 4.5),
    ("акцент на своей подложке", "--accent", "--accent-soft", 4.5),
    ("текст на кнопке-акценте", "--accent-on", "--accent", 4.5),
    ("«проверено скриптом»", "--ok", "--ok-soft", 4.5),
    ("«вердикт ИИ»", "--warn", "--warn-soft", 4.5),
    ("«ручной прогон»", "--danger", "--danger-soft", 4.5),
    ("вывод терминала", "--term-ink", "--term-bg", 4.5),
]


def test_both_themes_are_readable_by_wcag() -> None:
    """Контраст текста к фону — счётом, а не «на глаз при дневном свете».

    Тёмная тема правится подбором, и подбор легко уводит подписи в
    нечитаемое: в тёмной палитре разница между `--ink-soft` и
    `--ink-faint` на глаз почти незаметна, а в числах это разница между
    8.4 и 4.6. Порог берётся один раз здесь, а не на каждом правке.
    """
    light = _palette(r":root \{(.*?)\n\}")
    dark = {**light, **_palette(r':root\[data-theme="dark"\] \{(.*?)\n\}')}

    failures = []
    for theme_name, palette in (("светлая", light), ("тёмная", dark)):
        for label, fg, bg, need in CONTRAST_PAIRS:
            got = _contrast(palette[fg], palette[bg])
            if got < need:
                failures.append(f"{theme_name}: {label} — {got:.2f}, нужно {need}")
    assert not failures, "контраст ниже порога:\n" + "\n".join(failures)
