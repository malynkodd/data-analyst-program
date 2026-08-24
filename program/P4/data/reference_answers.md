# Эталонные ответы P4 («Три источника, один объект»)

Считает `reference_p4.py`, независимо от `fetch_prozorro.py`/`fetch_edr.py`/
`fetch_nbu.py`. Прогон на машине автора 2026-08-22.

## Контрольная точка (снапшот)

```
> python program\P4\data\fetch_prozorro.py
> python program\P4\data\fetch_edr.py
> python program\P4\data\fetch_nbu.py
```

| Файл | Строк | sha256 |
|---|---|---|
| `snapshot/tenders_food.csv` | 300 | `0450956fb29bbcc7aea2acf2ab5c68853a4cf7193cc46636bca03bc0ea670d9b` |
| `snapshot/contracts_food.csv` | 500 | `6cdb6b63c0ac8349e608a2dcb334b1cc5de17f7a5e3ad4dcb6f39f3d09ba5a75` |
| `snapshot/edr_lookup.csv` | 329 | `13a3cf46389357f7982aa54e149810a6cefa945765d3b9e5dc206df7036f4d6e` |
| `snapshot/edrpous_needed.txt` | 449 | `690099736b59f1e52ffe883db702a5eedfa40eec61ef405601438c110518de75` |
| `snapshot/edrpous_not_found.txt` | 120 | `3738a7ead53ed6aa8f351b6490b58fac66a58430d2379f9c3342c5b5645bcea9` |
| `snapshot/usd_uah.csv` | 1483 | `c2b644de23fbdcbc83d79e63efa17aaedb7ba77c1ff9c61cefc71060ca5acb6e` |
| `raw/uo.zip` (не в git, решение 36) | — | `171a62ce8ed6e43018df28c7539d4c25801215599d3b314432c77e3b0fff7bad` |

Prozorro и НБУ — живые источники, при повторной выгрузке числа
разойдутся (правило части 5 blueprint). `raw/uo.zip` — снапшот на
2026-08-22 (решение 35/36), не переиздаётся при каждом запуске.

## Разбор закрыт турникетом

Ответы, ранги, выбранные трактовки и разбор дефектов вынесены в
`answers.md` и закрыты турникетом (`tools/vault.py`, решения 51 и 53).
Причина названа независимой проверкой
`audit/independent-final-check-2026-08-24.md`, блокер 8.2: проект — это
единственное доказательство, что умения работают вместе, и приёмка, где
ответ лежит рядом открытым файлом, доказывает только умение читать.

Открывается после сохранённой попытки, проход пишется в
`research/attempts.md`:

```
> python tools\vault.py open program\P4\data\answers.md --attempt program\P4\work\<ваш файл>
```

Открытым здесь остаётся ровно то, без чего проект не начать: контрольная
точка датасета выше.

**четыре `ref_*.csv` тоже закрыты** — в этом проекте эталонная таблица
и есть ответ на вопрос заказчика, и держать её открытой значило бы
закрыть разбор, оставив рядом то, ради чего его закрывали. Порядок
работы меняется на один шаг: сначала свой результат, потом открыть
эталон **в файл** и сверить обычным `compare_csv.py`.

```
> python tools\vault.py open program\P4\data\ref_match_report.csv --attempt program\P4\work\<ваш файл> --to program\P4\data\unlocked\ref_match_report.csv
> python program\M3\data\compare_csv.py program\P4\work\<ваш csv> program\P4\data\unlocked\ref_match_report.csv
```

Каталог `unlocked/` — в `.gitignore`: расшифрованный эталон остаётся на
диске и в репозиторий не возвращается.
