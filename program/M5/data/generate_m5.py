"""Генератор сквозного датасета модуля M5 (Python).

Запуск (после `pip install openpyxl` — см. `program/M5/step-00.md`,
«Предусловие модуля»):

    python generate_m5.py

Пишет папку `raw/` рядом с собой — четыре файла, три формата, ровно те,
которых требует умение B1 части 1 blueprint («папка из 4 файлов
csv/xlsx/json с разными кодировками, разделителями и заголовками»):

    payouts_2026_q1.csv  — cp1251, разделитель `;`, десятичная запятая,
                           даты `дд.мм.рррр`
    payouts_2026_q2.csv  — UTF-8 с BOM, разделитель `,`, десятичная
                           точка, даты ISO, ДВЕ КОЛОНКИ ПЕРЕИМЕНОВАНЫ
                           (`payout_date`→`paid_at`, `amount`→`total`)
                           и статусы в нижнем регистре
    partners.xlsx        — два листа: «Партнери» (шапка в две строки,
                           дубли, часть записей без кода) и «Курс НБУ»
                           (курс USD/UAH только по рабочим дням)
    fees_api.json        — выгрузка «API комиссий»: вложенная структура
                           со страницами; последний элемент страницы
                           повторён первым элементом следующей —
                           типовой дефект пагинации

Домен — fintech: платёжный сервис, выплаты партнёрам (решение 21, п. 2).
Данные синтетические. Категория датасета и обоснование отступления от
раздела 1.3 скилла curriculum-design — `program/M5/step-00.md`.

**Папка `raw/` не коммитится** (корневой `.gitignore`): в репозитории —
генератор, скрипт эталонов и эталонные CSV. Скрипт печатает после
генерации число строк и sha256 каждого файла — учащийся сверяет их с
`reference_answers.md`, раздел «Контрольная точка», ДО того, как
приступать к задачам шагов.

Детерминированность: `SEED` задан до первого обращения к генератору
случайных чисел, порядок вызовов фиксирован циклами. Повторный запуск
даёт побайтово те же файлы (проверяется sha256 из контрольной точки).

Кодировки заданы явно в каждом открытии файла (решение 17). Перевод
строки в CSV — CRLF, как у генератора M4.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import re
import sys
import zipfile
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook

if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

SEED = 20260817
RNG = random.Random(SEED)

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"

Q1_START, Q1_END = date(2026, 1, 1), date(2026, 3, 31)
Q2_START, Q2_END = date(2026, 4, 1), date(2026, 6, 30)

# Курс начинается позже первой выплаты — намеренно. Валютные выплаты
# первых дней января остаются без курса и без более раннего курса в ряду:
# это третья, самая неприятная причина потери строк в B2 — не «нет ключа»
# и не «разный регистр», а «ключ есть, но ряд начинается позже».
RATES_START = date(2026, 1, 5)

PAGE_SIZE = 300

CITIES = ["Київ", "Львів", "Одеса", "Харків", "Дніпро", "Вінниця",
          "Запоріжжя", "Ужгород"]

# Тариф партнёра: имя и ставка комиссии. Ставка нужна генератору, чтобы
# комиссия в `fees_api.json` не была случайным числом: она считается от
# суммы выплаты, и учащийся, посчитавший take rate, получает величину,
# близкую к ставке тарифа, — иначе сверка с эталоном ничего не значит.
PLANS = [("Базовий", Decimal("0.025")), ("Стандарт", Decimal("0.020")),
         ("Преміум", Decimal("0.016"))]

FORMS = ["ТОВ", "ФОП", "ПП"]
WORDS_A = ["Світло", "Кобза", "Дніпро", "Явір", "Барвінок", "Каштан",
           "Смерека", "Полтва", "Либідь", "Хортиця", "Оболонь", "Січ",
           "Троянда", "Верес", "Калина", "Лелека", "Скіф", "Тиса",
           "Черемош", "Ятрань"]
WORDS_B = ["Маркет", "Логістик", "Трейд", "Сервіс", "Груп"]

MODIFIED_TAG = re.compile(rb"<dcterms:modified[^>]*>[^<]*</dcterms:modified>")

TWO = Decimal("0.01")
FOUR = Decimal("0.0001")


def money(value: Decimal) -> Decimal:
    return value.quantize(TWO, rounding=ROUND_HALF_UP)


def business_days(start: date, end: date) -> list[date]:
    days, cur = [], start
    while cur <= end:
        if cur.weekday() < 5:
            days.append(cur)
        cur += timedelta(days=1)
    return days


def build_partners() -> list[dict]:
    """60 партнёров. Код — восьмизначный, как ЄДРПОУ; у пяти его нет
    вовсе (в CRM запись создали вручную) — такие сопоставляются только
    по названию."""
    names: list[str] = []
    for word_b in WORDS_B:
        for word_a in WORDS_A:
            names.append(f"{FORMS[len(names) % len(FORMS)]} «{word_a} {word_b}»")
    partners = []
    for i, name in enumerate(names[:60]):
        plan_name, plan_rate = PLANS[i % len(PLANS)]
        partners.append({
            "code": f"{30000001 + i * 7}",
            "name": name,
            "city": CITIES[i % len(CITIES)],
            "plan": plan_name,
            "rate": plan_rate,
            "status": "активний" if i % 11 else "припинено",
        })
    for i in (4, 17, 38, 45, 59):  # пять записей без кода
        partners[i]["code"] = ""
    return partners


def noisy_name(name: str) -> str:
    """Название партнёра в выгрузке выплат приходит текстом и не совпадает
    со справочником побайтово: лишние пробелы, снятые кавычки, регистр.
    Ровно то, из-за чего join по названию теряет строки, если название не
    нормализовать."""
    roll = RNG.random()
    if roll < 0.15:
        return f"  {name} "
    if roll < 0.25:
        return name.replace("«", "").replace("»", "")
    if roll < 0.30:
        return name.upper()
    if roll < 0.36:
        return name.replace(" ", "  ")
    return name


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)

    partners = build_partners()
    # Два кода, которых нет в справочнике: партнёров подключили, а
    # выгрузку CRM не обновили. Их выплаты теряются на join'е со
    # справочником — и это единственная потеря, которую нельзя починить
    # нормализацией.
    ghosts = [{"code": "39990001", "name": "ТОВ «Нова Пошта Пей»",
               "rate": Decimal("0.021")},
              {"code": "39990002", "name": "ФОП Ткаченко О. В.",
               "rate": Decimal("0.024")}]

    rate_days = business_days(RATES_START, Q2_END)
    usd_rate: dict[date, Decimal] = {}
    value = Decimal("41.8000")
    for day in rate_days:
        value = value + Decimal(str(round(RNG.uniform(-0.18, 0.19), 4)))
        value = min(max(value, Decimal("40.5000")), Decimal("43.9000"))
        usd_rate[day] = value.quantize(FOUR, rounding=ROUND_HALF_UP)

    payouts: list[dict] = []
    payout_id = 1000001
    day = Q1_START
    while day <= Q2_END:
        for _ in range(RNG.randint(18, 28)):
            if RNG.random() < 0.004:
                who = RNG.choice(ghosts)
                partner_rate = who["rate"]
            else:
                who = RNG.choice(partners)
                partner_rate = who["rate"]
            currency = "USD" if RNG.random() < 0.08 else "UAH"
            if currency == "USD":
                amount = money(Decimal(str(round(RNG.uniform(120, 3000), 2))))
            else:
                amount = money(Decimal(str(round(RNG.uniform(480, 92000), 2))))
            roll = RNG.random()
            status = "PAID" if roll < 0.85 else ("PENDING" if roll < 0.95 else "FAILED")
            payouts.append({
                "payout_id": payout_id,
                # Код есть не всегда: в 6% строк выгрузка отдаёт только
                # название партнёра.
                "partner_code": "" if RNG.random() < 0.06 else who["code"],
                "partner_name": noisy_name(who["name"]),
                "date": day,
                "amount": amount,
                "currency": currency,
                "status": status,
                "rate": partner_rate,
            })
            payout_id += 1
        day += timedelta(days=1)

    # --- комиссии: только по выплаченным, с пропусками -------------------
    fee_items: list[dict] = []
    fees_skipped = 0
    fees_no_rate = 0
    for p in payouts:
        if p["status"] != "PAID":
            continue
        if p["currency"] == "USD":
            rate = usd_rate.get(p["date"])
            if rate is None:
                earlier = [d for d in usd_rate if d < p["date"]]
                rate = usd_rate[max(earlier)] if earlier else None
            if rate is None:
                # Комиссию в гривне посчитать нечем — курса нет ни на дату,
                # ни раньше. Запись не создаётся; строка выплаты останется
                # без комиссии, и это видно в отчёте B2, а не молча.
                fees_no_rate += 1
                continue
            amount_uah = money(p["amount"] * rate)
        else:
            amount_uah = p["amount"]
        if RNG.random() < 0.05:
            fees_skipped += 1  # комиссия ещё не рассчитана
            continue
        fee_items.append({
            "payout_id": p["payout_id"],
            "fee": {"amount": str(money(amount_uah * p["rate"])), "currency": "UAH"},
        })

    pages = []
    duplicated = 0
    for start in range(0, len(fee_items), PAGE_SIZE):
        chunk = fee_items[start:start + PAGE_SIZE]
        if pages:
            # Типовой дефект пагинации: последний элемент предыдущей
            # страницы приходит ещё раз первым элементом следующей.
            chunk = [pages[-1]["items"][-1]] + chunk
            duplicated += 1
        pages.append({"page": len(pages) + 1, "per_page": PAGE_SIZE, "items": chunk})

    payload = {
        "meta": {"source": "fees-api", "generated_for": "M5", "pages": len(pages)},
        "pages": pages,
    }
    fees_path = RAW / "fees_api.json"
    fees_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )

    # --- две выгрузки выплат ---------------------------------------------
    q1 = [p for p in payouts if p["date"] <= Q1_END]
    q2 = [p for p in payouts if p["date"] >= Q2_START]

    q1_path = RAW / "payouts_2026_q1.csv"
    with q1_path.open("w", encoding="cp1251", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\r\n")
        w.writerow(["payout_id", "partner_code", "partner_name",
                    "payout_date", "amount", "currency", "status"])
        for p in q1:
            w.writerow([p["payout_id"], p["partner_code"], p["partner_name"],
                        p["date"].strftime("%d.%m.%Y"),
                        f"{p['amount']:.2f}".replace(".", ","),
                        p["currency"], p["status"]])

    q2_path = RAW / "payouts_2026_q2.csv"
    with q2_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=",", lineterminator="\r\n")
        w.writerow(["payout_id", "partner_code", "partner_name",
                    "paid_at", "total", "currency", "status"])
        for p in q2:
            w.writerow([p["payout_id"], p["partner_code"], p["partner_name"],
                        p["date"].isoformat(), f"{p['amount']:.2f}",
                        p["currency"], p["status"].lower()])

    # --- справочник партнёров и курс: один файл, два листа ---------------
    wb = Workbook()
    ws = wb.active
    ws.title = "Партнери"
    ws.append(["Довідник партнерів. Вигрузка з CRM", None, None, None, None])
    ws.append(["Код ЄДРПОУ", "Назва партнера", "Місто", "Тариф", "Статус"])
    rows = [[p["code"], p["name"], p["city"], p["plan"], p["status"]] for p in partners]
    # Три дубля: партнёра завели дважды, во второй записи другой город.
    for i in (7, 23, 51):
        dup = list(rows[i])
        dup[2] = CITIES[(CITIES.index(dup[2]) + 3) % len(CITIES)]
        rows.append(dup)
    for row in rows:
        ws.append(row)

    ws2 = wb.create_sheet("Курс НБУ")
    ws2.append(["Дата", "USD/UAH"])
    for d in rate_days:
        ws2.append([d.isoformat(), str(usd_rate[d])])

    # xlsx — это zip, и sha256 у него по умолчанию НЕ воспроизводится:
    # openpyxl штампует в `docProps/core.xml` время сохранения, а zip —
    # время записи каждой позиции. Измерено: два прогона подряд дали
    # 7c449884… и 91ceb941… при побайтово одинаковых CSV и JSON. Поэтому
    # дата свойств фиксируется, а архив пересобирается с постоянными
    # метками — иначе контрольная точка из `reference_answers.md` не
    # сходилась бы ни у кого, включая автора.
    stamp = datetime(2026, 8, 17, 0, 0, 0)
    wb.properties.created = stamp
    wb.properties.modified = stamp
    wb.properties.creator = "generate_m5.py"
    wb.properties.lastModifiedBy = "generate_m5.py"
    buffer = BytesIO()
    wb.save(buffer)
    partners_path = RAW / "partners.xlsx"
    with zipfile.ZipFile(BytesIO(buffer.getvalue())) as src:
        with zipfile.ZipFile(partners_path, "w", zipfile.ZIP_DEFLATED) as dst:
            for name in src.namelist():
                data = src.read(name)
                if name == "docProps/core.xml":
                    # `wb.properties.modified` openpyxl при сохранении
                    # перезаписывает временем прогона — измерено: из десяти
                    # позиций архива расходилась ровно эта одна. Ставим дату
                    # текстом уже после сохранения.
                    data = MODIFIED_TAG.sub(
                        b'<dcterms:modified xsi:type="dcterms:W3CDTF">'
                        b"2026-08-17T00:00:00Z</dcterms:modified>", data)
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                dst.writestr(info, data)

    # --- контрольная точка ----------------------------------------------
    print("Датасет M5 записан в", RAW)
    print(f"SEED = {SEED}")
    print()
    print(f"{'файл':<22}{'строк данных':>14}  sha256")
    counts = {
        q1_path: len(q1),
        q2_path: len(q2),
        partners_path: len(rows),
        fees_path: sum(len(pg["items"]) for pg in pages),
    }
    for path, n in counts.items():
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        print(f"{path.name:<22}{n:>14}  {digest}")

    print()
    print("Инварианты (проверяются здесь, а не доверием к описанию):")
    ids = [p["payout_id"] for p in payouts]
    print(f"  payout_id уникальны: {len(set(ids)) == len(ids)} ({len(ids)} строк)")
    print(f"  q1 + q2 = все выплаты: {len(q1) + len(q2) == len(payouts)}")
    print(f"  партнёров в справочнике: {len(partners)}, из них без кода: "
          f"{sum(1 for p in partners if not p['code'])}, строк с дублями: {len(rows)}")
    print(f"  кодов вне справочника (выплаты-сироты): {len(ghosts)}")
    print(f"  дней с курсом: {len(rate_days)} "
          f"({RATES_START.isoformat()} .. {Q2_END.isoformat()}, только рабочие)")
    print(f"  страниц комиссий: {len(pages)}, дублей на границах страниц: {duplicated}")
    print(f"  комиссия не рассчитана (пропуск): {fees_skipped}")
    print(f"  комиссия невозможна — нет курса ни на дату, ни раньше: {fees_no_rate}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
