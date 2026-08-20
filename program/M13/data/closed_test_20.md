# Закрытый тест J1/J2 — 20 вакансий (не встречавшихся в `step-01.md`)

Источник — `research/market.md`, разделы «LinkedIn / Otta» (13
вакансий) и «RemoteOK / WeWorkRemotely» (12 вакансий), уже проверенные
fetch'ем на Фазе 0 (правило 3 CLAUDE.md); разметка «открыта/закрыта/
неясно» и маркеры гео-ограничения — сделаны этим заходом, при
написании `step-02.md`, независимо от Фазы 0.

**Не открывать до задания `step-02.md`, пункт 2.** Таблица — эталон для
самопроверки после того, как разметка сделана самостоятельно.

| № | Вакансия / компания | Регион (из текста) | Формат | Классификация | Маркер(ы) |
|---|---|---|---|---|---|
| 1 | Senior Data Analyst, Customer Analytics — Stryker | Michigan, US | Remote | Закрыта | явный штат США |
| 2 | Principal Business Analyst, Fraud — Mission Lane | Remote US | Remote | Закрыта | явный список стран (US) |
| 3 | Senior Analyst, Portfolio Strategy — Forward Financing | Remote US | Remote | Закрыта | явный список стран (US) |
| 4 | Data Analyst, Reporting Partnerships — Doximity | SF/Remote US | Remote | Закрыта | явный список стран (US) |
| 5 | Senior Revenue Analytics Analyst — GitLab | Remote Canada/US | Remote | Закрыта | явный список стран (Canada/US) |
| 6 | Lead Data Analyst, MyPay — Chime | Chicago/NY/SF | Hybrid (4-5д офис) | Закрыта | гибрид с обязательными визитами в конкретные города США |
| 7 | Insights Analyst, Dispute Experience — Chime | Remote US | Remote | Закрыта | явный список стран (US) |
| 8 | Data Analyst — Hostinger | Вільнюс, Литва | Hybrid | Закрыта | конкретный город + гибрид |
| 9 | Junior Business & Data Analyst — Upgrade, Inc. | US (SF) | Remote | Закрыта | явный город/страна (US) |
| 10 | Data Analyst — Fusemachines | Remote (Канада) | Remote | Закрыта | явный список стран (Canada) |
| 11 | Data Analyst — Haystack (агентство) | Вена, Австрия | не указан | Закрыта | конкретный город + требование немецкого языка (де-факто исключает без него) |
| 12 | BI Analyst — Joblinxsapp (госсектор Канады) | Канада (Альберта) | Remote, контракт | Закрыта | явная страна/провинция + проверка на судимость (требует местного резидентства) |
| 13 | Data Analyst / Curam — AHU Technologies | Remote (US госсектор) | Remote, контракт | Закрыта | госсектор США — контракты с госорганами почти всегда требуют гражданства/резидентства США, даже без явного указания |
| 14 | Data Analyst (Product & Customer) — Oowlish | Бразилія | Remote | Неясно | регион в карточке — Бразилия, но компания-аутсорсер может нанимать шире; текста недостаточно для однозначного вывода без перехода на страницу компании |
| 15 | Data Analyst Excel — YO IT Consulting | Remote (страна не указана) | Remote, контракт | Неясно | ни явного списка стран, ни явного «hires globally» — отсутствие ограничения не то же самое, что подтверждённая открытость |
| 16 | Junior Data Analyst — Numa | Лиссабон/Європа | Remote | Неясно | «Європа» как регион не уточняет, входит ли Украина в допустимый список — требует перехода к полному тексту вакансии |
| 17 | Home-Based Marketing Data Analyst — DCX | Anywhere (факт. Азия/PH-смена) | Remote | Неясно (коллизия) | заявлено «Anywhere», но описанная рабочая смена привязана к филиппинскому часовому поясу — классический пример расхождения метаданных и тела вакансии, тот же класс, что YipitData/Sardine в `step-01.md` |
| 18 | Data Analyst — Stio® | US | Remote | Неясно | исходный текст обрезан при сборе на Фазе 0 (`research/market.md`, «не удалось подтвердить») — недостаточно данных для уверенной классификации, это тоже честный ответ «неясно», а не повод придумывать недостающее |
| 19 | Data Analyst — Hired | Worldwide | Remote | Открыта | явное «Worldwide», без страновых исключений в тексте |
| 20 | Data Analyst (AI Translation Quality) — OnTheGoSystems | Anywhere | Remote | Открыта | явное «Anywhere», требование — «самостоятельная постановка задач», не страна |

**Итог банка:** 13 закрыто, 5 неясно, 2 открыто. Соотношение (65% /
25% / 10%) само по себе учебный факт — большинство «remote» вакансий
международного рынка, попавших в выборку `research/market.md`, при
чтении текста целиком оказываются geo-restricted, что напрямую
подтверждает вывод раздела «Открыто для найма из Украины / B2B» того
же файла: 86% формально «remote» вакансий не открыты для Украины.
