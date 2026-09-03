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


# Пара «что читаем — на чём читаем» и порог. Матрица строится
# перемножением, а не перечислением: до редизайна пар было двенадцать, и
# каждая новая поверхность требовала вспомнить, какой текст на ней
# окажется. Забыть перемножение труднее, чем дописать строку.
#
# Пороги: 7.0 (WCAG AAA) для основного текста — его читают часами, и
# ночью именно он либо «выжигает» глаза, либо не читается; 4.5 (AA) для
# вторичного текста, смысловых цветов и надписи на кнопке; 3.0 (AA,
# критерий 1.4.11 «нетекстовый контраст») для приглушённых подписей, для
# обводки фокуса и для границы того, что нажимают и во что печатают.
SURFACES = ["--bg", "--bg-soft", "--bg-raised", "--bg-float", "--bg-sunk"]
TONES = ["--accent", "--ok", "--warn", "--danger"]


def _contrast_pairs() -> list[tuple[str, str, str, float]]:
    pairs: list[tuple[str, str, str, float]] = []
    for surface in SURFACES:
        pairs += [
            (f"основной текст на {surface}", "--ink", surface, 7.0),
            (f"вторичный текст на {surface}", "--ink-soft", surface, 4.5),
            (f"приглушённый текст на {surface}", "--ink-faint", surface, 3.0),
            (f"ссылка на {surface}", "--accent", surface, 4.5),
            (f"граница поля ввода на {surface}", "--control-line", surface, 3.0),
        ]
    for tone in TONES:
        soft = tone + "-soft"
        pairs += [
            (f"{tone} на своей подложке", tone, soft, 4.5),
            (f"основной текст на подложке {tone}", "--ink", soft, 7.0),
            (f"вторичный текст на подложке {tone}", "--ink-soft", soft, 4.5),
        ]
    pairs += [
        ("текст на кнопке-акценте", "--accent-on", "--accent", 4.5),
        ("текст на кнопке-акценте под курсором", "--accent-on", "--accent-hover", 4.5),
        ("обводка фокуса на полотне", "--focus", "--bg", 3.0),
        ("обводка фокуса на карточке", "--focus", "--bg-raised", 3.0),
        ("вывод терминала", "--term-ink", "--term-bg", 4.5),
    ]
    return pairs


CONTRAST_PAIRS = _contrast_pairs()


def test_both_themes_are_readable_by_wcag() -> None:
    """Контраст текста к фону — счётом, а не «на глаз при дневном свете».

    Тёмная тема правится подбором, и подбор легко уводит подписи в
    нечитаемое: в тёмной палитре разница между `--ink-soft` и
    `--ink-faint` на глаз почти незаметна, а в числах это разница между
    8.6 и 5.2. Порог берётся один раз здесь, а не на каждой правке.
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
    assert len(CONTRAST_PAIRS) > 40, "матрица неожиданно мала — тест смотрит не туда"



# ---------------------------------------------------------------- тема

# Список слов, которыми в файле объявлены оба тёмных блока. Пары
# «регулярка → человеческое имя» держатся здесь, потому что ими
# пользуются сразу несколько тестов ниже.
DARK_SYSTEM_RE = (r'@media \(prefers-color-scheme: dark\) \{\s*'
                  r':root:not\(\[data-theme="light"\]\) \{(.*?)\n  \}')
DARK_MANUAL_RE = r':root\[data-theme="dark"\] \{(.*?)\n\}'


def _declarations(block: str) -> dict[str, str]:
    """Имя → значение, без учёта отступов и порядка строк."""
    return {n: v.strip() for n, v in re.findall(r"(--[a-z0-9-]+):\s*([^;]+);", block)}


def test_the_two_dark_blocks_say_exactly_the_same_thing() -> None:
    """Тёмная палитра написана дважды, и разъехаться ей нельзя.

    Один блок работает по системной настройке, второй — по тумблеру.
    Расхождение видно только тому, у кого система стоит светлой, а
    тумблер тёмным (или наоборот), — то есть почти никому и почти
    никогда. Поэтому сверяется машиной, а не глазами.
    """
    system = _declarations(re.search(DARK_SYSTEM_RE, CSS, re.S).group(1))
    manual = _declarations(re.search(DARK_MANUAL_RE, CSS, re.S).group(1))
    assert system, "системный тёмный блок не нашёлся — тест смотрит не туда"
    only_system = sorted(set(system) - set(manual))
    only_manual = sorted(set(manual) - set(system))
    assert not only_system, f"есть только в системном тёмном блоке: {only_system}"
    assert not only_manual, f"есть только в ручном тёмном блоке: {only_manual}"
    differ = sorted(n for n in system if system[n] != manual[n])
    assert not differ, "два тёмных блока разошлись значениями: " + ", ".join(
        f"{n} = {system[n]} против {manual[n]}" for n in differ)


# Лестница поверхностей от утопленной к всплывающей. В тёмной теме это
# единственный носитель глубины: тень на тёмном фоне не видна.
ELEVATION = ["--bg-sunk", "--bg", "--bg-soft", "--bg-raised", "--bg-float"]


def test_dark_elevation_is_a_monotonic_ladder() -> None:
    """Чем ближе поверхность к человеку, тем она светлее. Без исключений.

    Ступень должна быть заметна и не должна быть полосой: разница по
    относительной светимости берётся в разах, а не в единицах hex, —
    глаз считает именно так. Порог снизу (1.2) ловит слипшиеся ступени,
    сверху (2.2) — лестницу, на которой карточка выглядит наклейкой.
    """
    dark = _palette(DARK_MANUAL_RE)
    steps = [_luminance(dark[name]) for name in ELEVATION]
    for lower, upper, a, b in zip(steps, steps[1:], ELEVATION, ELEVATION[1:]):
        ratio = (upper + 0.005) / (lower + 0.005)
        assert 1.2 <= ratio <= 2.2, (
            f"ступень {a} → {b} = x{ratio:.2f}: "
            f"{'ступени слиплись' if ratio < 1.2 else 'ступень слишком крупная'}")

    light = _palette(r":root \{(.*?)\n\}")
    assert _luminance(light["--bg-sunk"]) < _luminance(light["--bg"]), \
        "в светлой теме жёлоб обязан быть темнее полотна"


def test_hover_lifts_never_sinks() -> None:
    """Наведение не красится цветом жёлоба.

    До редизайна `:hover` ставил `--bg-sunk` — в светлой теме это чуть
    темнее полотна и читается правильно, а в тёмной ровно наоборот:
    строка под курсором ТЕМНЕЛА, то есть уезжала от человека вместо того,
    чтобы к нему подняться. Теперь наведение — полупрозрачная плёнка
    `--hover` поверх той поверхности, на которой элемент лежит, и правило
    одно на обе темы.
    """
    sinking = [rule.strip() for rule in re.findall(r"[^{}]*:hover[^{}]*\{[^}]*\}", CSS)
               if "--bg-sunk" in rule]
    assert not sinking, "наведение красится в цвет жёлоба:\n" + "\n".join(sinking)

    light = _declarations(re.search(r":root \{(.*?)\n\}", CSS, re.S).group(1))
    dark = _declarations(re.search(DARK_MANUAL_RE, CSS, re.S).group(1))
    assert light["--hover"].startswith("rgba("), "--hover обязан быть полупрозрачным"
    assert dark["--hover"].startswith("rgba("), "--hover обязан быть полупрозрачным"


def test_the_page_canvas_is_never_used_as_a_raised_surface() -> None:
    """`--bg` красит только полотно, и красит его только `body`.

    В светлой теме полотно белое, то есть светлее любой панели, и
    `background: var(--bg)` на карточке внутри панели читается как
    «поднято». В тёмной ровно наоборот: полотно темнее панели, и та же
    строка топит элемент. Так утонул блок текущего этапа в дереве — его
    видно на снимке экрана, а не в тестах, поэтому правило записано.
    Поднятому положено `--bg-raised`, всплывающему `--bg-float`.
    """
    rules = re.findall(r"([^{}]*)\{([^}]*)\}", CSS)
    guilty = [sel.strip() for sel, body in rules
              if re.search(r"background(-color)?:\s*var\(--bg\)\s*[;}]", body)
              and sel.strip() != "body"]
    assert not guilty, f"полотно страницы использовано как поднятая поверхность: {guilty}"


def test_the_page_does_not_flash_the_wrong_theme_on_load() -> None:
    """Тема — до стилей, переходы — не в первый кадр.

    Два независимых источника мигания. Первый: `data-theme` проставлен
    позже, чем браузер применил CSS, — окно моргает светлым. Второй
    появился вместе с общим переходом цвета: страница начинает жизнь со
    светлой палитрой, скрипт ставит тёмную, и переход честно анимирует
    этот переезд. Гасится `data-boot`, который снимается через два кадра
    в том же inline-скрипте — не в `app.js`, иначе переходы зависели бы
    от того, загрузился ли он.
    """
    head = HTML[:HTML.index("</head>")]
    script_at = head.index("<script>")
    styles = [head.index(m.group(0)) for m in re.finditer(r"<link[^>]+stylesheet[^>]*>", head)]
    assert styles, "в <head> нет ни одной таблицы стилей — тест смотрит не туда"
    assert script_at < min(styles), \
        "скрипт темы стоит ниже таблиц стилей: тема успевает моргнуть"

    assert 'dataset.boot' in head, "первый кадр не защищён от анимации перехода"
    assert 'requestAnimationFrame' in head, "`data-boot` некому снять"
    boot = re.search(r"((?::root\[data-boot\][^{,]*,\s*)*:root\[data-boot\][^{,]*)\{([^}]*)\}",
                     CSS)
    assert boot, "в CSS нет правила, гасящего переходы на старте"
    selectors = {s.strip() for s in boot.group(1).split(",") if s.strip()}
    assert ":root[data-boot] *" in selectors, \
        f"правило старта не покрывает все элементы, только {sorted(selectors)}"
    assert "transition: none !important" in boot.group(2), \
        "правило старта не гасит переход или гасится авторским правилом ниже"
    assert "dataset.boot" not in JS, \
        "`data-boot` снимается в app.js: переходы не должны зависеть от его загрузки"


def test_theme_switch_timing_agrees_between_css_and_script() -> None:
    """Длительность перехода темы записана в двух файлах — они обязаны сойтись.

    В CSS её задаёт `:root[data-switching]`, в скрипте по ней заводится
    таймер, снимающий тот же атрибут. Если скрипт снимет раньше — переход
    оборвётся на середине и доиграет рывком.
    """
    block = re.search(r":root\[data-switching\] \{(.*?)\n\}", CSS, re.S)
    assert block, "в CSS нет блока `:root[data-switching]`"
    css_ms = int(re.search(r"--dur-theme:\s*(\d+)ms", block.group(1)).group(1))
    js_ms = int(re.search(r"THEME_SWITCH_MS\s*=\s*(\d+)", JS).group(1))
    assert js_ms == css_ms, f"CSS ждёт {css_ms} мс, скрипт снимает атрибут через {js_ms}"
    slack = re.search(r"THEME_SWITCH_MS \+ (\d+)", JS)
    assert slack and int(slack.group(1)) > 0, \
        "таймер снимает `data-switching` ровно в момент конца перехода, без запаса на кадр"


def test_motion_is_declared_once_and_respects_the_system_setting() -> None:
    """Переход цвета — общим правилом, поимённо по свойствам, и с оговоркой.

    `transition: all` анимировал бы и раскладку: подстановка длинного
    названия шага поехала бы по экрану. А человек, попросивший систему
    убрать анимацию, обязан её не увидеть.
    """
    rule = re.search(r"@media \(prefers-reduced-motion: no-preference\) \{\s*"
                     r"\*, \*::before, \*::after \{(.*?)\n  \}", CSS, re.S)
    assert rule, "общего правила перехода нет или оно не под prefers-reduced-motion"
    body = rule.group(1)
    code = re.sub(r"/\*.*?\*/", "", CSS, flags=re.S)
    assert "transition: all" not in code, "`transition: all` анимирует и раскладку"
    for prop in ("background-color", "border-color", "color", "box-shadow"):
        assert prop in body, f"переход не объявлен для {prop}"


def test_no_colour_or_duration_is_written_as_a_bare_number_outside_the_tokens() -> None:
    """Цвет мимо палитры — тот же класс ошибки, что число программы в HTML.

    Он не переопределится в тёмной теме и останется светлым пятном. Всё,
    что цвет, объявлено переменной в `:root`; ниже по файлу цвета
    встречаются только через `var(--…)`.
    """
    tail = CSS[CSS.index(":root[data-theme=\"light\"] { color-scheme: light; }"):]
    stray = re.findall(r"(?<!\w)#[0-9a-fA-F]{3,8}\b", tail)
    assert not stray, f"цвет мимо палитры в теле файла: {sorted(set(stray))}"


def test_every_declared_token_is_actually_used() -> None:
    """Мёртвая переменная — обещание, за которым ничего нет.

    Исключение объявлено вслух: `--s-*` и `--t-*` — это шкалы, они
    объявлены целиком нарочно, и дыра в шкале хуже неиспользованного
    значения.
    """
    declared = set(re.findall(r"^\s*(--[a-z0-9-]+):", CSS, re.MULTILINE))
    used = set(re.findall(r"var\((--[a-z0-9-]+)", CSS))
    scales = {n for n in declared if re.match(r"^--[st]-", n)}
    dead = sorted(declared - used - scales)
    assert not dead, f"объявлены и нигде не используются: {dead}"
