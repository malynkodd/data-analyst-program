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

Эталон: `a1_task1_running_total.csv` — `step-06.md`.

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

Эталон: `a1_task2_rank_desc.csv` — `step-06.md`.

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

Эталон: `a1_task3_lag_diff.csv` — `step-06.md`.

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

Эталон: `a1_task4_city_cumulative.csv` — `step-06.md`.

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

Эталон: `a1_task5_top2_category.csv` — `step-06.md`.

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

Эталон: `a1_task6_diff_avg.csv` — `step-06.md`.

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

Запрос параметризован смещением месяца: `+1 month` для M1, `+2 month`
для M2 — единственное отличие между 1.3 и 1.4. Ниже он выписан дважды,
по разу на горизонт, а не один раз со словесной оговоркой: оба варианта
исполняются `tools/check_consistency.py` и сверяются каждый со своим
CSV, поэтому правка одного и забытая правка другого не проходят молча.

### M1 (1.3, разобранный пример) — `+1 month`, файл `a3_cohort_retention_m1.csv`

Эталон: `a3_cohort_retention_m1.csv` — `step-07.md`.

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

Эталон: `a3_cohort_retention_m2.csv` — `step-07.md`.

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
    WHERE substr(o.order_date, 1, 7) = strftime('%Y-%m', c.cohort_month || '-01', '+2 month')
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
(а) отношение "до/после", (б) абсолютный пол на исходном замере (иначе
на быстрой машине отношение проходит на шумовых долях секунды) и
(в) план запроса (`EXPLAIN QUERY PLAN`). Подробности порога — `step-08.md`, 1.5.

### Контрольная точка датасета (не коммитится, сверяется до задач)

`generate_activity_log.py` печатает её сам после генерации — сравнить
дословно, до того как приступать к задачам `step-08.md`:

| Показатель | Значение |
|---|---|
| Строк в `activity_log` | **4 800 000** |
| sha256 первых 1000 строк (`ORDER BY log_id`) | `93fdb9a1e351c61a938b30cbd0ee80a1e3a4605fd50b9d93318b00da4caed0eb` |

Проверено перегенерацией на двух чистых базах подряд — оба числа
совпали побайтово оба раза. Если у учащегося число строк или sha256 не
совпали — не переходить к задачам, а сначала проверить: та же версия
`generate_activity_log.py` (без правок), та же последовательность
загрузки (`schema.sql` → `seed.sql` → `retention_seed.sql` → генератор,
в этом порядке, ровно один раз каждый), тот же Python (версия `random`
не должна расходиться между актуальными 3.x, но если расхождение не
находится — это отдельная находка, а не тихо игнорируемая мелочь).

Проверено также при переопределении объёма (`generate_activity_log.py
m3.db 1000` и `... m3.db 500`): при `n_rows_target ≥ 1000` sha256
совпадает с указанным выше независимо от N (100 000 и 4 800 000 строк
дали идентичный хэш в этом заходе); при `n_rows_target < 1000` скрипт
печатает явное сообщение «контрольная точка не определена» вместо
хэша от неполного набора или падения. **Инвариант «хэш не зависит от
N» держится только пока генератор пишет строки одним
последовательным циклом без перемешивания и без вычислений, зависящих
от общего `n_rows_target` (см. докстринг `generate_activity_log.py`)**
— если логика генерации изменится (батчи со своим состоянием ГПСЧ,
перемешивание порядка вставки, дата как функция от `N`), инвариант
проверяется заново, а не считается гарантией навсегда.

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

---

# Переход на PostgreSQL (`step-09.md`–`step-12.md`)

Все числа этого раздела получены прогоном на **обоих** движках, на одной
машине, в одном заходе: SQLite 3.45.1 (модуль стандартной библиотеки
Python 3.11.9) и PostgreSQL 17.6 (x86_64-windows). Датасет тот же:
`schema.sql` + `seed.sql` + `retention_seed.sql`, перенесённый по
инструкции `step-09.md`, плюс `activity_log` из `generate_activity_log.py`.

## Перенос (`step-09.md`)

| Проверка | Значение | Совпадает с SQLite |
|---|---|---|
| Строк `customers` | 252 | да |
| Строк `products` | 6 | да |
| Строк `orders` | 366 | да |
| Строк `order_items` | 23 | да |
| Строк `payments` | 13 | да |
| `SUM(amount)` по всем 366 заказам | 317959.87 | да |
| `SUM(amount)`, `status='completed' AND order_id < 200` | 8600.00 | да (контрольная сумма модуля из `step-00.md`) |
| Заказов, где `SUM(quantity*unit_price) <> amount` | 0 | да |
| Несовпадений инварианта «платёж ⟺ completed» (19 исходных заказов) | 0 | да |

Отображение денежного типа — замер, показывающий цену наивного выбора:

| Тип колонки `amount` в PostgreSQL | `SUM(amount)` по 366 заказам |
|---|---|
| `NUMERIC(10,2)` (взято в `schema_pg.sql`) | **317959.87** |
| `REAL` (буквальный перенос типа из `schema.sql`) | **317959.84** |
| `DOUBLE PRECISION` | **317959.87000000005** |

В SQLite та же сумма — 317959.87. Построчно ни одно из 366 значений при
переносе в `REAL` не искажается настолько, чтобы отличаться в двух знаках
(запрос `WHERE amount <> amount::real::numeric(10,2)` даёт 0 строк) —
расходится только агрегат.

Порядок загрузки: `customers`, `products`, `orders`, `order_items`,
`payments`. При нарушении (`order_items` до `products`) PostgreSQL
отвечает `insert or update on table "order_items" violates foreign key
constraint "order_items_product_id_fkey"`, `DETAIL: Key (product_id)=(1002)
is not present in table "products"`, и загружает 0 строк.

Выгрузка `.dump` из SQLite, поданная в `psql`, обрывается на 25-й строке:
`ERROR: relation "orders" does not exist` — SQLite выдаёт таблицы в
порядке создания (`customers`, затем `order_items`), а `order_items`
ссылается на `orders` ниже по файлу. После отката в базе остаётся 0
таблиц (проверено запросом к `information_schema.tables`). Отдельно:
`PRAGMA foreign_keys=OFF;` даёт `ERROR: syntax error at or near "PRAGMA"`.

## Девять расхождений диалектов (`step-10.md`)

Все девять проверены выполнением на обоих движках.

| № | Откуда | SQLite | PostgreSQL |
|---|---|---|---|
| 1 | `step-02.md` 1.3, `HAVING total > 500` | 7 строк | `ERROR: column "total" does not exist` |
| 2 | `step-02.md` 1.6, `order_id` мимо `GROUP BY` | 3 строки | `ERROR: column "orders.order_id" must appear in the GROUP BY clause or be used in an aggregate function` |
| 3 | `step-02.md` 1.6, `WHERE SUM(amount) > 500` | `OperationalError: misuse of aggregate: SUM()` | `ERROR: aggregate functions are not allowed in WHERE` |
| 4 | `step-01.md` 1.6, `status = "completed"` | 13 | `ERROR: column "completed" does not exist` |
| 5 | `step-01.md` 1.6, `status LIKE 'COMPLETED'` | **360** | **0, без ошибки** (`ILIKE` даёт 360) |
| 6 | `step-07.md` 1.3, `substr(order_date, 1, 7)` | `2026-05` | `ERROR: function substr(date, integer, integer) does not exist` |
| 7 | `step-07.md` 1.3, `strftime('%Y-%m', order_date)` | `2026-05` | `ERROR: function strftime(unknown, date) does not exist` |
| 8 | `step-06.md` задача 6, `ROUND(AVG(amount), 2)` | 661.54 | 661.54 на `NUMERIC(10,2)`; `ERROR: function round(double precision, integer) does not exist` на `DOUBLE PRECISION` |
| 9 | `step-08.md` 1.3, `EXPLAIN QUERY PLAN` | план | `ERROR: syntax error at or near "QUERY"` |

Правка расхождения 1 — `HAVING SUM(amount) > 500`; после неё PostgreSQL
даёт тех же 7 клиентов (1, 2, 3, 5, 8, 9, 12) с суммами 2480.00, 1320.00,
980.00, 1150.00, 1485.00, 510.00, 675.00.

Зависимость `дата::text` от настройки сервера (почему `to_char` надёжнее
приведения к тексту): на заказе 103 (дата 2026-06-11) `substr(order_date::text,
1, 7)` даёт `2026-06` при `DateStyle = ISO, MDY` (по умолчанию),
`11.06.2` при `German, DMY` и `11/06/2` при `SQL, DMY`. Ошибки нет ни в
одном случае. `to_char(order_date, 'YYYY-MM')` даёт `2026-06` при всех
трёх.

## Переносимость A1 (`step-10.md`)

Все 6 запросов задания `step-06.md` и разобранный пример из его 1.3
выполняются в PostgreSQL **без единой правки синтаксиса** и дают тот же
результат, что в SQLite. Проверено построчно по всем 6 эталонным CSV
(`a1_task1_running_total.csv` … `a1_task6_diff_avg.csv`): 13, 13, 13, 13,
6, 13 строк, расхождение значений 0.

Единственная необходимая правка — не диалектная, а по объёму: после
`retention_seed.sql` в `orders` 366 строк, и без фильтра `order_id < 200`
запросы возвращают 360 строк вместо 13 (на обоих движках одинаково).

Сравнение с эталоном — **по значениям, а не побайтово**: `NUMERIC(10,2)`
печатает `1200.00` там, где SQLite печатает `1200.0`.

## A3 на PostgreSQL (`step-11.md`)

Запрос из `step-07.md` после трёх правок (`substr` → `to_char` в двух
местах, `strftime(..., '+k month')` → `to_date(...) + INTERVAL 'k month'`)
даёт те же 12 когорт. Значения совпадают с `a3_cohort_retention_m1.csv` и
`a3_cohort_retention_m2.csv` полностью; `retention_pct` печатается как
`35.00` против `35.0` в SQLite (тип, не число).

Вариант через `date_trunc('month', дата)::date` даёт те же 12 строк на
обоих горизонтах (M1: суммарно 73 вернувшихся; M2: 3, 5, 2, 3, 6, 5, 2,
1, 1, 2, 2, 2 — совпадает с CSV). `date_trunc` возвращает `timestamp with
time zone` (проверено `pg_typeof`), отсюда необходимость `::date`.

Числа для типичных ошибок шага:

| Ошибка | Результат |
|---|---|
| `to_date(cohort_month,'YYYY-MM') + 1` вместо `+ INTERVAL '1 month'` | `retained` = 20 во всех 12 когортах (100.00%) вместо 7, 8, 4, 6, 8, 5, 7, 8, 7, 4, 4, 5 |
| `DATE '2025-01-15' + 1` | `2025-01-16` (день, не месяц) |
| `DATE '2025-01-15' + INTERVAL '1 month'` | `2025-02-15 00:00:00` |

Числа для типичных ошибок `step-07.md` (те же на обоих движках —
свойство датасета, не движка):

| Ошибка | Результат |
|---|---|
| «вернулся когда-либо после первого заказа» вместо точного месяца | по 12 когортам 8, 11, 6, 8, 11, 10, 9, 9, 8, 5, 4, 7; для `2025-05` это 11 против верных 6 на горизонте M2 |
| группировка по `first_date` целиком (день, а не месяц) | 178 когорт вместо 12 (столько различных дней у первых заказов 240 клиентов) |

## A4 на PostgreSQL (`step-12.md`)

Перенос `activity_log`: выгрузка в CSV 4.4 с, файл 160 МБ, загрузка
`\copy` — 12.1 с, вывод `COPY 4800000`.

Парные замеры, одна машина, 4 800 000 строк:

| Замер | SQLite 3.45.1 | PostgreSQL 17.6 |
|---|---|---|
| Запрос 1.3 (`login`), без индексов | 57.378 с | 53.594 с |
| Запрос 1.3, индекс `(customer_id, event_type)` | 0.034 с | 0.045 с |
| Ускорение 1.3 | ×1665 | ×1191 |
| Запрос 1.4 (июнь), без индексов | 57.122 с | 65.097 с |
| Запрос 1.4, «чужой» индекс `(customer_id, event_type)` | 12.363 с (×4.6) | 11.515 с (×5.7) |
| Запрос 1.4, индекс `(customer_id, event_date)` | 0.018 с | 0.020 с |
| Ускорение 1.4 | ×3258 | ×3255 |
| Построение индекса `(customer_id, event_type)` | 2.55 с | 2.21 с |
| Построение индекса `(customer_id, event_date)` | 2.91 с | 1.91 с |

Замеры SQLite в этой таблице сделаны заново, на той же машине, что и
замеры PostgreSQL, — поэтому они отличаются от чисел раздела «A4» выше
(70.66 с / 0.044 с, другая машина и другой заход). Совпадает то, что
проверяется критерием: план запроса и порядок ускорения.

Планы для `activity_log` (запрос 1.4):

| Состояние | SQLite (`EXPLAIN QUERY PLAN`) | PostgreSQL (`EXPLAIN (ANALYZE)`) |
|---|---|---|
| Без индексов | `SCAN a` | `Seq Scan on activity_log a`, `loops=252`, `actual rows=1564`, `Rows Removed by Filter: 4798436` |
| «Чужой» индекс | `SEARCH a USING INDEX idx_activity_customer_type (customer_id=?)` | `Bitmap Heap Scan`, ниже `Bitmap Index Scan on idx_activity_customer_type`, `Rows Removed by Filter: 17484`, `Heap Blocks: exact=3577826` |
| Нужный индекс | `SEARCH a USING COVERING INDEX idx_activity_customer_date (customer_id=? AND event_date>? AND event_date<?)` | `Index Only Scan using idx_activity_customer_date`, `Heap Fetches: 0` |

`EXPLAIN (ANALYZE)` на запросе без индекса занял 65.107 с — столько же,
сколько сам запрос (65.097 с): `ANALYZE` означает реальное выполнение.

Результат (252 строки) идентичен во всех шести замерах на обоих движках.

Тип `event_date` при переносе: `TEXT` и `DATE` дают одинаковый результат
на `BETWEEN '2025-06-01' AND '2025-06-30'` (проверено на клиентах 1, 2,
340: 1550, 1582, 1561 события в обоих вариантах) — совпадение держится
только на формате `ГГГГ-ММ-ДД`, где лексикографический порядок совпадает
с хронологическим. В `step-12.md` берётся `DATE`.
