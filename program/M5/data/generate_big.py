"""Генератор большой выгрузки для шага M5.09 (умение B7).

Один файл `raw/payouts_big.csv` — та же предметная область, что у
остального модуля (выплаты партнёрам платёжного сервиса), но объёмом,
на котором «прочитать целиком и посчитать» перестаёт быть бесплатным.
Категория — синтетика учебного модуля с генератором (решение 29
`design/decisions.md`); файл не коммитится, в git лежит только этот
скрипт и контрольная точка в `reference_answers.md`.

Почему в файле есть три широкие текстовые колонки, которые никому не
нужны: без них отбор колонок (`usecols`) ничего не экономит, и
упражнение вырождается. В рабочих выгрузках такие колонки есть всегда —
комментарий оператора, исходная строка платёжного шлюза, признак
источника.

Запуск из корня репозитория:

    .venv\\Scripts\\python.exe program\\M5\\data\\generate_big.py

Печатает контрольную точку: число строк, размер в байтах и sha256.
Детерминирован — `SEED` фиксирован до первого обращения к `random`.
Время прогона на машине автора — около 40 с, файл около 300 МБ.
"""

from __future__ import annotations

import hashlib
import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

SEED = 20260824
random.seed(SEED)

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
OUT = RAW / "payouts_big.csv"

N_ROWS = 1_800_000
PERIOD_START = date(2026, 1, 1)
N_DAYS = 181  # 2026-01-01 .. 2026-06-30

PARTNERS = [f"{30000000 + i}" for i in range(1, 121)]
STATUSES = ["PAID"] * 84 + ["PENDING"] * 10 + ["FAILED"] * 6
CHANNELS = ["gateway-a", "gateway-b", "gateway-c", "manual"]
NOTES = [
    "auto settlement batch, no manual review required",
    "operator note: partner requested split payout, approved",
    "gateway callback received twice, second one ignored",
    "reconciliation comment left blank by upstream system",
    "payout scheduled by nightly job, priority normal",
]


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    header = (
        "payout_id,partner_code,payout_date,amount,currency,status,"
        "channel,raw_payload,operator_note,source_system\n"
    )
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        fh.write(header)
        for i in range(N_ROWS):
            day = PERIOD_START + timedelta(days=random.randrange(N_DAYS))
            partner = random.choice(PARTNERS)
            amount = round(random.uniform(120.0, 92000.0), 2)
            status = random.choice(STATUSES)
            channel = random.choice(CHANNELS)
            note = random.choice(NOTES)
            payload = (
                f"{{'gw':'{channel}','ref':'{2_000_000 + i}',"
                f"'ts':'{day.isoformat()}T09:00:00Z','retry':0}}"
            )
            fh.write(
                f"{5_000_000 + i},{partner},{day.isoformat()},{amount:.2f},UAH,"
                f"{status},{channel},\"{payload}\",\"{note}\",core-ledger\n"
            )

    size = OUT.stat().st_size
    digest = hashlib.sha256()
    with OUT.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)

    print("Большая выгрузка M5 записана в", OUT)
    print("SEED =", SEED)
    print(f"строк данных: {N_ROWS}")
    print(f"размер, байт: {size}")
    print(f"размер, МБ:   {size / 1024 / 1024:.1f}")
    print("sha256:", digest.hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
