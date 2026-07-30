# Контрольные числа для M3, умения A1/A3/A4 (эталон)

Все числа получены выполнением SQL на sqlite3 (модуль стандартной
библиотеки Python) поверх `schema.sql` + `seed.sql` (умение A1) и поверх
`schema.sql` + `seed.sql` + `retention_seed.sql` (умение A3). Для A4 —
поверх той же базы с добавленной `activity_log` (`generate_activity_log.py`).
Числа не придуманы — воспроизводимы запуском запросов ниже.

## A1 — демонстрационная задача (`step-06.md`, 1.3)

Задача: для каждого клиента пронумеровать ВСЕ его заказы (любой статус)
по порядку даты.

```sql
WITH ordered AS (
    SELECT customer_id, order_id, order_date, status
    FROM orders
)
SELECT customer_id, order_id, order_date, status,
       ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date, order_id) AS order_seq
FROM ordered
ORDER BY customer_id, order_seq;
```

| customer_id | order_id | order_date | status | order_seq |
|---|---|---|---|---|
| 1 | 101 | 2026-05-02 | completed | 1 |
| 1 | 102 | 2026-05-20 | completed | 2 |
| 1 | 103 | 2026-06-11 | completed | 3 |
| 2 | 104 | 2026-05-05 | completed | 1 |
| 2 | 105 | 2026-05-18 | completed | 2 |
| 2 | 106 | 2026-06-01 | cancelled | 3 |
| 3 | 107 | 2026-05-09 | completed | 1 |
| 5 | 108 | 2026-05-14 | completed | 1 |
| 5 | 109 | 2026-06-02 | completed | 2 |
| 6 | 110 | 2026-05-22 | cancelled | 1 |
| 7 | 111 | 2026-05-30 | pending | 1 |
| 8 | 112 | 2026-05-03 | completed | 1 |
| 8 | 113 | 2026-05-25 | completed | 2 |
| 8 | 114 | 2026-06-08 | completed | 3 |
| 9 | 115 | 2026-05-11 | completed | 1 |
| 9 | 116 | 2026-06-04 | pending | 2 |
| 11 | 117 | 2026-05-07 | cancelled | 1 |
| 11 | 118 | 2026-06-09 | cancelled | 2 |
| 12 | 119 | 2026-05-28 | completed | 1 |

Клиенты 4 и 10 отсутствуют в выводе — у них вообще нет заказов
(тот же факт, что уже показан в `step-05.md`).

## A1 — battery (`step-06.md`, 1.4), 6 задач

### T1. Накопительная сумма completed-заказов по клиенту

```sql
WITH completed AS (
    SELECT customer_id, order_id, order_date, amount
    FROM orders WHERE status = 'completed'
)
SELECT customer_id, order_id, order_date, amount,
       SUM(amount) OVER (PARTITION BY customer_id ORDER BY order_date, order_id
                          ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_total
FROM completed
ORDER BY customer_id, order_date, order_id;
```

| customer_id | order_id | order_date | amount | running_total |
|---|---|---|---|---|
| 1 | 101 | 2026-05-02 | 1200.0 | 1200.0 |
| 1 | 102 | 2026-05-20 | 850.0 | 2050.0 |
| 1 | 103 | 2026-06-11 | 430.0 | 2480.0 |
| 2 | 104 | 2026-05-05 | 600.0 | 600.0 |
| 2 | 105 | 2026-05-18 | 720.0 | 1320.0 |
| 3 | 107 | 2026-05-09 | 980.0 | 980.0 |
| 5 | 108 | 2026-05-14 | 540.0 | 540.0 |
| 5 | 109 | 2026-06-02 | 610.0 | 1150.0 |
| 8 | 112 | 2026-05-03 | 455.0 | 455.0 |
| 8 | 113 | 2026-05-25 | 700.0 | 1155.0 |
| 8 | 114 | 2026-06-08 | 330.0 | 1485.0 |
| 9 | 115 | 2026-05-11 | 510.0 | 510.0 |
| 12 | 119 | 2026-05-28 | 675.0 | 675.0 |

### T2. Ранжирование completed-заказов клиента по сумме (убывание)

```sql
WITH completed AS (
    SELECT customer_id, order_id, amount FROM orders WHERE status = 'completed'
)
SELECT customer_id, order_id, amount,
       ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY amount DESC, order_id ASC) AS rank_in_customer
FROM completed
ORDER BY customer_id, rank_in_customer;
```

| customer_id | order_id | amount | rank_in_customer |
|---|---|---|---|
| 1 | 101 | 1200.0 | 1 |
| 1 | 102 | 850.0 | 2 |
| 1 | 103 | 430.0 | 3 |
| 2 | 105 | 720.0 | 1 |
| 2 | 104 | 600.0 | 2 |
| 3 | 107 | 980.0 | 1 |
| 5 | 109 | 610.0 | 1 |
| 5 | 108 | 540.0 | 2 |
| 8 | 113 | 700.0 | 1 |
| 8 | 112 | 455.0 | 2 |
| 8 | 114 | 330.0 | 3 |
| 9 | 115 | 510.0 | 1 |
| 12 | 119 | 675.0 | 1 |

### T3. Разница с предыдущим completed-заказом клиента

```sql
WITH completed AS (
    SELECT customer_id, order_id, order_date, amount FROM orders WHERE status = 'completed'
)
SELECT customer_id, order_id, order_date, amount,
       LAG(amount) OVER (PARTITION BY customer_id ORDER BY order_date, order_id) AS prev_amount,
       amount - LAG(amount) OVER (PARTITION BY customer_id ORDER BY order_date, order_id) AS diff_from_prev
FROM completed
ORDER BY customer_id, order_date, order_id;
```

| customer_id | order_id | order_date | amount | prev_amount | diff_from_prev |
|---|---|---|---|---|---|
| 1 | 101 | 2026-05-02 | 1200.0 | (пусто) | (пусто) |
| 1 | 102 | 2026-05-20 | 850.0 | 1200.0 | -350.0 |
| 1 | 103 | 2026-06-11 | 430.0 | 850.0 | -420.0 |
| 2 | 104 | 2026-05-05 | 600.0 | (пусто) | (пусто) |
| 2 | 105 | 2026-05-18 | 720.0 | 600.0 | 120.0 |
| 3 | 107 | 2026-05-09 | 980.0 | (пусто) | (пусто) |
| 5 | 108 | 2026-05-14 | 540.0 | (пусто) | (пусто) |
| 5 | 109 | 2026-06-02 | 610.0 | 540.0 | 70.0 |
| 8 | 112 | 2026-05-03 | 455.0 | (пусто) | (пусто) |
| 8 | 113 | 2026-05-25 | 700.0 | 455.0 | 245.0 |
| 8 | 114 | 2026-06-08 | 330.0 | 700.0 | -370.0 |
| 9 | 115 | 2026-05-11 | 510.0 | (пусто) | (пусто) |
| 12 | 119 | 2026-05-28 | 675.0 | (пусто) | (пусто) |

### T4. Накопительное число completed-заказов по городу

```sql
WITH completed AS (
    SELECT o.order_id, o.order_date, c.city
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
    WHERE o.status = 'completed'
)
SELECT city, order_id, order_date,
       COUNT(*) OVER (PARTITION BY city ORDER BY order_date, order_id
                      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS orders_so_far_in_city
FROM completed
ORDER BY city, order_date, order_id;
```

| city | order_id | order_date | orders_so_far_in_city |
|---|---|---|---|
| Дніпро | 108 | 2026-05-14 | 1 |
| Дніпро | 109 | 2026-06-02 | 2 |
| Київ | 101 | 2026-05-02 | 1 |
| Київ | 102 | 2026-05-20 | 2 |
| Київ | 103 | 2026-06-11 | 3 |
| Львів | 104 | 2026-05-05 | 1 |
| Львів | 105 | 2026-05-18 | 2 |
| Львів | 119 | 2026-05-28 | 3 |
| Одеса | 112 | 2026-05-03 | 1 |
| Одеса | 107 | 2026-05-09 | 2 |
| Одеса | 113 | 2026-05-25 | 3 |
| Одеса | 114 | 2026-06-08 | 4 |
| Харків | 115 | 2026-05-11 | 1 |

### T5. Топ-2 позиции заказа по выручке в каждой категории товаров

```sql
WITH revenue AS (
    SELECT oi.order_item_id, oi.product_id, p.category,
           oi.quantity * oi.unit_price AS revenue
    FROM order_items oi
    JOIN products p ON p.product_id = oi.product_id
),
ranked AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY category ORDER BY revenue DESC, order_item_id ASC) AS rank_in_category
    FROM revenue
)
SELECT category, product_id, order_item_id, revenue, rank_in_category
FROM ranked
WHERE rank_in_category <= 2
ORDER BY category, rank_in_category;
```

| category | product_id | order_item_id | revenue | rank_in_category |
|---|---|---|---|---|
| addon | 1004 | 21 | 410.0 | 1 |
| addon | 1004 | 17 | 330.0 | 2 |
| service | 1005 | 13 | 390.0 | 1 |
| service | 1005 | 2 | 350.0 | 2 |
| subscription | 1002 | 9 | 980.0 | 1 |
| subscription | 1002 | 1 | 850.0 | 2 |

### T6. Отклонение от общего среднего чека (completed-заказы)

```sql
WITH completed AS (
    SELECT customer_id, order_id, amount FROM orders WHERE status = 'completed'
)
SELECT order_id, customer_id, amount,
       ROUND(AVG(amount) OVER (), 2) AS avg_completed_amount,
       ROUND(amount - AVG(amount) OVER (), 2) AS diff_from_avg
FROM completed
ORDER BY order_id;
```

| order_id | customer_id | amount | avg_completed_amount | diff_from_avg |
|---|---|---|---|---|
| 101 | 1 | 1200.0 | 661.54 | 538.46 |
| 102 | 1 | 850.0 | 661.54 | 188.46 |
| 103 | 1 | 430.0 | 661.54 | -231.54 |
| 104 | 2 | 600.0 | 661.54 | -61.54 |
| 105 | 2 | 720.0 | 661.54 | 58.46 |
| 107 | 3 | 980.0 | 661.54 | 318.46 |
| 108 | 5 | 540.0 | 661.54 | -121.54 |
| 109 | 5 | 610.0 | 661.54 | -51.54 |
| 112 | 8 | 455.0 | 661.54 | -206.54 |
| 113 | 8 | 700.0 | 661.54 | 38.46 |
| 114 | 8 | 330.0 | 661.54 | -331.54 |
| 115 | 9 | 510.0 | 661.54 | -151.54 |
| 119 | 12 | 675.0 | 661.54 | 13.46 |

## A1 — типичные ошибки (числа для `step-06.md`, 1.6)

**Забыт `ORDER BY` внутри `OVER` (T1).** `SUM(amount) OVER (PARTITION BY
customer_id)` без `ORDER BY` даёт на каждой строке итоговую сумму
клиента, а не накопительную:

| customer_id | order_id | amount | wrong_total (без ORDER BY) | правильный running_total |
|---|---|---|---|---|
| 1 | 101 | 1200.0 | 2480.0 | 1200.0 |
| 1 | 102 | 850.0 | 2480.0 | 2050.0 |
| 1 | 103 | 430.0 | 2480.0 | 2480.0 |

**Забыт `DESC` в `ORDER BY` внутри `OVER` (T2).** Без `DESC` ранжирование
идёт по возрастанию — ранг 1 достаётся самому дешёвому заказу вместо
самого дорогого:

| customer_id | order_id | amount | wrong_rank (без DESC) | правильный rank_in_customer |
|---|---|---|---|---|
| 1 | 103 | 430.0 | 1 | 3 |
| 1 | 102 | 850.0 | 2 | 2 |
| 1 | 101 | 1200.0 | 3 | 1 |

**Забыт `PARTITION BY customer_id` в `LAG` (T3).** `prev_amount`
подтягивается из заказа **другого** клиента, ближайшего по дате:

| customer_id | order_id | order_date | amount | wrong_prev_amount (без PARTITION BY) | правильный prev_amount |
|---|---|---|---|---|---|
| 8 | 112 | 2026-05-03 | 455.0 | 1200.0 (заказ 101, клиент 1) | (пусто) |
| 2 | 104 | 2026-05-05 | 600.0 | 455.0 (заказ 112, клиент 8) | (пусто) |
| 5 | 108 | 2026-05-14 | 540.0 | 510.0 (заказ 115, клиент 9) | (пусто) |

## A3 — когортный retention, 12 когорт (`step-07.md`)

Датасет: `schema.sql` + `seed.sql` + `retention_seed.sql`
(`generate_retention.py`, `SEED = 20260803`, 240 новых клиентов
`customer_id` 101–340, 347 заказов `order_id` 20001+, когорта = месяц
первого заказа, 20 клиентов на когорту; независимые броски на
активность в месяц+1 и в месяц+2 после когортного месяца).

Запрос параметризован смещением месяца (`+1 month` для M1, `+2 month`
для M2 — единственное отличие между 1.3 и 1.4):

```sql
WITH first_order AS (
    SELECT customer_id, MIN(order_date) AS first_date
    FROM orders
    WHERE customer_id > 100
    GROUP BY customer_id
),
cohorts AS (
    SELECT customer_id, substr(first_date, 1, 7) AS cohort_month
    FROM first_order
),
cohort_size AS (
    SELECT cohort_month, COUNT(*) AS cohort_size
    FROM cohorts
    GROUP BY cohort_month
),
target_month_activity AS (
    SELECT c.cohort_month, c.customer_id
    FROM cohorts c
    JOIN orders o ON o.customer_id = c.customer_id
    WHERE substr(o.order_date, 1, 7) = strftime('%Y-%m', c.cohort_month || '-01', '+1 month')
    GROUP BY c.cohort_month, c.customer_id
),
retained AS (
    SELECT cohort_month, COUNT(*) AS retained
    FROM target_month_activity
    GROUP BY cohort_month
)
SELECT s.cohort_month, s.cohort_size,
       COALESCE(r.retained, 0) AS retained,
       ROUND(COALESCE(r.retained, 0) * 100.0 / s.cohort_size, 2) AS retention_pct
FROM cohort_size s
LEFT JOIN retained r ON r.cohort_month = s.cohort_month
ORDER BY s.cohort_month;
```

### M1 (1.3, разобранный пример) — `+1 month`, файл `a3_cohort_retention_m1.csv`

| cohort_month | cohort_size | retained | retention_pct |
|---|---|---|---|
| 2025-01 | 20 | 7 | 35.0 |
| 2025-02 | 20 | 8 | 40.0 |
| 2025-03 | 20 | 4 | 20.0 |
| 2025-04 | 20 | 6 | 30.0 |
| 2025-05 | 20 | 8 | 40.0 |
| 2025-06 | 20 | 5 | 25.0 |
| 2025-07 | 20 | 7 | 35.0 |
| 2025-08 | 20 | 8 | 40.0 |
| 2025-09 | 20 | 7 | 35.0 |
| 2025-10 | 20 | 4 | 20.0 |
| 2025-11 | 20 | 4 | 20.0 |
| 2025-12 | 20 | 5 | 25.0 |

### M2 (1.4, задание) — `+2 month`, файл `a3_cohort_retention_m2.csv`

| cohort_month | cohort_size | retained | retention_pct |
|---|---|---|---|
| 2025-01 | 20 | 3 | 15.0 |
| 2025-02 | 20 | 5 | 25.0 |
| 2025-03 | 20 | 2 | 10.0 |
| 2025-04 | 20 | 3 | 15.0 |
| 2025-05 | 20 | 6 | 30.0 |
| 2025-06 | 20 | 5 | 25.0 |
| 2025-07 | 20 | 2 | 10.0 |
| 2025-08 | 20 | 1 | 5.0 |
| 2025-09 | 20 | 1 | 5.0 |
| 2025-10 | 20 | 2 | 10.0 |
| 2025-11 | 20 | 2 | 10.0 |
| 2025-12 | 20 | 2 | 10.0 |

Обе таблицы — по 12 строк, каждая когорта размером ровно 20 — сумма
`cohort_size` по всем 12 строкам равна 240, совпадает с числом
клиентов, сгенерированных `generate_retention.py`. M2 < M1 для каждой
когорты (естественное следствие независимых, но убывающих по горизонту
бросков) — это не проверяется отдельным критерием, но служит быстрой
проверкой на глаз, что запрос не перепутал смещение месяца.

## A4 — оптимизация, до/после (`step-08.md`)

Датасет: та же база + `activity_log`, созданная `generate_activity_log.py`
(`SEED = 20260804`, 4 800 000 строк, без индекса на `customer_id`).
Измерено на референсной машине автора — **абсолютное время зависит от
железа учащегося**, механически проверяемый порог — не секунды, а
(а) отношение "до/после" и (б) план запроса (`EXPLAIN QUERY PLAN`).

Запрос (число `login`-событий на клиента):

```sql
SELECT c.customer_id,
       (SELECT COUNT(*) FROM activity_log a
        WHERE a.customer_id = c.customer_id AND a.event_type = 'login') AS n_logins
FROM customers c
ORDER BY c.customer_id;
```

| Показатель | До индекса | После индекса |
|---|---|---|
| Время выполнения (референсная машина автора) | 70.66 с | 0.044 с |
| Ускорение | — | ≈1606× |
| `EXPLAIN QUERY PLAN` для `activity_log` | `SCAN a` (полный скан 4.8 млн строк на каждого из 252 клиентов) | `SEARCH a USING COVERING INDEX idx_activity_customer_type (customer_id=? AND event_type=?)` |

Индекс: `CREATE INDEX idx_activity_customer_type ON activity_log(customer_id, event_type);`
Построение индекса на референсной машине — 3.68 с, разовая операция.

Результаты запроса до и после индекса побайтово совпадают (252 строки,
проверено сравнением `res == res2` в Python) — индекс меняет план и
время, не меняет ответ.

### Вариант для задания (1.4, `step-08.md`) — фильтр по диапазону дат

Запрос (число любых событий клиента в июне 2025):

```sql
SELECT c.customer_id,
       (SELECT COUNT(*) FROM activity_log a
        WHERE a.customer_id = c.customer_id
          AND a.event_date BETWEEN '2025-06-01' AND '2025-06-30') AS n_events_june
FROM customers c
ORDER BY c.customer_id;
```

| Показатель | Без индекса | С индексом `(customer_id, event_type)` из 1.3 | С индексом `(customer_id, event_date)` |
|---|---|---|---|
| Время (референсная машина) | 71.32 с | 15.04 с | 0.02 с |
| `EXPLAIN QUERY PLAN` для `activity_log` | `SCAN a` | `SEARCH a USING INDEX idx_activity_customer_type (customer_id=?)` | `SEARCH a USING COVERING INDEX idx_activity_customer_date (customer_id=? AND event_date>? AND event_date<?)` |

Индекс из 1.3 (`customer_id, event_type`) **частично** ускоряет этот
запрос (71.32 → 15.04 с) — SQLite использует его для поиска по
`customer_id`, но всё равно построчно проверяет `event_date` внутри
найденного диапазона. 15 с всё ещё выше порога `<5 с` — недостаточно;
нужен отдельный индекс, покрывающий именно `event_date`
(`CREATE INDEX idx_activity_customer_date ON activity_log(customer_id,
event_date);`). Три результата (без индекса / с чужим индексом / со
своим) побайтово совпадают — индекс меняет только план и время.
