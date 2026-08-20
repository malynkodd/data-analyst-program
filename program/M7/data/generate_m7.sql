-- Генератор датасета M7 (BigQuery / DWH).
--
-- В отличие от M0-M6, здесь нет Python-скрипта и файла на диске: датасет
-- живёт целиком внутри BigQuery, создаётся одним SQL-запросом
-- (program/M7/step-00.md, "Отступление от конвенции модуля").
--
-- Домен fintech (решение 21, п.2): условная таблица транзакций, 731 день
-- (2024-01-01..2025-12-31, 2024 - високосный), 6000 операций на день без
-- исключений - объём партиций равный по конструкции, не по измерению
-- (program/M7/step-00.md, таблица дефектов).
--
-- Запуск: скопировать целиком в редактор запросов BigQuery, выполнить.
-- Не DML и не потоковая загрузка - совместимо с sandbox-режимом без
-- карты и биллинга (program/M7/step-01.md, 1.2).

CREATE SCHEMA IF NOT EXISTS fintech
OPTIONS (location = 'US');

CREATE OR REPLACE TABLE fintech.transactions_raw AS
SELECT
  day_offset * 6000 + row_num AS txn_id,
  CONCAT('ACC-', LPAD(CAST(MOD(row_num, 500) AS STRING), 4, '0')) AS account_id,
  ['purchase', 'refund', 'fee', 'transfer'][OFFSET(MOD(row_num, 4))] AS category,
  ROUND(50 + RAND() * 4950, 2) AS amount,
  'UAH' AS currency,
  DATE_ADD(DATE '2024-01-01', INTERVAL day_offset DAY) AS txn_date,
  TIMESTAMP_ADD(
    TIMESTAMP(DATE_ADD(DATE '2024-01-01', INTERVAL day_offset DAY)),
    INTERVAL CAST(RAND() * 86399 AS INT64) SECOND
  ) AS created_at
FROM UNNEST(GENERATE_ARRAY(0, 730)) AS day_offset,
     UNNEST(GENERATE_ARRAY(1, 6000)) AS row_num;

-- Контрольная точка - выполнить сразу после создания и сверить с
-- program/M7/data/reference_answers.md:
--
-- SELECT
--   COUNT(*) AS rows_total,
--   COUNT(DISTINCT txn_id) AS unique_ids,
--   COUNT(DISTINCT txn_date) AS unique_dates,
--   MIN(txn_date) AS min_date,
--   MAX(txn_date) AS max_date,
--   COUNT(DISTINCT account_id) AS accounts
-- FROM fintech.transactions_raw;
