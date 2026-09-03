"""Живость ссылок репозитория — правило 3 CLAUDE.md.

«Каждая ссылка на ресурс проверена через fetch. Битые — удалять.»
Проверка одноразовой быть не может: объявления о вакансиях живут 4–8
недель [М], документация переезжает. Этот скрипт делает проверку
повторяемой.

Что он различает — четыре состояния, а не два:

* **живая** — код 2xx или 3xx (редирект, за которым не всегда можно
  проследовать: `aka.ms/pbidesktopstore` ведёт на схему
  `ms-windows-store://`);
* **закрыта для автоматических запросов** — 401/403/429. Это не мёртвая
  ссылка: страница обычно открывается в браузере. Измерено 2026-08-23:
  все такие ответы пришли с `indeed.com`, `wellfound.com` и подобных
  площадок с защитой от ботов, а не с площадок, где вакансия снята;
* **известная мёртвая** — перечислена в `research/dead-links.md`:
  цитата вакансии, умершая после сбора выборки, или эндпоинт, чей отказ
  и есть измерение. Выводится как `[ЗНАЕМ]`, кода 1 не даёт;
* **мёртвая** — 404, 410, 5xx, отказ соединения, и в реестре её нет.
  Только она даёт код возврата 1.

`data.gov.ua` не запрашивается вовсе: его `robots.txt` отдельными блоками
запрещает ClaudeBot и другие AI-краулеры (решение 36
`design/decisions.md`, `research/sources-gate.md`, §1). Ссылки на него
выводятся строкой «пропущено», а не проверяются молча.

Запуск:
    python tools\\check_links.py
    python tools\\check_links.py --timeout 30 --jobs 8
"""
import argparse
import os
import re
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
URL_RE = re.compile(r'https?://[^\s)\]<>"`]+')
TRAILING = ".,;:"

# Каталоги, которые не являются содержанием репозитория.
SKIP_DIRS = {".venv", "node_modules", "__pycache__", ".git"}

# Источники, к которым агент не ходит по решению 36. Список именно
# доменный: запрет привязан к robots.txt конкретного сайта, а не к типу
# ресурса.
ROBOTS_FORBIDDEN = {"data.gov.ua", "www.data.gov.ua"}

# Локальный адрес — не внешний ресурс, а адрес собственного приложения
# app/ (решение 40), которым HANDOFF.md/app/README.md объясняют, как его
# открыть. Fetch снаружи никогда не ответит на 127.0.0.1, вне зависимости
# от того, жив ли сам app/ — правило 3 CLAUDE.md про мёртвые ссылки-цитаты
# сюда не относится. Найдено этим ревью 2026-09-03: без исключения адрес
# ложно считался «новой мёртвой ссылкой».
LOCAL_HOSTS = {"127.0.0.1", "localhost"}

# Реестр известных мёртвых ссылок (решение 39). Адреса берутся из того же
# текста, который читает человек, а не из отдельного списка, который
# разъедется с ним при первой правке.
DEAD_REGISTRY = ROOT / "research" / "dead-links.md"
REGISTRY_URL = re.compile(r"`(https?://[^`]+)`")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
BOT_WALL = {401, 403, 429}


def collect() -> dict[str, list[str]]:
    urls: dict[str, list[str]] = defaultdict(list)
    for path in ROOT.rglob("*.md"):
        rel = path.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        for raw in URL_RE.findall(path.read_text(encoding="utf-8")):
            urls[raw.rstrip(TRAILING)].append(rel.as_posix())
    return dict(urls)


def known_dead() -> set[str]:
    """Адреса из research/dead-links.md. Отсутствие файла — не молчаливое
    «реестр пуст», а [FAIL]: без реестра проверка не отличает известную
    мёртвую ссылку от новой."""
    if not DEAD_REGISTRY.exists():
        print(f"[FAIL] нет реестра research/dead-links.md (решение 39) — "
              f"известные мёртвые ссылки не отличить от новых")
        return set()
    return set(REGISTRY_URL.findall(DEAD_REGISTRY.read_text(encoding="utf-8")))


def curl_status(url: str, timeout: int) -> int | str:
    """Запасной запрос через curl.

    Не перестраховка: измерено 2026-08-23 — `ind.nl`, `fragomen.com` и
    `make-it-in-germany.com` отдают urllib ошибку соединения и при этом
    отвечают 200 на curl с тем же User-Agent (разница в согласовании
    TLS/HTTP2). Без этого запасного пути проверка объявляла бы живые
    ссылки мёртвыми, а правило 3 CLAUDE.md велит мёртвые удалять — то
    есть ложное срабатывание здесь стоит удалённого источника."""
    import subprocess

    try:
        done = subprocess.run(
            ["curl", "-s", "-o", os.devnull, "-w", "%{http_code}",
             "--max-time", str(timeout), "-A", UA, "-L", url],
            capture_output=True, text=True, timeout=timeout + 10,
        )
    except Exception as exc:
        return type(exc).__name__
    code = (done.stdout or "").strip()
    if code.isdigit() and code != "000":
        return int(code)
    return "нет соединения"


def probe(url: str, timeout: int) -> tuple[str, int | str]:
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return url, response.status
    except urllib.error.HTTPError as exc:
        return url, exc.code
    except Exception:  # соединение, DNS, TLS, таймаут — переспрашиваем curl
        return url, curl_status(url, timeout)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=25)
    parser.add_argument("--jobs", type=int, default=8)
    args = parser.parse_args()

    urls = collect()
    skipped = {u: f for u, f in urls.items() if urlparse(u).netloc in ROBOTS_FORBIDDEN}
    local = {
        u: f for u, f in urls.items()
        if u not in skipped and (urlparse(u).hostname or "") in LOCAL_HOSTS
    }
    to_check = {u: f for u, f in urls.items() if u not in skipped and u not in local}

    print(f"Ссылок в *.md: {len(urls)}; проверяется {len(to_check)}, "
          f"пропущено по решению 36: {len(skipped)}, локальных: {len(local)}\n")

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = dict(pool.map(lambda u: probe(u, args.timeout), to_check))

    # 3xx — живая ссылка: urllib отдаёт код редиректа там, где следовать
    # ему некуда (aka.ms/pbidesktopstore ведёт на схему ms-windows-store://).
    alive = [u for u, s in results.items() if isinstance(s, int) and 200 <= s < 400]
    walled = [u for u, s in results.items() if s in BOT_WALL]
    broken = [u for u, s in results.items() if u not in alive and u not in walled]
    registry = known_dead()
    known = [u for u in broken if u in registry]
    dead = [u for u in broken if u not in registry]

    for url in sorted(dead):
        where = ", ".join(sorted(set(to_check[url])))
        print(f"[FAIL] {results[url]} {url}\n       где: {where}")
    for url in sorted(known):
        print(f"[ЗНАЕМ] {results[url]} {url} — в реестре research/dead-links.md")
    for url in sorted(walled):
        print(f"[WARN] {results[url]} {url} — закрыт для автоматических запросов")
    for url in sorted(skipped):
        print(f"[SKIP] {url} — robots.txt запрещает агенту (решение 36)")
    for url in sorted(local):
        print(f"[SKIP] {url} — локальный адрес app/, не внешний ресурс")
    for url in sorted(u for u in registry if u in alive):
        print(f"[WARN] {url} снова отвечает {results[url]} — строку в "
              f"research/dead-links.md пора убрать")

    print(
        f"\nЖивых: {len(alive)}; закрытых для автозапросов: {len(walled)}; "
        f"известных мёртвых: {len(known)}; новых мёртвых: {len(dead)}; "
        f"пропущено: {len(skipped)}; локальных: {len(local)}"
    )
    if dead:
        print(
            "Новая битая ссылка: ссылка-ресурс удаляется или заменяется рабочей "
            "(правило 3 CLAUDE.md), ссылка-цитата заносится в реестр (решение 39)."
        )
        return 1
    print("Новых мёртвых ссылок нет.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
