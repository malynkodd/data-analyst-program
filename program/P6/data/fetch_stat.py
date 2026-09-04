"""Снапшот P6 — Держстат SDMX 2.1, два потока.

1. Розничная торговля, индекс оборота к тому же месяцу предыдущего
   года, по регионам (`DF_SALE_AND_STOCKS_OF_GOODS_RETAIL_M`,
   `INDICATOR=IDX_TRNVR_RTL_TRADE_VOL`, `BASE=UNADJ_CORR_MON_PREV_Y`,
   `FREQ=M`) — сигнал «спрос по региону растёт/падает», но по всей
   рознице целиком, БЕЗ разбивки по товарной категории — этот поток
   такой разбивки не даёт вообще (найдено прогоном, не в описании
   blueprint). Это первая, структурная причина, по которой на вопрос
   «где по НАШЕЙ категории растёт спрос» ответить нельзя точно.
2. Импорт обуви (группа 64 УКТВЭД), Украина в целом, все страны-партнёры
   свёрнуты (`AREA=_T`) — `DF_EXTERNAL_TRADE_INDIVIDUAL_GOODS_BY_COUNTRIES`.
   **Запрос `all/all` (все товары, все страны) на этом потоке не
   отвечает — измерено прогоном 2026-08-22: 40 с, обрыв соединения,
   без единого байта тела ответа** (`research/sources-gate.md`, §4,
   уже фиксировало 500 на соседнем потоке). Причина — размерный
   перекрёсток 22855 кодов GOODS x ~270 кодов AREA. Решение — резать
   по ключу: один код GOODS (`126400000000` = Группа 64, обувь),
   AREA=`_T` (в целом, не по странам) — ответ падает до 37 КБ, 0.9 с.

SEED не нужен — данные реальные, снимок фиксируется датой запуска.
"""
import argparse
import csv
import hashlib
import re
import sys
import time
import urllib.request
from pathlib import Path

# Кириллица в консоли не полагается на кодировку терминала
# (решение 17; симуляция 2026-09-04, дефект M9-1: без этой строки
# скрипт падал с UnicodeEncodeError, допечатав часть вывода).
sys.stdout.reconfigure(encoding="utf-8")

HEADERS = {"User-Agent": "data-analyst-program research (P6 snapshot)"}
HERE = Path(__file__).resolve().parent
# Каталог выгрузки. Значение по умолчанию — не snapshot/: повторная
# выгрузка не должна затирать файл, с которым её же велено сравнивать
# (симуляция 2026-09-04, дефект P3-1). Переопределяется --out.
OUT_DIR = HERE / "refetch"

BASE_URL = "https://stat.gov.ua/sdmx/workspaces/default:integration/registry/sdmx/2.1"

# Коды КАТОТТГ регионов (CL_KATOTTG, взято из снимка DSD_SALE_AND_STOCKS_OF_GOODS_RETAIL_M
# с `references=all`, 2026-08-22) — стабильный официальный классификатор,
# не меняется между прогонами, поэтому не тянется повторно каждый раз.
# Названия регионов — как в источнике (Держстат), не переводятся.
REGIONS = {
    "UA00000000000000000": "Україна",
    "UA01000000000013043": "Автономна Республіка Крим",
    "UA05000000000010236": "Вінницька",
    "UA07000000000024379": "Волинська",
    "UA12000000000090473": "Дніпропетровська",
    "UA14000000000091971": "Донецька",
    "UA18000000000041385": "Житомирська",
    "UA21000000000011690": "Закарпатська",
    "UA23000000000064947": "Запорізька",
    "UA26000000000069363": "Івано-Франківська",
    "UA32000000000030281": "Київська",
    "UA35000000000016081": "Кіровоградська",
    "UA44000000000018893": "Луганська",
    "UA46000000000026241": "Львівська",
    "UA48000000000039575": "Миколаївська",
    "UA51000000000030770": "Одеська",
    "UA53000000000028050": "Полтавська",
    "UA56000000000066151": "Рівненська",
    "UA59000000000057109": "Сумська",
    "UA61000000000060328": "Тернопільська",
    "UA63000000000041885": "Харківська",
    "UA65000000000030969": "Херсонська",
    "UA68000000000099709": "Хмельницька",
    "UA71000000000010357": "Черкаська",
    "UA73000000000044923": "Чернівецька",
    "UA74000000000025378": "Чернігівська",
    "UA80000000000093317": "Київ",
    "UA85000000000065278": "Севастополь",
}

SERIES_RE = re.compile(r"<Series ([^>]+)>(.*?)</Series>", re.S)
OBS_RE = re.compile(r'TIME_PERIOD="([^"]+)" OBS_VALUE="([^"]+)"')
ATTR_RE = re.compile(r'(\w+)="([^"]*)"')


def fetch(url: str, retries: int = 3, timeout: int = 60) -> str:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8")
        except Exception as exc:  # noqa: BLE001
            if attempt == retries - 1:
                raise
            time.sleep(2)


def parse_series(xml_text: str):
    for attrs_str, body in SERIES_RE.findall(xml_text):
        attrs = dict(ATTR_RE.findall(attrs_str))
        obs = OBS_RE.findall(body)
        yield attrs, obs


def fetch_retail() -> None:
    url = (f"{BASE_URL}/data/SSSU,DF_SALE_AND_STOCKS_OF_GOODS_RETAIL_M,4.0.0/all/all")
    xml_text = fetch(url)
    out_path = OUT_DIR / "retail_turnover_by_region.csv"
    n = 0
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["region_code", "region_name", "period", "idx_yoy_pct"])
        for attrs, obs in parse_series(xml_text):
            if attrs.get("INDICATOR") != "IDX_TRNVR_RTL_TRADE_VOL":
                continue
            if attrs.get("BASE") != "UNADJ_CORR_MON_PREV_Y":
                continue
            region = attrs.get("REGION")
            name = REGIONS.get(region, region)
            for period, value in obs:
                w.writerow([region, name, period, value])
                n += 1
    digest = hashlib.sha256(out_path.read_bytes()).hexdigest()
    print(f"{out_path.name}: {n} строк, sha256 {digest}")


def fetch_footwear() -> None:
    # GOODS=126400000000 (Группа 64 УКТВЭД, обувь), AREA=_T (в целом),
    # REGION=UA00... (Украина) — ключ из 7 позиций: REGION.GOODS.AREA.
    # INDICATOR.TYPE_OF_MEASURE.UNITS_OF_MEASURE_ETG.FREQ, пустые
    # позиции = «все».
    key = "UA00000000000000000.126400000000._T...."
    url = f"{BASE_URL}/data/SSSU,DF_EXTERNAL_TRADE_INDIVIDUAL_GOODS_BY_COUNTRIES,3.0.0/{key}/all"
    xml_text = fetch(url)
    out_path = OUT_DIR / "footwear_imports.csv"
    n = 0
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["period", "cost_usd_thousand", "qty_pairs"])
        cost_by_period = {}
        qty_by_period = {}
        for attrs, obs in parse_series(xml_text):
            if attrs.get("INDICATOR") != "IMP_GOODS" or attrs.get("FREQ") != "M":
                continue
            if attrs.get("TYPE_OF_MEASURE") == "MEASURE_COST":
                for period, value in obs:
                    cost_by_period[period] = value
            elif attrs.get("TYPE_OF_MEASURE") == "MEASURE_NUM" and attrs.get("UNITS_OF_MEASURE_ETG") == "715":
                for period, value in obs:
                    qty_by_period[period] = value
        periods = sorted(set(cost_by_period) | set(qty_by_period))
        for period in periods:
            w.writerow([period, cost_by_period.get(period, ""), qty_by_period.get(period, "")])
            n += 1
    digest = hashlib.sha256(out_path.read_bytes()).hexdigest()
    print(f"{out_path.name}: {n} строк, sha256 {digest}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=HERE / "refetch",
        help=(
            "каталог, куда писать выгрузку. По умолчанию — `refetch/` рядом со `snapshot/`: снапшот проекта повторной выгрузкой не перезаписывается, потому что сравнивать надо с ним, а не вместо него. Чтобы всё-таки переписать снапшот, каталог называется явно: --out snapshot"
        ),
    )
    return parser.parse_args()


def main() -> None:
    global OUT_DIR
    OUT_DIR = parse_args().out
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"каталог выгрузки: {OUT_DIR}")
    print("Отрицательный пример — 'all/all' без нарезки по ключу для потока внешней "
          "торговли (research/sources-gate.md, §4/§9):")
    try:
        fetch(f"{BASE_URL}/data/SSSU,DF_EXTERNAL_TRADE_INDIVIDUAL_GOODS_BY_COUNTRIES,3.0.0/all/all",
              retries=1, timeout=40)
        print("  неожиданно ответил — перепроверить, дефект мог быть исправлен на источнике")
    except Exception as exc:  # noqa: BLE001
        print(f"  подтверждено: {exc!r}")
    print()
    fetch_retail()
    fetch_footwear()


if __name__ == "__main__":
    main()
