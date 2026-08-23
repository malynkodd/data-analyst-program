# Данные блока career («Выход»)

## Статус этого файла

Полная декларация — `program/career/step-00.md`. У блока нет генератора и
нет собственного датасета: материал шагов — артефакты, накопленные
учащимся за M0–M16 и P1–P6, плюс один внешний эталон,
`research/market.md` (колонка «Обязательные требования», 123 вакансии,
заполнена на Фазе 0).

## Файлы

| Файл | Роль | В git? |
|---|---|---|
| `check_cv.py` | Проверка шага 01: объём, разделы, опора строк на файлы, подтверждение инструментов | да |
| `check_portfolio.py` | Проверка шага 02: карточки проектов и пара «исходник — перевод» (умение K2) | да |
| `check_search.py` | Проверка шага 03: разбор вакансий против эталона (K1) и трекер (первое условие J3) | да |
| `cv_template.md` | Скелет резюме для копирования; он же отрицательный пример к `check_cv.py` | да |
| `reference/cv.md` | Заполненное резюме на артефактах этого репозитория — положительный пример | да |
| `reference/portfolio_readme.md` | Шесть карточек проектов | да |
| `reference/summary_ru.md` | Резюме анализа P4 на русском — исходник пары K2 | да |
| `reference/summary_en.md` | Он же на английском, 150 слов — перевод пары K2 | да |
| `reference/vacancy_notes.md` | Разбор пяти англоязычных fintech-вакансий — положительный пример K1 | да |
| `reference_answers.md` | Измеренные числа блока и обе половины каждого примера | да |

Папка `program/career/work/` — результат работы учащегося. В репозиторий
не коммитится, в `.gitignore` не заносится: она просто пуста до
прохождения блока.

## Проверка строк

| Файл | Что считается | Значение |
|---|---|---|
| `reference/cv.md` | слов | 197 |
| `reference/cv.md` | строк в разделе «Работы» | 6 |
| `cv_template.md` | слов | 163 |
| `reference/summary_ru.md` | слов | 127 |
| `reference/summary_en.md` | слов | 150 |
| `reference/summary_en.md` | доля слов латиницей | 99% |
| пара summary | вхождений чисел, сошлось | 14 из 14 |
| `reference/portfolio_readme.md` | карточек проектов | 6 |
| `reference/vacancy_notes.md` | разобранных вакансий | 5 |

Числа сверяются прогонами из `reference_answers.md`, не пересчётом в уме.
Прогон на машине автора 2026-08-23.

## Запуск проверок

```
python program\career\data\check_cv.py
python program\career\data\check_portfolio.py
python program\career\data\check_search.py
```

Без аргументов каждая читает файлы из `program\career\work\`. Чтобы
прогнать на эталоне:

```
python program\career\data\check_cv.py program\career\data\reference\cv.md
python program\career\data\check_portfolio.py program\career\data\reference
python program\career\data\check_search.py program\career\data\reference\vacancy_notes.md
```

У `check_search.py` вторым аргументом принимается путь к трекеру — иначе
он читает `program\M14\work\tracker.csv`, который заводит шаг M14.01.
