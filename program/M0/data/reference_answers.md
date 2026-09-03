# Контрольные числа для `orders_log.csv` (эталон)

Посчитано на зафиксированном файле `orders_log.csv` (500 строк). Все
числа получены запуском указанных скриптов — воспроизводимы командой из
таблицы.

## `count_lines.py`

| Команда | Результат |
|---|---|
| `count_lines.py orders_log.csv` | rows in file: **500** |
| `count_lines.py orders_log.csv --status shipped` | **304** |
| `count_lines.py orders_log.csv --status pending` | **117** |
| `count_lines.py orders_log.csv --status cancelled` | **79** |

Проверка суммы: 304 + 117 + 79 = 500.

## `find_row.py`

| Команда | total matches |
|---|---|
| `find_row.py orders_log.csv --contains damaged` | **47** |
| `find_row.py orders_log.csv --contains "customer cancelled"` | **57** |
| `find_row.py orders_log.csv --contains "out of stock"` | **22** |
| `find_row.py orders_log.csv --contains "awaiting warehouse"` | **89** |
| `find_row.py orders_log.csv --contains "payment pending"` | **28** |
| `find_row.py orders_log.csv --contains Lviv` | **62** |

Проверка сумм: 57 + 22 = 79 (= все `cancelled`); 89 + 28 = 117 (= все
`pending`).

## `view_head.py`

Первые 5 строк файла (включая заголовок), `view_head.py orders_log.csv --lines 5`:

```
order_id,order_date,city,status,note
D0001,2026-06-27,Odesa,shipped,delivered on time
D0002,2026-06-28,Kharkiv,shipped,delivered on time
D0003,2026-07-24,Odesa,shipped,delivered on time
D0004,2026-07-09,Dnipro,shipped,delivered on time
```

## `check_utf8.py`

Проверено на двух файлах вручную при написании шага (не хранятся в
репозитории — создавались и удалялись при проверке):

- Файл, сохранённый в кодировке UTF-8, с кириллическим текстом на 3
  непустых строках: `decoded as UTF-8: yes`, `non-empty lines: 3`,
  `contains non-ASCII characters: True`, `OK`, код выхода 0.
- Тот же текст, сохранённый в кодировке cp1251: `FAIL: file is not valid
  UTF-8 ('utf-8' codec can't decode byte 0xcc in position 0: invalid
  continuation byte)`, код выхода 1.
