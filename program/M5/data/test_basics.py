"""Машинная сверка шага M5.02 «Язык-минимум аналитика» (умение B6).

Пятнадцать заданий раздела 1.4 — пятнадцать функций в вашем файле
`program\\M5\\work\\basics.py`. Этот файл их вызывает и сверяет с числами,
посчитанными независимо от вашего кода: эталоны получены прогоном
`reference_basics.py` на том же датасете (правило двойного авторства,
скилл curriculum-design, раздел 1.3), а не переписаны из вашего решения.

Запуск из корня репозитория:

    .venv\\Scripts\\python.exe -m pytest program\\M5\\data\\test_basics.py -q

Порог шага — 15 из 15 зелёных. Пятнадцать, а не двенадцать: каждая
функция проверяет одну конструкцию языка, и «почти все» здесь означает,
что одной конструкции вы не умеете.

Файл читает `raw/payouts_2026_q1.csv` и `raw/fees_api.json` сам, своим
кодом на стандартной библиотеке, и передаёт разобранные строки в ваши
функции аргументом. Ваши функции файлов не читают.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
WORK = HERE.parent / "work" / "basics.py"

# Эталоны. Посчитаны `reference_basics.py` на датасете SEED = 20260817,
# те же числа напечатаны в разделе 1.5 шага и в `reference_answers.md`.
# База для всех — только `payouts_2026_q1.csv`, 1996 строк.
EXPECTED = {
    "rows": 1996,
    "total_amount": 84632855.40,
    "paid_amount": 72219083.68,
    "count_by_status": {"PAID": 1699, "PENDING": 189, "FAILED": 108},
    "unique_codes": 57,
    "rows_without_code": 262,
    "bucket_counts": {"малая": 561, "средняя": 801, "крупная": 634},
    "big_paid": 213,
    "top5": [
        ("30000036", 1931580.12),
        ("30000099", 1703205.24),
        ("30000064", 1610306.54),
        ("30000078", 1565201.04),
        ("30000295", 1508713.23),
    ],
    "period": ("01.01.2026", "31.03.2026"),
    "page_item_counts": [300, 301, 301, 301, 301, 301, 301, 301, 301, 301, 301, 62],
    "fee_items": 3372,
    "unique_fee_ids": 3361,
    "name_variants_total": 251,
    "name_variants_30000036": 5,
    "first_name_30000036": "ПП  «Каштан  Маркет»",
}


def _load_basics():
    if not WORK.exists():
        pytest.skip(
            f"нет файла {WORK} — задание шага M5.02 ещё не выполнено; "
            "пропуск здесь не то же самое, что зелёный тест"
        )
    spec = importlib.util.spec_from_file_location("basics", WORK)
    module = importlib.util.module_from_spec(spec)
    sys.modules["basics"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def basics():
    return _load_basics()


@pytest.fixture(scope="module")
def rows():
    path = RAW / "payouts_2026_q1.csv"
    if not path.exists():
        pytest.skip(f"нет файла {path} — запустите generate_m5.py (шаг M5.01)")
    with path.open(encoding="cp1251", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


@pytest.fixture(scope="module")
def pages():
    path = RAW / "fees_api.json"
    if not path.exists():
        pytest.skip(f"нет файла {path} — запустите generate_m5.py (шаг M5.01)")
    return json.loads(path.read_text(encoding="utf-8"))["pages"]


def _call(module, name, *args):
    fn = getattr(module, name, None)
    if fn is None:
        pytest.fail(f"в basics.py нет функции {name}()")
    return fn(*args)


def test_00_dataset_is_the_same(rows):
    assert len(rows) == EXPECTED["rows"]


def test_01_to_amount(basics):
    assert _call(basics, "to_amount", "49088,78") == pytest.approx(49088.78)
    assert _call(basics, "to_amount", "121,39") == pytest.approx(121.39)


def test_02_total_amount(basics, rows):
    got = _call(basics, "total_amount", rows)
    assert got == pytest.approx(EXPECTED["total_amount"], abs=0.01)


def test_03_paid_amount(basics, rows):
    got = _call(basics, "paid_amount", rows)
    assert got == pytest.approx(EXPECTED["paid_amount"], abs=0.01)


def test_04_count_by_status(basics, rows):
    assert dict(_call(basics, "count_by_status", rows)) == EXPECTED["count_by_status"]


def test_05_unique_codes(basics, rows):
    got = _call(basics, "unique_codes", rows)
    assert isinstance(got, set), "unique_codes() обязана возвращать set, а не список"
    assert len(got) == EXPECTED["unique_codes"]
    assert "" not in got and " " not in got


def test_06_rows_without_code(basics, rows):
    assert _call(basics, "rows_without_code", rows) == EXPECTED["rows_without_code"]


def test_07_size_bucket(basics):
    assert _call(basics, "size_bucket", 19999.99) == "малая"
    assert _call(basics, "size_bucket", 20000.0) == "средняя"
    assert _call(basics, "size_bucket", 59999.99) == "средняя"
    assert _call(basics, "size_bucket", 60000.0) == "крупная"


def test_08_bucket_counts(basics, rows):
    assert dict(_call(basics, "bucket_counts", rows)) == EXPECTED["bucket_counts"]


def test_09_big_paid_ids(basics, rows):
    got = _call(basics, "big_paid_ids", rows, 80000.0)
    assert isinstance(got, list)
    assert len(got) == EXPECTED["big_paid"]
    assert got == sorted(got), "список обязан быть отсортирован по payout_id"
    assert len(set(got)) == len(got)


def test_10_top_partners(basics, rows):
    got = _call(basics, "top_partners", rows, 5)
    assert len(got) == 5
    for (code, total), (exp_code, exp_total) in zip(got, EXPECTED["top5"]):
        assert code == exp_code
        assert total == pytest.approx(exp_total, abs=0.01)


def test_11_period(basics, rows):
    first, last = _call(basics, "period", rows)
    assert (first, last) == EXPECTED["period"]


def test_12_page_item_counts(basics, pages):
    assert list(_call(basics, "page_item_counts", pages)) == EXPECTED["page_item_counts"]
    assert sum(EXPECTED["page_item_counts"]) == EXPECTED["fee_items"]


def test_13_unique_fee_ids(basics, pages):
    got = _call(basics, "unique_fee_ids", pages)
    assert isinstance(got, set), "unique_fee_ids() обязана возвращать set"
    assert len(got) == EXPECTED["unique_fee_ids"]


def test_14_name_variants(basics, rows):
    got = _call(basics, "name_variants", rows)
    assert len(got) == EXPECTED["unique_codes"]
    assert got["30000036"] == EXPECTED["name_variants_30000036"]
    assert sum(got.values()) == EXPECTED["name_variants_total"]


def test_15_first_name_and_safe_amount(basics, rows):
    names = _call(basics, "partner_names", rows)
    assert names["30000036"] == EXPECTED["first_name_30000036"]
    assert _call(basics, "safe_amount", "49088,78") == pytest.approx(49088.78)
    assert _call(basics, "safe_amount", "") is None
    assert _call(basics, "safe_amount", "н/д") is None
