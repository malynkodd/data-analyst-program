# Данные проекта P4 («Три источника, один объект»)

## Статус этого файла

Полная декларация — `program/P4/step-00.md`. Данные — **реальные
публичные**, зафиксированные снапшотом (часть 5 blueprint, «Реальные
публичные данные — P3, P4, P6»), не синтетика.

**Снапшот коммитится в репозиторий** (та же конвенция, что П3/П6),
**кроме `raw/uo.zip`** — 326 858 701 байт, слишком велик для git, в
`.gitignore` (решение 35/36: скачивается автором вручную, `robots.txt`
`data.gov.ua` запрещает AI-краулерам, в отличие от `bank.gov.ua` и
Prozorro API — снапшоты которых агент выгрузил напрямую).

## Три источника

| Источник | Файл | Роль |
|---|---|---|
| Prozorro API | `snapshot/tenders_food.csv`, `snapshot/contracts_food.csv` | ожидание (тендер) vs факт (контракт), CPV 15 |
| ЄДР юридичних осіб (`data.gov.ua`, `UO.zip`) | `snapshot/edr_lookup.csv` | сверка контрагентов по ЄДРПОУ |
| API НБУ | `snapshot/usd_uah.csv` | курсовой контекст |

## Файлы

| Файл | Роль | В git? |
|---|---|---|
| `fetch_prozorro.py` | Инструмент выгрузки: тендеры и контракты CPV 15 живой лентой Prozorro. | да |
| `fetch_edr.py` | Инструмент выгрузки: точечный потоковый разбор `raw/uo.zip` (3,16 ГБ, windows-1251) по списку нужных ЄДРПОУ — не полная загрузка в память. | да |
| `fetch_nbu.py` | Инструмент выгрузки: курс USD/UAH, 2022-08-01…дата выгрузки. | да |
| `reference_p4.py` | Считает сверку (двусторонняя, метод M6), топ-10 поставщиков, агрегаты тендеры/контракты — заново, независимо от скриптов выгрузки. | да |
| `reference_answers.md` | Контрольная точка (sha256 + строки) и все эталонные числа с определением каждого (решение 30). | да |
| `bigquery_p4.sql` | DDL + партиционированный запрос (M7) — не прогнан, нет доступа к консоли BigQuery (DEFERRED.md). | да |
| `make_bigquery_inserts.py` | Генерирует `INSERT INTO ... VALUES` из снапшота — загрузка через SQL, не `bq load` (тот же непроверенный пункт, что M7). | да |
| `ref_match_report.csv` | 3 строки: уникальных кодов, найдено, не найдено. | да |
| `ref_unmatched_report.csv` | 116 строк — код + причина потери, исчерпывающе. | да |
| `ref_top10_suppliers.csv` | 10 строк — топ поставщиков с флагом «в ЄДР». | да |
| `ref_totals_comparison.csv` | 3 строки — итог без фильтра / исключить / распределить (критерии 7–8). | да |
| `snapshot/tenders_food.csv` | **Реальный снапшот**, 300 строк, тендеры CPV 15. | да |
| `snapshot/contracts_food.csv` | **Реальный снапшот**, 500 строк, контракты CPV 15. | да |
| `snapshot/edr_lookup.csv` | **Реальный снапшот**, 329 строк — только нужные ЄДРПОУ из `UO.xml`, не весь реестр (~2 млн записей). | да |
| `snapshot/edrpous_needed.txt` / `edrpous_not_found.txt` | Списки кодов для/после сверки — промежуточный, но воспроизводимый артефакт. | да |
| `snapshot/usd_uah.csv` | **Реальный снапшот**, 1483 строки. | да |
| `raw/uo.zip` | Полный реестр ЄДР юрлиц, 326 858 701 байт. **Не в git** (решение 35/36) — скачивается автором по прямой ссылке. | **нет** |

## Проверка строк

| Файл | Строк |
|---|---|
| `ref_match_report.csv` | 3 |
| `ref_unmatched_report.csv` | 116 |
| `ref_top10_suppliers.csv` | 10 |
| `ref_totals_comparison.csv` | 3 |
| `snapshot/tenders_food.csv` | 300 |
| `snapshot/contracts_food.csv` | 500 |
| `snapshot/edr_lookup.csv` | 329 |
| `snapshot/usd_uah.csv` | 1483 |

## Как воспроизвести

```
$ python program\P4\data\fetch_prozorro.py
$ python program\P4\data\fetch_edr.py
$ python program\P4\data\fetch_nbu.py
$ python program\P4\data\reference_p4.py
```

`fetch_edr.py` требует `raw/uo.zip` на диске — скачивается автором
вручную (инструкция и прямая ссылка — `program/P4/step-00.md`).
