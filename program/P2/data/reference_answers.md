# Эталонные ответы P2 (конверсия в первую оплату)

Считает `reference_p2.py`, независимо от списков `generate_p2.py`.

## Контрольная точка

```
> python program\P2\data\generate_p2.py
```

Ожидается:

```
signups.csv: 17434 строк, sha256 e852a8d5734d6e48c90853c170e2728a9c06fa5a50d47310404d6ab80e56351d
payments.csv: 31021 строк, sha256 d6d290a8139fa317f7e9c87913c67b8cbec63a47173ad48129b4d25dcb0ff6a4
```

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
> python tools\vault.py open program\P2\data\answers.md --attempt program\P2\work\<ваш файл>
```

Открытым здесь остаётся ровно то, без чего проект не начать: контрольная
точка датасета выше.

**`ref_retention.csv` тоже закрыт** — в этом проекте эталонная таблица
и есть ответ на вопрос заказчика, и держать её открытой значило бы
закрыть разбор, оставив рядом то, ради чего его закрывали. Порядок
работы меняется на один шаг: сначала свой результат, потом открыть
эталон **в файл** и сверить обычным `compare_csv.py`.

```
> python tools\vault.py open program\P2\data\ref_retention.csv --attempt program\P2\work\<ваш файл> --to program\P2\data\unlocked\ref_retention.csv
> python program\M3\data\compare_csv.py program\P2\work\<ваш csv> program\P2\data\unlocked\ref_retention.csv
```

Каталог `unlocked/` — в `.gitignore`: расшифрованный эталон остаётся на
диске и в репозиторий не возвращается.
