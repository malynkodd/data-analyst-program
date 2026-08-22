# Данные проекта P5 («Портфель просрочки»)

## Статус этого файла

Полная декларация — `program/P5/step-00.md`. Датасет — синтетика с
генератором (часть 5 blueprint, «Синтетические данные — P1, P2, P5»):
кредиты на уровне договора с историей платежей не публикуются нигде в
реальном мире.

**Сами данные в репозиторий не коммитятся** (решение 29): папка `raw/`
перечислена в корневом `.gitignore`. В git лежат генератор, скрипт
эталонов и эталонные CSV.

## Файлы

| Файл | Роль | В git? |
|---|---|---|
| `generate_p5.py` | Генератор. `SEED = 20260822`. Пишет `raw/applications.csv`, `raw/loans.csv`, `raw/schedule.csv`, `raw/payments.csv`, `raw/marketing_spend.csv`. | да |
| `reference_p5.py` | Считает 8 метрик и сравнение до/после смены скоринга заново, независимо от генератора. Определения (база/ключ/зрелость) — в докстроках и `reference_answers.md`. | да |
| `reference_answers.md` | Контрольная точка и все восемь метрик с определением каждой (решение 30). | да |
| `domain_questions.md` | Ответы на 5 доменных интервью-вопросов (критерий 11). | да |
| `ref_funnel_metrics.csv` | approval_rate, fpd, fpd30, roll_rate_30_60. 4 строки. | да |
| `ref_vintage.csv` | Винтаж по когортам выдачи, 2025-01…2025-12. 12 строк. | да |
| `ref_business_metrics_p5.csv` | repeat_customer_rate, avg_ticket, cac_per_loan. 3 строки. | да |
| `ref_default_comparison.csv` | Главный вопрос проекта: default rate до/после 2026-04-01, на fpd30 и на ever_90dpd. 4 строки. | да |
| `raw/applications.csv` | `application_id, applicant_id, applied_date, channel, requested_amount, score, approved`. 7288 строк. | **нет** |
| `raw/loans.csv` | `loan_id, application_id, applicant_id, channel, origination_date, principal`. 4917 строк. | **нет** |
| `raw/schedule.csv` | Договорной график, неизменный: `loan_id, installment_no, due_date, due_amount`. 14751 строк (4917×3). | **нет** |
| `raw/payments.csv` | Факт: `loan_id, installment_no, paid_date, extended, extended_due_date`. Пустой `paid_date` — не оплачено на дату выгрузки. 14751 строк. | **нет** |
| `raw/marketing_spend.csv` | Один общий маркетинговый бюджет периода (как в M11). 1 строка. | **нет** |

## Проверка строк

| Файл | Строк |
|---|---|
| `ref_funnel_metrics.csv` | 4 |
| `ref_vintage.csv` | 12 |
| `ref_business_metrics_p5.csv` | 3 |
| `ref_default_comparison.csv` | 4 |

## Как воспроизвести

```
$ python program\P5\data\generate_p5.py
$ python program\P5\data\reference_p5.py
```
