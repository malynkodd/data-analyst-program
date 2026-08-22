-- BigQuery-часть P4 (M7): загрузка сверенных данных, партиционированный
-- запрос, снижение объёма сканирования ≥5×.
--
-- Как в M7 (program/M7/step-00.md, "Отступление от конвенции модуля"):
-- у среды написания нет доступа к консоли BigQuery. Запрос проверен на
-- синтаксис написанием (BigQuery Standard SQL), не прогнан. Точные
-- байты — то, что учащийся увидит в консоли и зафиксирует скриншотом
-- (DEFERRED.md, "Проверка BigQuery").
--
-- В отличие от M7 (731 день РОВНО по 6000 строк — гарантия конструкции,
-- не измерение), здесь реальные контракты, распределены по датам
-- НЕРАВНОМЕРНО: снапшот `contracts_food.csv` (500 строк, собран
-- descending-сканом живой ленты 2026-08-22) даёт 292 строки на август
-- 2026 и лишь единицы на 2025 год. Гарантия здесь — не структурная
-- «партиция = 1/N», а посчитанная по факту распределения этого
-- снапшота (reference_p4.py печатает точные доли): месяц с наименьшей
-- долей даёт кратность с огромным запасом, месяц с наибольшей —
-- не даст вовсе. Ниже — заведомо годный месяц, посчитанный, не
-- угаданный.
--
-- Загрузка: program/P4/data/snapshot/contracts_food.csv — реально
-- сверенные данные этого проекта (не GENERATE_ARRAY, как в M7 —
-- здесь синтетики нет, часть 5 blueprint, "Реальные публичные данные").
-- Поддержка batch-загрузки CSV в BigQuery sandbox не подтверждена
-- документацией явно (тот же непроверенный пункт, что M7) — таблица
-- строится INSERT-строками, воспроизводимыми из CSV скриптом
-- `program/P4/data/make_bigquery_inserts.py`, а не через `bq load`.

CREATE SCHEMA IF NOT EXISTS procurement
OPTIONS (location = 'US');

CREATE OR REPLACE TABLE procurement.contracts_food (
  contract_id      STRING,
  tender_id        STRING,
  date_signed      DATE,
  status           STRING,
  cpv_id           STRING,
  amount           NUMERIC,
  currency         STRING,
  buyer_name       STRING,
  buyer_edrpou     STRING,
  supplier_name    STRING,
  supplier_edrpou  STRING,
  supplier_in_edr  BOOL
)
PARTITION BY date_signed;

-- Строки вставляются `make_bigquery_inserts.py` (INSERT INTO ... VALUES,
-- batch не подтверждён) — не хранятся здесь текстом: contracts_food.csv
-- меняется при каждой новой выгрузке, INSERT пришлось бы переписывать
-- вручную при каждом расхождении со снапшотом (критерий 5 части 5
-- blueprint), а генератор всегда синхронен с текущим CSV.

-- Базовый запрос — без фильтра по партиционирующей колонке, читает
-- всю таблицу целиком:
SELECT
  supplier_edrpou,
  ANY_VALUE(supplier_name) AS supplier_name,
  SUM(amount) AS total_uah
FROM procurement.contracts_food
WHERE currency = 'UAH'
GROUP BY supplier_edrpou
ORDER BY total_uah DESC
LIMIT 10;

-- Партиционированный запрос — январь 2026: 75 из 500 строк снапшота
-- (15.0%, посчитано `reference_p4.py`) — читает только партиции внутри
-- WHERE, оценочная кратность снижения ≈6.7× (500/75), с запасом над
-- требованием части 5 blueprint «≥5×».
SELECT
  supplier_edrpou,
  ANY_VALUE(supplier_name) AS supplier_name,
  SUM(amount) AS month_total_uah
FROM procurement.contracts_food
WHERE currency = 'UAH'
  AND date_signed BETWEEN DATE('2026-01-01') AND DATE('2026-01-31')
GROUP BY supplier_edrpou
ORDER BY month_total_uah DESC
LIMIT 10;
