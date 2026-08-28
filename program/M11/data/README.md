# Сквозной датасет модуля M11 (Доменный пакет — fintech, кредитование)

## Статус этого файла

Полная декларация — `program/M11/step-00.md`. Домен — fintech (решение
21, п. 2; выбор домена обоснован частью 4 blueprint, «Решение 2»): тот
же сервис микрокредитов, что в M8, со стороны кредитного портфеля.
Данные синтетические, `SEED = 20260827`.

**Сами данные в репозиторий не коммитятся** (решение 29): `raw/` в
корневом `.gitignore`.

## Файлы

| Файл | Роль | В git? |
|---|---|---|
| `generate_m11.py` | Генератор: заявки → одобрение → займы → погашение с риском, зависящим от скрытого кредитного рейтинга. | да |
| `reference_m11.py` | Считает восемь метрик заново, независимо от генератора. В докстроке — определения (база, окно) каждой. | да |
| `reference_slices.py` | Считает FPD, FPD30 и roll rate в трёх корзинах по размеру займа и approval rate в четырёх корзинах по скоринговому баллу — вторые задачи шага 01. Границы корзин печатает явно. | да |
| `reference_answers.md` | Контрольная точка и все восемь метрик. | да |
| `ref_funnel_metrics.csv` | Эталон шага 01: approval rate, FPD, FPD30, roll rate. 4 строки. | да |
| `ref_vintage.csv` | Эталон шага 02: винтажный анализ по месяцу выдачи. 5 строк. | да |
| `ref_business_metrics_m11.csv` | Эталон шага 03: repeat customer rate, средний чек, CAC на заём. 3 строки. | да |
| `ref_slices.csv` | Эталон вторых задач шага 01: те же метрики в разрезах. 13 строк. | да |
| `raw/applications.csv` | Заявки: `application_id, applicant_id, applied_date, requested_amount, score, approved`. 3281 строка. | **нет** |
| `raw/loans.csv` | Выданные займы: `loan_id, application_id, applicant_id, origination_date, due_date, principal, resolution_days`. Пустой `resolution_days` — не погашен на дату выгрузки. 2132 строки. | **нет** |
| `raw/marketing_spend.csv` | Один общий маркетинговый бюджет периода. 1 строка. | **нет** |

## Проверка строк

| Файл | Строк |
|---|---|
| `ref_funnel_metrics.csv` | 4 |
| `ref_vintage.csv` | 5 |
| `ref_business_metrics_m11.csv` | 3 |
| `ref_slices.csv` | 13 |

## Порядок загрузки

| Шаг | Что появляется | Файлы |
|---|---|---|
| `step-01.md` | весь датасет | `raw/` целиком |
| `step-02.md`–`step-05.md` | ничего нового | — |

## Как воспроизвести

```
$ .venv\Scripts\python.exe program\M11\data\generate_m11.py
$ .venv\Scripts\python.exe program\M11\data\reference_m11.py
```

`reference_slices.py` читает `raw/` относительно своего каталога и
запускается из него:

```
$ cd program\M11\data
$ ..\..\..\.venv\Scripts\python.exe reference_slices.py
```
