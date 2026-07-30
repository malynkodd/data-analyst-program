-- Схема модуля M3 для PostgreSQL — те же 5 таблиц, что в schema.sql
-- (SQLite). Переход на PostgreSQL к концу модуля — решение 15
-- design/decisions.md; момент перехода (после step-08.md) — решение 19.
--
-- Отличия от schema.sql перечислены построчно в program/M3/step-09.md,
-- 1.3. Коротко: три типа отображены не один-в-один, и это сознательный
-- выбор, а не механическая замена слов:
--   TEXT (дата)  -> DATE     — у SQLite отдельного типа даты нет вовсе
--                             (sqlite.org/quirks.html, п. 3.2), у
--                             PostgreSQL есть; из-за этого substr() и
--                             strftime() по дате перестают работать —
--                             разбор в step-10.md.
--   REAL (деньги)-> NUMERIC(10,2) — REAL в PostgreSQL это 4 байта
--                             (6 знаков), а в SQLite 8 байт; прямое
--                             отображение REAL->REAL молча меняет
--                             SUM(amount) по 366 заказам с 317959.87 на
--                             317959.84 (замер — step-09.md, 1.3).
--   INTEGER PRIMARY KEY      — оставлен как есть: все id задаются явно
--                             при загрузке, автогенерация (GENERATED ...
--                             AS IDENTITY) не нужна и здесь не вводится.
--
-- Запуск (после createdb m3):
--     psql -U postgres -d m3 -f schema_pg.sql

DROP TABLE IF EXISTS payments, order_items, products, orders, customers CASCADE;

CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    city        TEXT NOT NULL
);

CREATE TABLE orders (
    order_id    INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    order_date  DATE NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('completed', 'cancelled', 'pending')),
    amount      NUMERIC(10,2) NOT NULL
);

CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    category   TEXT NOT NULL CHECK (category IN ('subscription', 'addon', 'service'))
);

CREATE TABLE order_items (
    order_item_id INTEGER PRIMARY KEY,
    order_id      INTEGER NOT NULL REFERENCES orders(order_id),
    product_id    INTEGER NOT NULL REFERENCES products(product_id),
    quantity      INTEGER NOT NULL,
    unit_price    NUMERIC(10,2) NOT NULL
);

CREATE TABLE payments (
    payment_id INTEGER PRIMARY KEY,
    order_id   INTEGER NOT NULL REFERENCES orders(order_id),
    paid_at    DATE NOT NULL,
    amount     NUMERIC(10,2) NOT NULL,
    method     TEXT NOT NULL CHECK (method IN ('card', 'bank_transfer'))
);

-- activity_log создаётся отдельно, в step-12.md: таблица на 4 800 000
-- строк генерируется локально и не коммитится (см. step-00.md).
