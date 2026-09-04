"""Генерирует INSERT-запросы BigQuery из `snapshot/contracts_food.csv` +
`snapshot/edr_lookup.csv` (флаг `supplier_in_edr`) — для вставки следом
за DDL в `bigquery_p4.sql` (batch-загрузка CSV в sandbox не подтверждена
документацией, тот же непроверенный пункт, что у M7). Печатает
INSERT INTO ... VALUES (...), (...), ...; порциями по BATCH строк.
"""
import csv
import sys
from pathlib import Path

# Кириллица в консоли не полагается на кодировку терминала
# (решение 17; симуляция 2026-09-04, дефект M9-1: без этой строки
# скрипт падал с UnicodeEncodeError, допечатав часть вывода).
sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
SNAP = HERE / "snapshot"
BATCH = 200


def sql_str(v: str) -> str:
    return "NULL" if not v else "'" + v.replace("'", "\\'") + "'"


def sql_num(v: str) -> str:
    return "NULL" if not v else v


def main() -> None:
    with (SNAP / "edr_lookup.csv").open(encoding="utf-8") as f:
        in_edr = {r["edrpou"] for r in csv.DictReader(f)}

    with (SNAP / "contracts_food.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print(f"-- {len(rows)} строк, сгенерировано из contracts_food.csv + edr_lookup.csv")
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i + BATCH]
        values = []
        for c in chunk:
            supplier_in_edr = c["supplier_edrpou"] in in_edr
            values.append(
                "(" + ", ".join([
                    sql_str(c["contract_id"]), sql_str(c["tender_id"]),
                    f"DATE({sql_str((c['date_signed'] or '')[:10])})" if c["date_signed"] else "NULL",
                    sql_str(c["status"]), sql_str(c["cpv_id"]),
                    sql_num(c["amount"]), sql_str(c["currency"]),
                    sql_str(c["buyer_name"]), sql_str(c["buyer_edrpou"]),
                    sql_str(c["supplier_name"]), sql_str(c["supplier_edrpou"]),
                    "TRUE" if supplier_in_edr else "FALSE",
                ]) + ")"
            )
        print("INSERT INTO procurement.contracts_food VALUES")
        print(",\n".join(values) + ";")
        print()


if __name__ == "__main__":
    main()
