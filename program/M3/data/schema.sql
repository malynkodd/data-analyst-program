-- Схема модуля M3 целиком — 5 таблиц, объявлены в program/M3/step-00.md
-- ДО написания дальнейших шагов (правило "шаг 0", design/decisions.md,
-- решение 16). customers/orders уже используются в step-05.md — их
-- определения не менялись при добавлении остальных трёх таблиц.

CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    city        TEXT NOT NULL
);

CREATE TABLE orders (
    order_id    INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    order_date  TEXT NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('completed', 'cancelled', 'pending')),
    amount      REAL NOT NULL
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
    unit_price    REAL NOT NULL
);

CREATE TABLE payments (
    payment_id INTEGER PRIMARY KEY,
    order_id   INTEGER NOT NULL REFERENCES orders(order_id),
    paid_at    TEXT NOT NULL,
    amount     REAL NOT NULL,
    method     TEXT NOT NULL CHECK (method IN ('card', 'bank_transfer'))
);
