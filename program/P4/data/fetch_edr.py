"""Снапшот P4 — прицельная выборка из ЄДР юридичних осіб (`UO.zip`,
решение 35/36 `design/decisions.md`).

**Файл нельзя открыть в Excel и нельзя грузить в память целиком.**
`UO.xml` внутри `program/P4/data/raw/uo.zip` — **3 160 020 503 байт**
(3,16 ГБ) несжатым, один плоский XML: `<DATA><SUBJECT>...</SUBJECT>...
</DATA>`, без переносов между записями. Обход — потоковый
(`xml.etree.ElementTree.iterparse` прямо на файловом объекте внутри
ZIP, без полной распаковки на диск), с `elem.clear()` после каждой
`SUBJECT`, иначе дерево в памяти растёт на весь файл.

**Кодировка — не UTF-8.** XML-декларация утверждает
`encoding="windows-1251"` (найдено прогоном, не в описании blueprint —
часть 5 blueprint называет «кириллица не в UTF-8» общим требованием к
источникам P3/P4/P6, здесь это подтверждено фактически, не гипотетично).
`ElementTree` читает объявленную кодировку из самой декларации
корректно — специальной обработки не требует, но это первое, что
ломается при попытке прочитать файл наивно (`open(..., encoding="utf-8")`
на уже распакованный `.xml`).

Схема записи: `<SUBJECT><RECORD>` (внутренний ID реестра, не ЄДРПОУ)
`<NAME>` `<SHORT_NAME>` `<OPF>` (организационно-правовая форма)
`<EDRPOU>` `<STAN>` (статус: діючий / припинено / ...) `<REGISTRATION>`
`<TERMINATED_INFO>` и другие поля, не нужные этому проекту.

Отбор — не полный разбор: читаются ТОЛЬКО записи, чей `<EDRPOU>` есть в
`program/P4/data/snapshot/edrpous_needed.txt` (уникальные ЄДРПОУ
заказчиков/поставщиков из тендеров и контрактов Prozorro, собраны
`fetch_prozorro.py`). Это и есть «нарезка по ключу» для этого файла —
без неё пришлось бы держать в памяти или на диске работу с 3+ ГБ ради
нескольких сотен нужных записей.
"""
from __future__ import annotations

import csv
import hashlib
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

# Кириллица в консоли не полагается на кодировку терминала
# (решение 17; симуляция 2026-09-04, дефект M9-1: без этой строки
# скрипт падал с UnicodeEncodeError, допечатав часть вывода).
sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
RAW_ZIP = HERE / "raw" / "uo.zip"
SNAP = HERE / "snapshot"
SNAP.mkdir(parents=True, exist_ok=True)


def main() -> None:
    needed_path = SNAP / "edrpous_needed.txt"
    needed = set(needed_path.read_text(encoding="utf-8").splitlines())
    needed = {e for e in needed if e}
    print(f"Ищем {len(needed)} ЄДРПОУ в UO.xml (3,16 ГБ, один проход)")

    found: dict[str, dict] = {}
    t0 = time.time()
    n_records = 0

    with zipfile.ZipFile(RAW_ZIP) as z:
        with z.open("UO.xml") as f:
            for event, elem in ET.iterparse(f, events=("end",)):
                if elem.tag != "SUBJECT":
                    continue
                n_records += 1
                edrpou_el = elem.find("EDRPOU")
                edrpou = edrpou_el.text if edrpou_el is not None else None
                if edrpou in needed:
                    def txt(tag):
                        e = elem.find(tag)
                        return e.text if e is not None and e.text else ""
                    found[edrpou] = {
                        "edrpou": edrpou,
                        "name": txt("NAME"),
                        "short_name": txt("SHORT_NAME"),
                        "opf": txt("OPF"),
                        "stan": txt("STAN"),
                        "registration": txt("REGISTRATION"),
                        "terminated_info": txt("TERMINATED_INFO"),
                    }
                elem.clear()
                if n_records % 200000 == 0:
                    dt = time.time() - t0
                    print(f"  {n_records} записей, найдено {len(found)}/{len(needed)}, {dt:.0f} с")
                if len(found) == len(needed):
                    print(f"  все {len(needed)} найдены на записи {n_records} — остановка раньше конца файла")
                    break

    dt = time.time() - t0
    print(f"Готово: {n_records} записей просмотрено за {dt:.0f} с, найдено {len(found)}/{len(needed)}")

    out_path = SNAP / "edr_lookup.csv"
    with out_path.open("w", encoding="utf-8", newline="") as out:
        w = csv.writer(out)
        w.writerow(["edrpou", "name", "short_name", "opf", "stan", "registration", "terminated_info"])
        for edrpou in sorted(found):
            r = found[edrpou]
            w.writerow([r["edrpou"], r["name"], r["short_name"], r["opf"], r["stan"],
                        r["registration"], r["terminated_info"]])

    missing = sorted(needed - found.keys())
    missing_path = SNAP / "edrpous_not_found.txt"
    missing_path.write_text("\n".join(missing), encoding="utf-8")

    digest = hashlib.sha256(out_path.read_bytes()).hexdigest()
    print(f"{out_path.name}: {len(found)} строк, sha256 {digest}")
    print(f"{missing_path.name}: {len(missing)} ЄДРПОУ не найдено в UO.xml "
          f"(ФОП вместо юрлица, РНОКПП вместо ЄДРПОУ, иностранный поставщик, реестр устарел)")


if __name__ == "__main__":
    main()
