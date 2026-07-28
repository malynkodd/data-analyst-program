# Рынок труда Data Analyst — доказательная база (Фаза 0.1)

Дата сбора: 2026-07-28. Все вакансии ниже — открыты на момент сбора,
ссылка на каждую проверена через fetch (получен полный текст объявления).
Вакансии, не прошедшие проверку (404, редирект на "похожие", логин-стена),
в выборку не включены и не считаются в статистике.

Методология: WebSearch/WebFetch по публичным страницам job-бордов для
сегментов Remote/EU/US и PL/CZ/DE/NL; для Украины — Claude in Chrome
(Djinni, DOU, Work.ua публично отдают полный текст вакансии без логина).
Цель — 150 вакансий: 60 remote-friendly EU/US/global, 40 Польша/Чехия/
Германия/Нидерланды, 30 Украина, срез Middle — не отдельный сегмент, а
метка внутри всех карточек.

Статус сбора по сегментам — см. в начале каждого раздела.

---

## Сегмент: Украина (Djinni / DOU / Work.ua) — 30/30

Собрано и подтверждено: 30 из 30 (14 Djinni, 10 DOU, 6 Work.ua).

### Djinni (14)

| # | Вакансия / компания | Домен | Локация | Формат | Уровень | Обязательные требования | Желательные | Вилка | English | Тестовое |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | [BI аналітик — ITExpert](https://djinni.co/jobs/839836-bi-analitik/) | Healthcare/MedTech | Киев | Гибрид | Middle (от 2 лет) | Power BI, Microsoft Fabric, SQL, опыт BI-аналитика, построение семантических моделей, DAX | Lakehouse/Warehouse в Fabric, валидация данных к ERP | не указано ($$-тир Djinni) | не требуется | нет данных |
| 2 | [Data Governance Manager — Ukrgasbank](https://djinni.co/jobs/839828-data-governance-manager/) | Fintech | Украина | Remote/гибрид | Senior (3-5 лет, PM-фокус) | DAMA DMBoK, DGI, TOGAF, COBIT, каталоги данных (OpenMetadata/DataHub/Collibra), KPI качества данных | ДСТУ ISO/IEC 38505, ISO 8000 | не указано ($$) | A2 | нет данных |
| 3 | [Web and Digital Data Analyst — Halo Lab](https://djinni.co/jobs/830326-web-and-digital-data-analyst/) | Agency/Design | Remote (весь мир) | Remote, part/full-time | Middle (от 3 лет) | GA4, Google Tag Manager, BigQuery, Power BI, A/B-тесты, модели атрибуции | Hotjar, сертификат Google | не указано ($$$) | B2 | есть |
| 4 | [Security Data Analyst — Risk Inc.](https://djinni.co/jobs/839747-security-data-analyst/) | Gambling | Remote (весь мир) | Remote | Middle+ (от 3 лет) | DLP-инструменты, SIEM, анализ security-логов, форензика | — | не указано ($$$$) | не требуется | нет данных |
| 5 | [Data Analyst (Marketing) — Evoplay](https://djinni.co/jobs/817920-data-analyst-marketing/) | Gaming (UA продукт) | Киев | Офис/гибрид/remote | Junior-Middle (от 2 лет) | Excel, Power BI, Tableau, Power Query, DAX | — | $1500-3000 (похожие) | не указано | нет данных |
| 6 | [BI Developer/Data Analyst — Bulls-media](https://djinni.co/jobs/839716-bi-developer-data-analyst/) | Advertising | Киев | Гибрид | Middle (от 2 лет) | Power BI, DAX, SQL, Excel/Sheets формулы, Python | non-relational DB | не указано ($$$) | B2 | нет данных |
| 7 | [Product Analyst — United Tech](https://djinni.co/jobs/771604-product-analyst/) | Social/streaming | Remote (EU+UA) | Remote | Senior (от 4 лет) | Advanced SQL, статистика (hypothesis testing, causal inference, regression), A/B-тесты, product/marketing analytics | GBQ, Python, R, cohort/LTV/churn | $2000-3700 (похожие) | B1 | нет данных |
| 8 | [Marketing Analyst — United Tech](https://djinni.co/jobs/814857-marketing-analyst/) | Social/streaming | Remote (весь мир) | Remote | Middle (от 3, рассм. от 2) | Strong SQL, BI (Tableau/Looker), маркетинговые метрики (CAC/ROI/LTV/ARPU), атрибуция | Python, ML basics | не указано ($$$) | B2 | нет данных |
| 9 | [Data Analyst (SQL/Python, Operations) — Meduzzen](https://djinni.co/jobs/831210-data-analyst-sql-python-operations-focus/) | Outsource/Other | Remote (весь мир) | Remote | Middle (от 4, рассм. от 3) | SQL, Python, Excel, автономная работа в distributed teams | — | не указано ($$$) | B2 | logic + Python assessment |
| 10 | [Marketing Data Analyst — boringseo.team](https://djinni.co/jobs/818597-marketing-data-analyst/) | Gambling/Affiliate | Remote (весь мир) | Remote | Middle (от 2 лет) | SQL (сложные запросы), Tableau/Power BI/Looker, iGaming-метрики (CPA/RevShare/FTD), API-интеграции, Excel продвинутый | Python | $1500-3000 (похожие) | не требуется | есть (испыт. срок с целями) |
| 11 | [Marketing Data Analyst (iGaming/Affiliate SEO) — boringseo.team](https://djinni.co/jobs/824427-marketing-data-analyst-igaming-affiliate-seo/) | Gambling/Affiliate | Remote (весь мир) | Remote | Middle (от 3 лет) | Power BI/Looker, iGaming/affiliate-метрики, Excel продвинутый | — | $2000-3500 (похожие) | не требуется | есть |
| 12 | [Data System Analyst — Nova Digital](https://djinni.co/jobs/839669-data-system-analyst/) | Telecom (UA продукт) | Remote (EU+UA) | Remote | Senior (от 3 лет) | ERD, SQL/СУБД, BPMN/UML/DFD, BRD/FSD/SRS документация, SDLC, Agile/Scrum | — | $2000-3700 (похожие) | B1 | нет данных |
| 13 | [Data analyst\\engineer — NuxGame](https://djinni.co/jobs/839659-data-analyst-engineer/) | Gambling | Remote (EU+UA) | Remote | Middle (2-3 года) | Advanced SQL, Python (pandas/numpy), BI (Tableau/Power BI), ETL/ELT концепции | dbt, Airflow/Kafka, ClickHouse/BigQuery, Snowflake | $2000-3700 (похожие) | B1 | нет данных |
| 14 | [Credit Risk Analyst — RiskSeal](https://djinni.co/jobs/834236-credit-risk-analyst/) | Fintech | Remote (EU+UA) | Remote | Middle (от 2 лет) | Python, SQL, credit risk modelling, scoring, PD-модели, логрегрессия/деревья/ML | альтернативные данные, model governance | не указано ($$$$) | B2 | нет данных |

### DOU (10)

| # | Вакансия / компания | Домен | Локация | Формат | Уровень | Обязательные требования | Желательные | Вилка | English | Тестовое |
|---|---|---|---|---|---|---|---|---|---|---|
| 15 | [Head of Analytics — PawChamp, SKELAR](https://jobs.dou.ua/companies/skelar/vacancies/365754/) | Consumer/PetTech | Киев/Львов/Варшава/remote | Гибрид/remote | Senior/Head | Опыт Lead/Head of Analytics, построение data foundation, продуктовая+маркетинговая+бизнес-аналитика, управление командой | AI-автоматизация аналитики | не указано | не указано | нет данных |
| 16 | [Reporting Analyst — Platform, SKELAR](https://jobs.dou.ua/companies/skelar/vacancies/345294/) | Finance (внутр.) | Киев | Офис | Middle (3-4 года) | Управленческая отчётность, финконтроллинг, Excel продвинутый, ERP-автоматизация, дашборды | опыт в Big-4/FMCG | не указано | не указано | нет данных |
| 17 | [Head of Analytics — Galaktica](https://jobs.dou.ua/companies/galaktica/vacancies/366178/) | Product/Mobile | Киев/Львов/Одесса/Ларнака/remote | Гибрид/remote | Senior/Head | Стратегия аналитики, BI-инфраструктура, продукт+маркетинг+бизнес-аналитика, управление командой, работа с C-level | AI/автоматизация | не указано | не указано | нет данных |
| 18 | [Sr. Data Analyst (Supply Operations) — Glovo](https://jobs.dou.ua/companies/glovo/vacancies/361390/) | Delivery/Marketplace | Киев | Гибрид | Senior (от 2 лет, по факту требования — Middle+) | SQL уверенный, работа с большими данными, Excel/Sheets, дашборды/KPI | Looker/Tableau/Power BI | не указано | B2+ | нет данных |
| 19 | [Marketing Analyst — Code Street, SKELAR](https://jobs.dou.ua/companies/skelar/vacancies/367576/) | Social/Streaming | Киев | Гибрид | Junior-Middle (от 1 года) | SQL уверенный, Python (pandas/numpy/statsmodels), когортный/воронковый анализ, A/B-тесты, CAC/LTV/ROAS | MMP, ML (churn/LTV forecasting), Amplitude/Mixpanel | не указано | не указано | нет данных |
| 20 | [Senior Data Analyst (AI) — NerdySoft](https://jobs.dou.ua/companies/nerdysoft/vacancies/359877/) | Fintech/CreditTech | Remote | Remote | Senior | Very strong SQL, lending/banking domain, semantic models, AI-агенты/LLM для аналитики | Snowflake, Snowflake Cortex AI, Power BI | не указано | не указано | нет данных |
| 21 | [Senior Data Analyst — Starlight Media](https://jobs.dou.ua/companies/starlightmedia/vacancies/363437/) | Media | Remote | Remote | Senior (от 2 лет) | Экспертный SQL и Python, BigQuery/GCC, матстатистика, прогнозные модели, ETL, Looker Studio/Power BI | n8n, Microsoft Data Products | $1300-1800 | не указано | нет данных |
| 22 | [Data Analyst (Performance Marketing) — BetterMe](https://jobs.dou.ua/companies/betterme/vacancies/331277/) | Health/Wellness | Киев/remote/за рубежом | Remote/гибрид | Middle (от 2 лет) | SQL и Excel полное владение, Python для скриптинга, Tableau, LLM API/prompt engineering | Amplitude/Firebase/AppsFlyer, A/B-тесты, Ads API | не указано | Strong (не указан CEFR) | нет данных |
| 23 | [Data Analyst (Conversion & Growth) — 4bill](https://jobs.dou.ua/companies/4bill-io/vacancies/367332/) | Fintech/Payments | Remote | Remote | Middle (от 2 лет) | SQL (чтение сложных запросов), причинно-следственный анализ, Power BI | A/B-тесты, Excel/Sheets продвинутый | не указано | не указано | нет данных |
| 24 | [Product Data Analyst — appflame](https://jobs.dou.ua/companies/appflame/vacancies/367532/) | Dating/Social (UA продукт) | Киев | Офис | Junior-Middle (от 2 лет) | SQL уверенный, 1 BI-инструмент (желательно Tableau), базовая статистика, data storytelling | Python/R, A/B statistical significance, ClickHouse, ML | не указано | не указано | нет данных |

### Work.ua (6)

| # | Вакансия / компания | Домен | Локация | Формат | Уровень | Обязательные требования | Желательные | Вилка | English | Тестовое |
|---|---|---|---|---|---|---|---|---|---|---|
| 25 | [Аналітик з управлінської звітності — UKRNAFTA](https://www.work.ua/jobs/8350668/) | Oil&Gas (гос.) | не указано (Украина) | не указано | не указано | не указано (текст описания — общий про компанию, конкретные требования не зафиксированы) | — | не указано | не указано | нет данных |
| 26 | [Marketing Data Analyst (SQL) — «Є гроші»](https://www.work.ua/jobs/8164251/) | Fintech (МФО) | Украина, Remote | Remote | Junior-Middle | SQL-запросы (join, агрегации), Excel/Sheets автоматизация, маркетинговые KPI (CPA/CPL/ROI/ROMI), когортный/retention-анализ | — | 30 000–40 000 грн | не указано | нет данных |
| 27 | [Аналітик (Power BI) — Symbol](https://www.work.ua/jobs/8166588/) | Retail/Luxury | Украина | не указано | Junior (от 1 года) | MS SQL, Power BI (Power Pivot, Power Query) на высоком уровне, визуализация данных | — | не указано | не указано | нет данных |
| 28 | [Аналітик з моделювання фінансових ризиків — PwC SDC Lviv](https://www.work.ua/jobs/8332893/) | Consulting (Big4) | Львов/Remote | Remote/офис | Junior-Middle | не полностью зафиксировано (страница обрезана при сборе) — упомянуты английский и польский курсы, менторинг | — | не указано | требуется (уровень не указан) | нет данных |
| 29 | [Операційний аналітик (продажі) — Everstar](https://www.work.ua/jobs/7715235/) | Defense/Manufacturing | Киев | Офис | Middle (от 2 лет, факт. требуют 5) | Excel (Macros), 1С, Jira, Google Workspace, дашборды (ТЗ на создание) | Power BI | не указано | не указано | нет данных |
| 30 | [Фахівець з аналітичної роботи — WOG](https://www.work.ua/jobs/5892239/) | Retail/Fuel | Луцк | Офис | Junior (от 1 года) | Excel (формулы, сводные таблицы), BAS (1С), базовый бухучёт | Tableau, OLAP | не указано | не указано | нет данных |

**Примечание по сегменту:** вакансия #25 (Work.ua, UKRNAFTA) прошла fetch-проверку
(страница открылась, компания подтверждена), но JS-выжимка вернула только
блок "похожие вакансии компании" без основного текста требований — вероятно,
описание подгружается динамически и не попало в снятый DOM-срез. Ссылка
рабочая, вакансия реальная, но детальные требования не зафиксированы честно
как "не указано", а не выдуманы. Вакансия #28 (PwC) — текст был обрезан
инструментом на середине списка требований; ключевые технические навыки
не попали в срез, зафиксировано только то, что было получено.

---

## Сегмент: Remote-friendly EU/US/global

Цель: 60. Собрано 62/60: RemoteOK/WeWorkRemotely (12), LinkedIn/Otta+ATS
(13), Indeed (16), доп. сбор Wellfound/WWR/RemoteOK/careers (21) → 62.

### LinkedIn / Otta (+ Greenhouse/Ashby/Lever как разрешённая замена) — 13/20

LinkedIn и Otta оказались почти непригодны для честной fetch-проверки:
9 из 10 прямых ссылок LinkedIn редиректят на бот-стену поиска без логина;
9 из 9 вакансий Otta/Welcome to the Jungle показали "Job no longer
available" (индекс площадки устарел). Пришлось расширить на карьерные
страницы компаний (Greenhouse/Ashby/Lever, разрешено ТЗ) — там тоже
высокий процент брака: десятки найденных вакансий уже закрыты. Итог: 13
подтверждённых. Wellfound/WeWorkRemotely — 403; Workday — JS не
рендерится; BuiltIn — все найденные помечены removed.

| # | Вакансия / компания | Домен | Регион | Формат | Уровень | Обязательные требования | Желательные | Вилка | English | Тестовое |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | [Senior Data Analyst, Customer Analytics — Stryker](https://www.linkedin.com/jobs/view/senior-data-analyst-customer-analytics-remote-at-stryker-4440277907) | Medtech | Michigan, US | Remote | Middle | Bachelor's, 2+ года, Power BI/Excel, SQL Server | Master's, Python/R, статистика | $77.7k–168.4k | не указано | нет |
| 2 | [Principal Business Analyst, Fraud — Mission Lane](https://job-boards.greenhouse.io/missionlane/jobs/8624381002) | Fintech | Remote US | Remote | Senior/Principal | 3+ года, SQL/Python, A/B/Champion-Challenger, quant degree | Fraud strategy, стартап-опыт | $118k–135k+бонус | не указано | нет |
| 3 | [Business Analysis, Acquisitions — Mission Lane](https://job-boards.greenhouse.io/missionlane/jobs/8445714002) | Fintech | Remote US | Remote | Middle-Senior | 2-7 лет, SQL/Python, quant degree | Consumer lending, AI-coding assistants | $118k–157k | не указано | нет |
| 4 | [Data Analyst (Product & Customer) — Oowlish](https://jobs.lever.co/oowlish/4d812d70-6ae0-4640-b6e9-98c7cc9c4080) | IT-аутсорс/SaaS | Бразилия | Remote | Middle | 3+ года, SQL, Python/R, дашборды | AI-инструменты | не указана | fluent (обязательно) | нет |
| 5 | [Senior Analyst, Portfolio Strategy — Forward Financing](https://jobs.ashbyhq.com/forward%20financing/ad368d1e-bc13-4611-9ed6-d1d1d7da6c52) | Fintech (MCA) | Remote US | Remote | Senior (5+ лет) | Excel/SQL/Tableau/Python, regression/decision trees/A-B | Consumer credit опыт | $135k–170k+10% | не указано | нет |
| 6 | [Data Analyst, Reporting Partnerships — Doximity](https://job-boards.greenhouse.io/doximity/jobs/7787892) | Healthtech | SF/Remote US | Remote | Middle (2+ года) | Продвинутый SQL, Python-скрипты, client-facing коммуникация | — | $77k–134k+equity | не указано | нет |
| 7 | [Product Analyst — Buildkite](https://job-boards.greenhouse.io/buildkite/jobs/5237220008) | DevTools/CI-CD | US West Coast | Remote | Middle (2-4 года) | SQL, Metabase/Looker/Tableau, продуктовая аналитика, статистика | Python/R, Snowflake/dbt | не указана | не указано | нет |
| 8 | [Senior Revenue Analytics Analyst — GitLab](https://job-boards.greenhouse.io/gitlab/jobs/8616308002) | DevOps SaaS | Remote Canada/US | Remote | Senior | Analytics в pre-sales/SaaS, сложный SQL, Python | — | $115.2k–194.4k | не указано | нет |
| 9 | [Lead Data Analyst, MyPay — Chime](https://job-boards.greenhouse.io/chime/jobs/8576707002) | Fintech/Neobank | Chicago/NY/SF | Hybrid (4-5д офис) | Lead/Senior | 7+ лет credit risk, экспертный SQL, Python (Pandas/Scikit-learn), A/B | Fintech/EWA сектор | $152k–210k+бонус | не указано | нет |
| 10 | [Senior Data Analyst, New Account Risk — Chime](https://job-boards.greenhouse.io/chime/jobs/8637297002) | Fintech | SF, US | Hybrid (4д офис) | Middle-Senior | 3+ года fraud/risk, SQL, Looker/Hex, Excel | Python/R, identity fraud | $133k–185k+бонус | не указано | нет |
| 11 | [Insights Analyst, Dispute Experience — Chime](https://job-boards.greenhouse.io/chime/jobs/8565199002) | Fintech | Remote US | Remote | Senior (5+ лет) | SQL, Python/R, статистика, T&S/Fraud/Risk опыт | ML-эвалюация, Looker/Mode | $138k–190k+бонус | не указано | нет |
| 12 | [Data Analyst — Modern Health](https://job-boards.greenhouse.io/modernhealth/jobs/8550544002) | Healthtech (mental health) | Remote US | Remote | Middle (2+ года) | SQL, Python/R, dbt, статистика, Looker/Tableau/Omni | Master's, HIPAA | $90.6k–125.4k | не указано | нет |
| 13 | [Data Analyst — Hostinger](https://jobs.ashbyhq.com/hostinger/1e28a4d4-0988-4dfb-9c90-9bc413d5c99f) | Web-hosting/SaaS | Вильнюс, Литва | Hybrid | Middle (2+ года) | SQL, Tableau, коммуникация | — | от €3800/мес gross | не указано | нет |

*Отбраковано: 9 LinkedIn (редирект на поиск), 9 Otta/WTTJ (closed), десятки Greenhouse/Ashby/Lever ссылок вели на уже закрытые вакансии, 5 Workday (JS не рендерится), 3 BuiltIn (removed).*

### RemoteOK / WeWorkRemotely — 12/20

Найдено 33 уникальных кандидата, подтверждено (открыто и актуально) 12.
**Оба источника отдают HTTP 403 обычному WebFetch на каждый URL** — все
подтверждённые ниже получены через альтернативный fetch-инструмент;
12 живых вакансий не удалось прочитать из-за таймаутов/403 и не включены
в выборку (это ограничение доступа в моменте сбора, а не признак
недействительности вакансий). Ещё 9 отбракованы как закрытые/устаревшие.

| # | Вакансия / компания | Домен | Регион | Формат | Уровень | Обязательные требования | Желательные | Вилка | English | Тестовое |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | [Data Analyst — ActivTrak](https://remoteok.com/remote-jobs/remote-data-analyst-activtrak-1133346) | HR-tech/SaaS | Remote (US) | Remote | Middle (3+ года) | Продвинутый SQL, BI (Tableau/Power BI DAX/Looker Studio/Qlik), Python, API, ETL/DWH | Workforce Analytics | не указана | не указано | нет |
| 2 | [Junior Business & Data Analyst — Upgrade, Inc.](https://remoteok.com/remote-jobs/remote-junior-business-amp-data-analyst-upgrade-inc-1133488) | Fintech | US (SF) | Remote | Junior (2+ года) | SQL (joins/CTE/window functions), Tableau, Excel, Redshift/Databricks, AI-инструменты (Claude/ChatGPT) | Гипотезы под руководством | $75 000–95 000/год + equity | обязателен | нет |
| 3 | [Data Analyst Excel — YO IT Consulting](https://remoteok.com/remote-jobs/remote-data-analyst-excel-yo-it-consulting-1134019) | AI data labeling (агентство) | Remote | Remote, контракт | не указан | Excel в бизнес-контексте, внимание к деталям, коммуникация | Презентации, доп. BI | не указана | подразумевается | нет |
| 4 | [Data Analyst — Fusemachines](https://remoteok.com/remote-jobs/remote-data-analyst-fusemachines-1133041) | Enterprise AI | Remote (Канада) | Remote | Senior (8+ лет) | Snowflake 5+ лет, DBT, сильный SQL, EDW, data modeling, менторство | — | не указана | не указано | нет |
| 5 | [Junior Data Analyst — Numa](https://remoteok.com/remote-jobs/remote-junior-data-analyst-numa-1134429) | PropTech/Hospitality | Лиссабон/Европа | Remote | Junior | SQL + Looker/Tableau/Power BI, Excel/Sheets продвинутый | — | не указана | не указано | нет |
| 6 | [Data Analyst — Haystack (агентство)](https://remoteok.com/remote-jobs/remote-data-analyst-haystack-1134078) | Стройматериалы | Вена, Австрия | не указан | Middle | Power BI+DAX, SQL, немецкий И английский свободно | — | не указана | обязателен (с немецким) | нет |
| 7 | [BI Analyst — Joblinxsapp (агентство, госсектор Канады)](https://remoteok.com/remote-jobs/remote-business-intelligence-analyst-joblinxsapp-1133037) | Госсектор | Канада (Альберта) | Remote, контракт 18 мес. | Senior (5+ лет) | Power BI 5 лет, SQL 5 лет, DAX, Azure data platforms, проверка на судимость | Databricks, Azure Synapse | не указана | не указано | 3 референса вместо теста |
| 8 | [Data Analyst — Stio®](https://remoteok.com/remote-jobs/remote-data-analyst-stior-1132903) | E-commerce/Retail | US | Remote | Middle/Senior | Snowflake, Fivetran, dbt, Power BI, SQL, Python, R, AI-ассистированная разработка | текст обрезан при сборе | не удалось подтвердить | не указано | нет |
| 9 | [Data Analyst — Hired](https://remoteok.com/remote-jobs/remote-data-analyst-hired-1132989) | не указан | Worldwide | Remote | не указан | текст публикации крайне скудный, требования не раскрыты | — | "Competitive" | не указано | нет |
| 10 | [Home-Based Marketing Data Analyst — DCX](https://weworkremotely.com/remote-jobs/dcx-home-based-marketing-data-analyst) | BPO/Roofing marketing | Anywhere (факт. Азия/PH-смена) | Remote | Junior (1-3 года) | Google Analytics/Ads, Power BI, AccuLynx, Ahrefs, HubSpot | Tableau/Looker Studio | PHP 38 000–48 000/мес | обязателен | нет |
| 11 | [Data Analyst / Curam — AHU Technologies](https://weworkremotely.com/remote-jobs/ahu-technologies-data-analyst-curam) | Gov IT consulting | Remote (US госсектор) | Remote, контракт | Senior (11+ лет) | ETL 8 лет, Tableau 5 лет, Curam v6+ 3 года, MS Visio | Data governance/MDM | $73–81/час | подразумевается | нет |
| 12 | [Data Analyst (AI Translation Quality) — OnTheGoSystems](https://weworkremotely.com/remote-jobs/onthegosystems-data-analyst-ai-translation-quality) | AI/Localization | Anywhere | Remote | Middle+ | SQL/Python, самостоятельная постановка задач, метрики/сегментация/корреляция vs причинность, AI-инструменты | Локализация, BI | не указана | свободный + доп. язык | нет |

*Отбраковано: 8 закрытых (Blockchain.com, Aisle and Abroad, KPA, Softrams, Spreetail, Mission BI Analyst, RainFocus, Sporty), 1 устаревшая (>3 мес.), 12 не удалось прочитать (403/timeout — не включены, хотя могут быть действующими).*

### Indeed (remote, преимущественно US) — 16/20

Найдено и зафетчено 20 карточек, 19 открылись, из них 3 оказались
expired (исключены), 1 — 404 (исключена). Итог: 16 подтверждённых
действующих вакансий.

**Важное наблюдение источника:** заметная часть результатов на Indeed под
запрос "Data Analyst" — это staffing-агентства (Intone Networks, Qureos
Inc), публикующие почти идентичные шаблоны вакансий под разными
"заказчиками" — по сути один посредник с 4+ листингами, не 4-5 разных
работодателей. Гео-охват сместился в US: живых remote-EU вакансий на
Indeed под этот запрос почти не индексируется (единственная найденная,
Gamesight, оказалась expired).

| # | Вакансия / компания | Домен | Регион | Формат | Уровень | Обязательные требования | Желательные | Вилка | English | Тестовое |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | [Senior Healthcare Data Analyst — Sentara Workforce Solutions](https://www.indeed.com/viewjob?jk=b7408ff42d639efb) | Healthcare | US (29 штатов), remote | Remote | Senior | Epic-сертификация (Clarity/Caboodle/Cogito), 3+ года, Excel/SQL/Power BI/Databricks | Azure, ETL, population health | $80 204–133 682/год | не указано | нет |
| 2 | [Part-Time Survey and Data Insights Analyst — Syneos Health](https://www.indeed.com/viewjob?jk=ccf4621485df3664) | Biopharma | US, remote | Remote, контракт | Middle | Qualtrics продвинутый, QlikSense/Tableau/Power BI, MS Office продвинутый | Master's, HR/L&D опыт | $51.25/час | не указано | нет |
| 3 | [Clinical Data - Business Analyst — Intone Networks](https://www.indeed.com/viewjob?jk=438e55e8b7bc505d) | Pharma/Clinical | US, remote | Remote | Middle/Senior (7+ лет) | RDM/CDISC/Pinnacle 21, Agile, Jira/Confluence | Reference Data Management | не указана | не указано | нет |
| 4 | [Data Analyst/Engineer — Intone Networks](https://www.indeed.com/viewjob?jk=40bcfcb8e21dfb11) | InfoSec | US, remote | Remote, контракт | не указан | SQL (запросы/процедуры/вьюхи), SSIS/ETL | — | не указана | не указано | нет |
| 5 | [Senior Data Analyst / Data Modeler — Intone Networks](https://www.indeed.com/viewjob?jk=8d713ba2d1ffab4c) | Professional services | US, remote | Remote | Senior (7-10+ лет) | Data modeling 5-7 лет, Snowflake+SQL 3-5 лет, Python, Power BI | OLAP, консалтинг-фон | не указана | не указано | нет |
| 6 | [Senior Data Analyst — Intone Networks](https://www.indeed.com/viewjob?jk=efcd32ce547cf9ab) | HR/People Analytics | US, remote | Remote, контракт | Senior | SQL, Workday, BI-дашборды | Tableau, Python, AI-инструменты | не указана | подразумевается | нет |
| 7 | [Remote Data Analyst (Colaval) — Qureos Inc](https://www.indeed.com/viewjob?jk=e6ede5c970b536fb) | Manufacturing | US, remote | Remote | Middle | Data models, SQL+Power BI/Tableau, статистика (SPSS/SAS) | Industrial опыт | $45–55/час | не указано | нет |
| 8 | [Data Analyst WFH (Universal Logistics) — Qureos Inc](https://www.indeed.com/viewjob?jk=70f912709f4652b5) | Logistics | US, remote | Remote | Middle | SQL, reporting, data mining, статистика (SPSS/SAS) | Logistics опыт | $45–55/час | не указано | нет |
| 9 | [BI Analyst (FT/PT) — Qureos Inc](https://www.indeed.com/viewjob?jk=3cf518472ed685bc) | не указан | US, remote | Remote | Entry-Middle | Excel, SQL, Power BI/Tableau/Looker | degree в анал. дисциплинах | не указана | не указано | нет |
| 10 | [Remote Data Analyst (Ultimutt Dog Care) — Qureos Inc](https://www.indeed.com/viewjob?jk=d095de9c08b18e0c) | Pet care | US, remote | Remote | Middle (2+ года) | SQL+Excel, Power BI/Tableau/Looker | Python/R, CRM-аналитика | $77 000/год | не указано | нет |
| 11 | [Data Analyst (contract) — KPMG LLP](https://www.indeed.com/viewjob?jk=486f19df2588d9d9) | Consulting | US, remote | Remote, контракт | Middle | SQL, Python/R, Tableau/Power BI, статанализ | — | $42–52/час | не указано | нет |
| 12 | [Jr. Data Analyst — Planned Systems International](https://www.indeed.com/viewjob?jk=3932f8e1175e10de) | Gov contracting | US, remote | Remote | Junior (1-2 года) | SQL, SSIS, Power Automate, MS Office/SharePoint | Power BI (DAX/M), MBI-допуск | не указана | не указано | нет |
| 13 | [Junior Data Analyst — Radiance Technologies](https://www.indeed.com/viewjob?jk=5340a34846068119) | Defense | US, remote | Remote | Junior (2 года) | 2 года опыта, **действующий допуск Top Secret** | Python/SQL/R/Power BI, ML | не указана | не указано | нет |
| 14 | [Junior Data & Insights Specialist — Great Waters Federal](https://www.indeed.com/viewjob?jk=c54b2e06b2a234f9) | Defense/Intelligence | US, remote | Remote | Junior | 2 года IT-опыта, public trust допуск, Tableau | — | не указана | не указано | нет |
| 15 | [Data Analyst Junior/Mid — Careerswift](https://www.indeed.com/viewjob?jk=aba50ac1a2126540) | не указан | US, remote | Remote | Junior-Middle (1-3 года) | SQL, Excel, Power BI/Tableau | — | не указана | не указано | нет |
| 16 | [Data Analyst (non-profit healthcare) — Qureos Inc](https://www.indeed.com/viewjob?jk=d69948fc0c7ad6cd) | Non-profit/Public health | US, remote | Remote | Middle | SQL, Python/R, Tableau/Power BI | Non-profit опыт | $21–32/час | не указано | нет |

*Отбраковано: Data Ideology (expired), Imagine Worldwide (expired), Gamesight/EU (expired), 1 ссылка 404.*

### Доп. сбор: Wellfound / WeWorkRemotely / RemoteOK / careers-страницы — 21

Целевой добор по прямому запросу: приоритет источникам с более долгоживущими
ссылками (Otta, WeWorkRemotely, RemoteOK, карьерные страницы компаний,
Wellfound), плюс новое поле **"Открыто для Украины/B2B"** — проверено для
каждой вакансии отдельно (текст самой вакансии, не только метаданные
площадки).

**Otta — второй раз подряд полный тупик**: домен жёстко редиректит на
welcometothejungle.com, полезного списка вакансий получить не удалось (0
вакансий с этого источника, как и в первом заходе). Рабочим оказался
**Wellfound** (живой листинг сайта, не кэш поисковика — кэшированные
ссылки на Wellfound той же протухли за ~2 месяца, как и другие площадки):
13 из 21. WeWorkRemotely дал 2 новых (категории частично 404/дубли).
RemoteOK — 2 новых (прямой листинг категории по-прежнему блокируется
403/SPA-shell, точечные ссылки на конкретные вакансии проходят). Ashby/
Greenhouse напрямую — 4.

**Ключевой результат по фильтру Украина/B2B (n=21): только 3 из 21 (14%)
явно открыты для найма из Украины или через B2B/контрактора без
привязки к конкретной стране.** Из них одна ([Ruby Labs](https://jobs.ashbyhq.com/ruby-labs/02eda1b4-c84a-4ee8-8a3d-0fdcc93cf0a9))
— по-настоящему качественная позиция с Украиной, названной по имени в
списке разрешённых локаций, независимый контракторский договор (B2B),
и требованием свободного русского/украинского вдобавок к английскому.
Две другие (ProviderNow, At Your School) — микро-стартапы (1-10 и 11-50
человек) с расплывчатой формулировкой "hires remotely in Everywhere",
скорее всего от отсутствия локальной инфраструктуры найма, чем от
осознанной глобальной стратегии, и с невысокой вилкой. Показательный
контр-пример: вакансия Xebia (CEE) с явным акцентом на Восточную Европу
в названии компании и списком стран (Болгария/Молдова/Польша/Румыния) —
**не включает Украину** и требует "valid work permit to work in the EU".
У 3 из 21 вакансий обнаружено прямое противоречие между метаданными
площадки ("Hires remotely in Everywhere"/страна) и текстом самой
вакансии, который жёстче ограничивает регион — в таблице приоритет
отдан тексту вакансии, расхождение отмечено отдельно.

*Это поле не было ретроспективно проверено для 41 вакансии, собранной в
первом заходе (RemoteOK/WWR/LinkedIn/Otta/Indeed выше) — там в основном
US-вакансии без явного упоминания Украины ни в одну, ни в другую сторону,
поэтому по аналогии с найденной здесь пропорцией (14% открыто) можно
предполагать похожий или худший результат, но это не проверенная цифра
и не входит в статистику.*

| # | Вакансия / компания | Домен | Регион (заявлено) | Формат | Уровень | Обязательные требования | Желательные | Вилка | English | Тестовое | UA/B2B |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | [Data Analyst — YipitData](https://wellfound.com/jobs/4410799-data-analyst) | Market research/DaaS | "Everywhere" (метаданные) vs "within the United States" (текст) | Remote | Middle (3-5 лет) | SQL, 3-5+ лет analytics, автономность, AI-инструменты | Python/PySpark | $130k–180k | не указано | нет данных | Нет (явно, коллизия площадка/текст) |
| 2 | [Senior Data Analyst — YipitData](https://wellfound.com/jobs/4289645-senior-data-analyst) | Market research/DaaS | та же коллизия | Remote | Senior (6-8+ лет) | Экспертный SQL, Python/PySpark, лидерство в неопределённости | — | $165k–205k | не указано | нет данных | Нет (явно) |
| 3 | [Data Analyst — HackerEarth](https://wellfound.com/jobs/4505509-data-analyst) | Recruiting-tech SaaS | US, UK | Remote | Junior-Middle (1 год) | Python (Pandas/NumPy), SQL, GenAI-инструменты, визуализация | Tableau/Power BI | $50k–70k | не указано | challenge assessment обязателен | Нет (явно) |
| 4 | [Data Analyst — Chronicle](https://wellfound.com/jobs/4489516-data-analyst) | AdTech/AI | только US | Onsite/remote US | Junior (2 года) | Чёткое письмо, AI-инструменты (Claude/Codex) | медиа-опыт | $80k–120k+equity | не указано | нет данных | Нет (явно) |
| 5 | [Data Analyst — Pave](https://wellfound.com/jobs/2883170-data-analyst) | Fintech | Canada/North America/US | Remote | Middle (3 года) | SQL, Python/Pandas, дашборды | Snowflake/AWS/dbt | $100k–150k+equity | не указано | нет данных | Нет (явно) |
| 6 | [Staff Data Analyst — Assured](https://wellfound.com/jobs/4452970-staff-data-analyst) | Insurtech | только US | Remote | Staff/Senior | SQL, дизайн экспериментов, работа со стейкхолдерами | Python/R/Tableau/PowerBI/Looker | $175k–195k | не указано | нет данных | Нет (явно) |
| 7 | [Data Analyst — ProviderNow](https://wellfound.com/jobs/4491940-data-analyst) | Healthtech | Everywhere | Remote | Middle (2-4 года) | SQL, Python или R, Tableau/Power BI, HIPAA | — | $25k–35k | не указано | нет данных | **Да (явно)** |
| 8 | [Data Analyst — At Your School](https://wellfound.com/jobs/4204660-data-analyst) | EdTech | Everywhere | Remote/Onsite | Middle (2 года) | Excel, SQL, Tableau/Power BI, data cleaning | — | $70k–85k | не указано | нет данных | **Да (явно)** |
| 9 | [Senior Data Analyst, GTM — Tremendous](https://wellfound.com/jobs/4377712-senior-data-analyst-gtm) | Fintech | US only (метаданные и текст) | Remote | Senior | Экспертный SQL, BI (Sigma/Tableau/Mode), GTM-аналитика | dbt/Fivetran, Python/R | $175k–225k | не указано | нет данных | Нет (явно) |
| 10 | [Data Analyst — Recidiviz](https://wellfound.com/jobs/3922048-data-analyst) | Non-profit civic tech | только US | Remote | Middle (2+ года) | SQL сложный, Python/Pandas, коммуникация | GCP/BigQuery/Looker | $97k (фикс.) | не указано | нет данных | Нет (явно) |
| 11 | [Business Data Analyst — Noldor](https://wellfound.com/jobs/3813338-business-data-analyst) | Insurtech | только US | Remote | Senior (5+ лет) | Продвинутый Excel/Sheets, insurance-домен | mandatory reporting | $115k–130k | не указано | нет данных | Нет (явно) |
| 12 | [Data Analyst — NumeralHQ](https://wellfound.com/jobs/3494497-data-analyst) | Fintech (tax) | только US | Remote | Middle | SQL, Excel/Sheets, финансовая реконсиляция | DBT/ETL, Python | $55k–120k | не указано | нет данных | Нет (явно, US visa sponsorship ≠ remote/B2B) |
| 13 | [Data Analyst, Fraud Intelligence — Sardine](https://wellfound.com/jobs/4417415-data-analyst-fraud-intelligence) | Fintech/antifraud | только US/Canada | Remote | Middle (3-5 лет) | SQL, Python или R, precision/recall/AUC | fraud/identity signals, ML | $115k–145k | не указано | нет данных | Нет (явно, несмотря на слоган "#WorkFromAnywhere") |
| 14 | [Salesforce & Omnichannel Analytics Lead — Bavarian Nordic](https://weworkremotely.com/remote-jobs/bavarian-nordic-salesforce-omnichannel-data-analytics-lead-m-f-d) | Biotech/Pharma | только UK | Remote | Senior/Lead | Master's, CRM/omnichannel, Power BI, Python, Veeva/Salesforce | pharma-опыт, немецкий | не указана | Fluent (+German plus) | нет данных | Нет (явно) |
| 15 | [Data Analyst (Maps Evaluator) — Peroptyx](https://weworkremotely.com/remote-jobs/peroptyx-data-anlayst) | AI training data/crowdwork | Anywhere in the World | Remote, контракт | не указан | Research skills, внимание к деталям | — | $10k–25k | подразумевается | вероятен отбор, не описан | **Да (явно)**, но не классический DA — gig-оценка карт для AI |
| 16 | [Data Analyst (Excel) — YO AI Labs](https://remoteok.com/remote-jobs/remote-data-analyst-yo-ai-labs-1135558) | AI training data broker | US (SF) | Remote, контракт | не указан | Продвинутый Excel, data cleaning/validation | доп. BI | не указана | подразумевается | нет данных | Нет (явно) |
| 17 | [Senior Data Analyst — Ruby Labs](https://jobs.ashbyhq.com/ruby-labs/02eda1b4-c84a-4ee8-8a3d-0fdcc93cf0a9) | Consumer tech | Serbia/Cyprus/Czechia/EU/Georgia/Latvia/Montenegro/Poland/Spain/**Ukraine** | Remote, B2B-контракт | Senior (3+ года) | Продвинутый SQL, продуктовая аналитика (Mixpanel/GA4/Amplitude), A/B-тесты, BI | Marketing Analytics, Python/R, GCP/BigQuery | не указана | Fluent English AND Russian/Ukrainian | 90 мин tech + 60 мин final | **Да (явно)** — единственная во всей выборке с Украиной по имени |
| 18 | [Product Data Analyst — Wand](https://jobs.ashbyhq.com/wand/1bd20353-4c24-4f0a-8ebf-c496b1fc3801) | Gaming | US/Canada/Caribbean | Remote | Senior (5 лет) | SQL (window functions), Python/Pandas, A/B-тесты | Hex/dbt/BigQuery, causal inference | $145k–175k | не указано | нет данных | Нет (явно) |
| 19 | [Data Analyst — GoHenry](https://jobs.ashbyhq.com/GoHenry/09e04acc-a14d-41f7-b123-cbad1815fa81) | Fintech (kids) | Лондон, визиты обязательны | Гибрид/remote с визитами | Middle-Senior | SQL в DWH продвинутый, Tableau, dbt/Dataform | BigQuery, Amplitude | не указана | Fluent | нет данных | Нет (явно) |
| 20 | [Data Analyst — Xebia (CEE)](https://job-boards.greenhouse.io/xebiacee/jobs/6109340004) | IT-консалтинг | Bulgaria/Moldova/Poland/Romania | Remote (в пределах стран) | Middle | SQL, BI (QuickSight/Sigma/Looker/PowerBI) | Athena/Iceberg | не указана | мин. B2 | Client Interview | Нет (явно) — Украина не в списке, нужен work permit в ЕС |
| 21 | [Data Analyst — Marketing Architects](https://remoteok.com/remote-jobs/remote-data-analyst-marketing-architects-1130731) | Marketing/Ad agency | Remote US (кроме Калифорнии) | Remote | Middle (2-5 лет) | Excel продвинутый, BI/data tools (Domo/Databricks/SQL), GPA 3.5+ | — | $70k–90k | не указано | ~30-мин assessment (вероятно) | Нет (явно, максимально жёстко — список исключённых виз) |

*Отбраковано: 2 Wellfound (вводящие в заблуждение заголовки — не
классический DA), 5 кэшированных Wellfound-ссылок (410 Gone), WWR —
дубли и нерелевантные заголовки (Data Governance Manager), RemoteOK — 8
закрытых/404 (CUDOS, KPA, Nextbite, Yassir, Capco, dv01, Super), 1
Ashby-вакансия закрыта, 1 пустая страница careers.*

## Сегмент: Польша / Чехия / Германия / Нидерланды — 31/40

Цель была 40 (10+10+10+10). PL и CZ вышли на план (10+10). DE и NL — нет:
собрано 6 DE + 5 NL = 11 вместо 20. **Честно фиксирую нехватку, не
подгоняю**: агент открыл через WebFetch ~65 URL по DE/NL, из них только
11 оказались действующими — подавляющее большинство ссылок из поиска
(проиндексированных Google/Bing) на момент проверки истекли (~22 явно
помечены expired/closed) или были недоступны технически (403/404/JS-SPA:
Adyen, ABN AMRO, Rabobank, TomTom, ASML, ING, N26, Just Eat Takeaway,
LinkedIn-карточки, StepStone). Наблюдение само по себе показательно:
средний срок жизни объявления на этих площадках — 4-8 недель, поиск
находит гораздо больше "фантомных" вакансий, чем реально открытых.

### Польша (10/10)

| # | Вакансия / компания | Домен | Город | Формат | Уровень | Обязательные требования | Желательные | Вилка | English | Тестовое |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | [Data Analyst — Egnyte](https://justjoin.it/job-offer/egnyte-poland-data-analyst-poznan-data) | Cloud/SaaS | Poznań | Гибрид (3/2) | Middle | SQL продвинутый, Tableau 3+ года, BigQuery 3+ года, SaaS-метрики | Python/R базовый, Salesforce, dbt | не указана | не указан явно | нет |
| 2 | [Data Analyst (Process Mining/BI) — Capgemini](https://justjoin.it/job-offer/capgemini-data-analyst-process-mining-bi--opole-data) | Consulting | Opole (+7 городов) | Гибрид | Senior | 5+ лет, Celonis, Power BI, SQL, SAP/Oracle | P2P/C2C/R2R процессы | не указана | очень хороший | нет |
| 3 | [Data Analyst — Payarto](https://pl.indeed.com/viewjob?jk=bcf4d94ff798a639) | Fintech | Warszawa | Гибрид | Junior/Middle (1-5 лет) | Python или R, SQL средний-продвинутый, статистика, PostgreSQL | Git, regex, LLM | не указана | очень хороший | нет |
| 4 | [Data Analyst — LexisNexis Risk Solutions](https://pl.indeed.com/viewjob?jk=db3068dce27fafa0) | Fraud/Risk | Warszawa | не указан | Middle | Python, SQL, executive-отчётность | Superset/Tableau/PowerBI, языки EMEA | 130 900–218 200 PLN/год | multilingual — плюс | нет |
| 5 | [Data Analyst — Rockwell Automation](https://pl.indeed.com/viewjob?jk=f4b90375ebb7add1) | Industrial automation | Katowice | Гибрид | Middle (3+ года) | Azure 3+ года, Power BI 3+ года, SQL, PowerApps | PL-300, Databricks, Python | не указана | не указан | нет |
| 6 | [Data Analyst — InPost](https://pl.indeed.com/viewjob?jk=3d067deb460f2231) | Logistics/e-commerce | Warszawa | Remote | Middle (2+ года) | PySpark/SQL/Python, Databricks, Azure/AWS/GCP | Power BI/Tableau | не указана | B1 | нет |
| 7 | [Data Analyst — OEConnection](https://pl.indeed.com/viewjob?jk=a6f9a2e97525310e) | Automotive SaaS | Kraków | Onsite | Junior | Свободный английский, аналитическое мышление, MS Office | Автопром | не указана | свободное владение | нет |
| 8 | [Data Analyst — Helprise](https://pl.indeed.com/viewjob?jk=663f1f22096132d8) | BPO/Compliance | Warszawa | Remote/гибрид | не указан | SQL сильный, облачные данные, Excel продвинутый | BI-инструменты, compliance | не указана | не указан явно | нет |
| 9 | [Data Analyst — Addepar](https://pl.indeed.com/viewjob?jk=b91523bfc6119d9c) | Fintech (wealth mgmt) | Warszawa | не указан | Middle | Финансовые данные, SQL, Jupyter | Инвестиционный домен | 160 000–192 000 PLN (база) | не указан явно | нет |
| 10 | [Data Analyst — Artifex Mundi](https://pl.indeed.com/viewjob?jk=e19966104d5fe9ca) | Gaming (F2P) | Katowice | Гибкий | Middle (2+ года) | Tableau/Firebase/BigQuery | AI-инструменты, F2P-домен | не указана | не указан | нет |

*Отбраковано: 6 expired вакансий на justjoin.it, 1 стажировка с началом в 2027, nofluffjobs.com/pracuj.pl — не открылись (403).*

### Чехия (10/10)

| # | Вакансия / компания | Домен | Город | Формат | Уровень | Обязательные требования | Желательные | Вилка | English | Тестовое |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | [Data Analyst — AXA Partners](https://cz.indeed.com/viewjob?jk=7f440cb0db086f78) | Insurance | Ostrava | Гибрид | Junior | Базовый SQL и BI, продвинутый Excel | Data governance, статистика | не указана | B2 | нет |
| 2 | [Data Analyst — Pluxee](https://cz.indeed.com/viewjob?jk=bd54f277c6a324d5) | Employee benefits | Praha | Onsite | Middle (2+ года) | Магистратура, Power BI, R/Python статмоделирование | Регрессии, сезонная корректировка | не указана | не указан явно | нет |
| 3 | [Data Analyst (стажировка/junior) — Fitify](https://cz.indeed.com/viewjob?jk=b5d34c6e629f20b4) | Fitness-стартап | Praha | Гибрид (до 50%) | Junior/Intern | SQL, аналитическое мышление, Data Studio | R/Python, ML | не указана | не указан явно | нет |
| 4 | [Data Analyst — Traffic Label](https://cz.indeed.com/viewjob?jk=f99942e4fae2381d) | iGaming/tech | Praha | Onsite | Middle (2+ года) | SQL продвинутый (Postgres/Redshift), Python, AWS, ELT | iGaming/crypto опыт, чешский | €50 000–55 000/год | отличный | нет |
| 5 | [Data Analyst — VAFO](https://cz.indeed.com/viewjob?jk=a402517bc7895000) | E-commerce/pet | Chrášťany | Onsite | Middle/Senior (3+ года) | SQL продвинутый (Snowflake), GA4, Looker Studio/Power BI | Python/dbt | не указана | B2 | нет |
| 6 | [Data Analyst (WFM) — International SOS](https://cz.indeed.com/viewjob?jk=c1d84f0fb7b01554) | Medical/Insurance | Praha | не указан | Middle (2-5 лет) | Workforce planning, Power BI, SQL, NICE CXone | Предиктивная аналитика | не указана | свободное владение | нет |
| 7 | [Data Analyst — OnTheGoSystems](https://cz.indeed.com/viewjob?jk=c3f21b97edf37e2d) | Localization | Praha (remote) | Remote | не указан | SQL/Python, работа с БД/логами/API, AI-инструменты | Локализация/QA опыт | не указана | свободный + ещё язык | нет |
| 8 | [Data Analyst (part-time) — Billigence](https://cz.indeed.com/viewjob?jk=cdcc11e0bf09537c) | Data-консалтинг | Praha | Гибрид, 20ч/нед | Entry (студенты) | SQL, Tableau, внимание к деталям | Snowflake, Power BI/Sigma | не указана | чешский + английский оба обязательны | нет |
| 9 | [Business Analyst II — Thermo Fisher Scientific](https://cz.indeed.com/viewjob?jk=7efbfa8b2df72ba9) | Biotech | Brno | Onsite | Middle | Магистратура+1 год, Agile, Excel/Power BI/SQL, Jira | ERP | не указана | не указан явно | нет |
| 10 | [Data Analyst — MultiSport Benefit](https://www.jobs.cz/rpd/2001071556/) | Employee benefits | Praha | Onsite | Middle | SQL, Power BI, Excel продвинутый | Python | не указана | чешский обязателен | нет |

*Отбраковано: 2 истёкшие на LinkedIn, 1 снята с Built In, 2× 404, 1× 403, 3 источника не отдали содержимое (JS-рендер/general board).*

### Германия (6/10)

| # | Вакансия / компания | Домен | Город | Формат | Уровень | Обязательные требования | Желательные | Вилка | English | Тестовое |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | [Data Analyst — Veeva Systems](https://de.indeed.com/viewjob?jk=cea3f03c0216312d) | Health-tech/SaaS | Германия, remote | Remote | Mid-Senior (5+ лет) | SQL+Python, облако (AWS/GCP/Azure), процессная документация | Life sciences, ETL, Airflow, GDPR/HIPAA | €50 000–85 000/год | не указано | сторонний personality assessment (3 дня) |
| 2 | [Mid Data Analyst (Finance) — SumUp](https://www.sumup.com/careers/positions/berlin-germany/data-analytics/mid-data-analyst-finance/8448674002/) | Fintech | Berlin | Onsite | Middle (4+ года) | SQL, поддержка FP&A, Tableau, стейкхолдер-менеджмент | — | не указана | не указано | нет |
| 3 | [Data Analyst — DRIVE Consulting GmbH](https://drive-consulting.jobs.personio.de/job/2578230) | IT-консалтинг (Automotive) | Aachen/Munich/Berlin | Onsite у клиента | Junior-Middle (1-3 года) | Python, пайплайны/дашборды, BI (QuickSight/Grafana/Tableau) | Автопром/индустрия | не указана | немецкий+английский | нет |
| 4 | [Senior Data Analyst — Kayzen](https://jobs.smartrecruiters.com/Kayzen1/743999684903028-senior-data-analyst-berlin-germany) | AdTech | Berlin | Onsite | Senior | Data modeling, SQL+Python/R, big data (Hadoop/Hive/Pig) | Ad-tech опыт | не указана | не указано | нет |
| 5 | [Data Analyst — OXG Glasfaser GmbH](https://de.indeed.com/viewjob?jk=45bbc184100828da) | Телеком/оптоволокно | Düsseldorf | Гибрид/remote (DE+25д EU) | Entry-Middle | ИТ-образование, Shell/Python/TypeScript, CI/CD, Azure/SSO база | Swagger/OpenAPI | бенефиты вместо ЗП | немецкий+английский | нет |
| 6 | [Senior Marketing Scientist — Taxfix*](https://de.indeed.com/viewjob?jk=0cf4d11b84bdd181) | Fintech (tax) | Berlin | Гибрид | Senior (3+ года) | Marketing science, attribution/MMM, SQL+Python+dbt, CAC/CLV | — | не указана | не указано | нет |

*\#6 — реальный заголовок "Senior Marketing Scientist", не "Data Analyst"; включена как погранично-релевантная marketing-analytics роль.*

### Нидерланды (5/10)

| # | Вакансия / компания | Домен | Город | Формат | Уровень | Обязательные требования | Желательные | Вилка | English | Тестовое |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | [Data Analist Delivery Operations — bol.com](https://careers.bol.com/nl/vacatures/data-analist-delivery-operations/8551480002/) | E-commerce | Utrecht | не указан | Middle-Senior (5-10 лет) | SQL/BigQuery, работа с несовершенными данными | Tableau/LookerStudio, AI-акселератор | €4 500–5 500/мес | нидерландский (+англ. версия) | нет |
| 2 | [Analytics — Commercial Projects — Picnic](https://jobs.picnic.app/en/vacancies/JBL6X0KG/analytics/commercial-and-analytics-projects-mid-level/amsterdam/north-holland/netherlands) | E-grocery | Amsterdam | не указан | Middle (2-5 лет) | Магистратура (эконометрика/математика/физика), consulting/PE/IB опыт, SQL+Python | — | не указана | нидерландский+английский | online test + assessment day |
| 3 | [Analytics — Logistics Projects — Picnic](https://jobs.picnic.app/en/vacancies/JPQRD9DL/analytics/logistics-and-analytics-projects-mid-level/amsterdam/north-holland/netherlands) | E-grocery | Amsterdam | не указан | Middle (2-5 лет) | Магистратура, SQL+Python, consulting/PE/IB опыт | — | не указана | нидерландский+английский | online test + assessment day |
| 4 | [Analytics — Tech Projects — Picnic](https://jobs.picnic.app/en/vacancies/JGYG909Q/analytics/tech-and-analytics-projects-mid-level/amsterdam/north-holland/netherlands) | E-grocery | Amsterdam | не указан | Middle (2-5 лет) | Магистратура, SQL+Python, consulting/PE/IB опыт | — | не указана | только английский | online test + assessment day |
| 5 | [Business Analyst — Keylane*](https://nl.indeed.com/viewjob?jk=e536d15a011ca282) | InsurTech/SaaS | Utrecht | Гибрид | Medior/Senior | Анализ сложных проблем, коммуникация, база software dev | Нидерландский, insurance domain, data modeling | €46 656–75 168/год | свободный (обязательно) | VOG справка + reference check |

*\#5 — реальный заголовок "Business Analyst", не "Data Analyst"; включена как погранично-релевантная (data modeling указан как plus).*

*Отбраковано (DE+NL): ~22 явно истёкших/закрытых (360 Treasury, Atlas Copco/Edwards Jena, Phoenix Medical, Smoobu, Flink, ABOUT YOU, Omio, Delivery Hero×5, BDO Utrecht, Canyon Bicycles, Coolblue Junior Data Analist, DGUV, Mahr EDV, Cognizant Netcentric, ib vogt, Philips×3), плюс ~30 недоступны технически (403/404/JS-SPA: Adyen×4, ABN AMRO×4, Rabobank×4, TomTom, ASML, ING×2, N26, Just Eat Takeaway×3, StepStone, LinkedIn).*

---

## Сводка по выборке

**Итого собрано и подтверждено: 123 вакансии** (план — 130 базовых карточек
без учёта Middle-среза; недобор по DE/NL честно зафиксирован).

| Сегмент | План | Факт | % выполнения |
|---|---|---|---|
| Remote EU/US/global (RemoteOK/WWR + LinkedIn/Otta/ATS + Indeed + доп. сбор Wellfound/careers) | 60 | 62 | 103% |
| Польша | 10 | 10 | 100% |
| Чехия | 10 | 10 | 100% |
| Германия | 10 | 6 | 60% |
| Нидерланды | 10 | 5 | 50% |
| Украина (Djinni/DOU/Work.ua) | 30 | 30 | 100% |
| **Итого** | **130*** | **123** | **95%** |

\* В задании указано «минимум 150». Remote-сегмент план перевыполнил
после доп. сбора (см. подраздел выше). Недобор по DE/NL остаётся
системным: на всех проверенных площадках подавляющее большинство ссылок,
которые находит поиск, на момент fetch-проверки уже истекли
(LinkedIn/Otta/Wellfound/BuiltIn — вакансия закрыта или сайт блокирует
бот-доступ; RemoteOK/WeWorkRemotely — 403 на прямой WebFetch у части
ссылок; DE/NL job-борды — средний срок жизни объявления 4-8 недель). Это
не подгонка под план, а фактическое ограничение метода "поиск + fetch без
логина" на актуальность индекса. Раздел анализа ниже опирается на все 123
реально подтверждённые вакансии.

### Открыто для найма из Украины / B2B

Проверено явно для 21 вакансии доп. сбора (не проверялось ретроспективно
для первых 41 remote-вакансии — там нет систематической разметки этого
поля, см. оговорку в подразделе выше). **Из 21: только 3 (14%) явно
открыты для Украины или найма через B2B/контракт без привязки к
конкретной стране.** Из 18 закрытых — почти все ограничены явным списком
стран (обычно US, реже US+Canada, UK, или конкретные страны ЕС без
Украины) прямо в тексте вакансии, а не только в фильтрах площадки. Это
ключевой практический вывод для программы: формальное слово "remote" в
заголовке вакансии в 86% случаев в этой подвыборке НЕ означает "можно
работать из Украины" — нужно читать текст вакансии целиком, искать
формулировки вида "hires globally"/"contractor"/явный список стран, и
явно закладывать это в модуль про поиск работы (Фаза 3).

### Срез по уровню (из фактических карточек)

Считается по буквальному значению колонки "Уровень" в таблицах выше; для
смешанных меток ("Junior-Middle", "Middle-Senior") — по первому названному
уровню.

| Уровень | N | % |
|---|---|---|
| Junior / Junior-Middle | 24 | 19.5% |
| Middle | 62 | 50.4% |
| Senior / Lead / Head / Principal / Staff | 29 | 23.6% |
| Не указан | 8 | 6.5% |

---

## Анализ

Все проценты ниже — от 123 подтверждённых вакансий (см. таблицы выше;
пересчитано после доп. сбора remote-сегмента). Подсчёт вёлся построчно
по колонкам "Обязательные требования" и "Желательные" каждой карточки.

### 1. Частотность инструментов и навыков

| Инструмент/навык | N | % от 123 |
|---|---|---|
| SQL (любой диалект) | 93 | 75.6% |
| — из них диалект назван явно (MS SQL, PostgreSQL, Redshift-SQL, Snowflake-SQL) | 6 | 4.9% |
| Python | 64 | 52.0% |
| Power BI | 47 | 38.2% |
| Tableau | 40 | 32.5% |
| Excel / Google Sheets | 31 | 25.2% |
| Cloud/DWH (AWS/GCP/Azure/Snowflake/BigQuery/Redshift/Databricks/ClickHouse) | 29 | 23.6% |
| — из них BigQuery отдельно (вкл. алиас GBQ) | 11 | 8.9% |
| — из них Snowflake отдельно | 9 | 7.3% |
| R | 23 | 18.7% |
| Looker / Looker Studio | 19 | 15.4% |
| dbt | 13 | 10.6% |
| A/B-тестирование / эксперименты | 10 | 8.1% |
| Статистика (регрессия, hypothesis testing, causal inference — строго, без общих слов) | 7 | 5.7% |
| Airflow / Kafka / ETL-оркестрация (явно названы) | 2 | 1.6% |
| Git (явное слово, вкл. GitHub/GitLab) | 1 | 0.8% |

Профиль 21 вакансии доп. сбора (Wellfound/WWR/RemoteOK/careers) заметно
смещён к Python (61.9% против 50.0% в остальной выборке) и Cloud/DWH
(28.6% против 22.5%), но заметно ниже по Power BI (28.6% против 40.2%) —
эти вакансии почти исключительно из US-стартапов/tech-компаний со
стеком SQL+Python+dbt/Snowflake, тогда как остальная выборка (Польша,
госсектор США, Украина) заметно более Power BI-центрична.

### 2. Требования вне инструментов

| Категория | N | % от 123 |
|---|---|---|
| Отраслевой домен как явное требование (fintech, gambling, healthcare, insurance, automotive и т.п.) | 30 | 24.4% |
| Работа со стейкхолдерами / бизнес-коммуникация (явно) | 5 | 4.1% |
| Продуктовые метрики (CAC/LTV/ROI/retention/churn/funnel) | 5 | 4.1% |
| Сторителлинг / презентация данных нетехнической аудитории (явно) | 2 | 1.6% |

Цифры по стейкхолдерам и сторителлингу занижены форматом таблицы: она
хранит сжатый список требований, а не полный текст вакансии, и soft
skills в сжатых списках систематически недопредставлены — при чтении
полных текстов (см. ссылки) формулировки вида "translate complex data
into actionable business recommendations" встречаются заметно чаще, чем
показывает механический подсчёт по колонке.

Отдельное качественное наблюдение (без точного % по всей выборке —
целевой подсчёт по этой метке не проводился): явные упоминания
использования AI-инструментов (ChatGPT/Claude/Gemini) как рабочего
инструмента аналитика встречаются в вакансиях разного уровня и
регионов — например [Upgrade,
Inc.](https://remoteok.com/remote-jobs/remote-junior-business-amp-data-analyst-upgrade-inc-1133488),
[BetterMe](https://jobs.dou.ua/companies/betterme/vacancies/331277/),
[NerdySoft](https://jobs.dou.ua/companies/nerdysoft/vacancies/359877/),
[Rockwell Automation](https://pl.indeed.com/viewjob?jk=f4b90375ebb7add1),
[Chronicle](https://wellfound.com/jobs/4489516-data-analyst). Заметный
тренд 2026 года, но без отдельного подсчёта по всей выборке нельзя дать
честную цифру — фиксируется как наблюдение, не как статистика.

### 3. Граница Junior → Middle

Сравнение по буквальной метке уровня (Junior/Junior-Middle, n=24 против
Middle+Senior, n=91; вне сравнения — "не указан", n=8):

| Требование | Junior | Middle+ | Разница |
|---|---|---|---|
| Python | 33.3% | 60.4% | +27.1 п.п. |
| SQL | 62.5% | 82.4% | +19.9 п.п. |
| dbt | 0% | 14.3% | +14.3 п.п. |
| Cloud/DWH | 16.7% | 27.5% | +10.8 п.п. |
| R | 16.7% | 20.9% | +4.2 п.п. |
| Статистика (строго) | 4.2% | 6.6% | +2.4 п.п. |

**4 требования, которые реально отделяют middle от junior**: (1) Python
как рабочий инструмент, а не "будет плюсом"; (2) SQL на уровне сложных
запросов (не просто SELECT/JOIN, а window functions, CTE, оптимизация);
(3) любой облачный DWH (Snowflake/BigQuery/Redshift) — у junior почти не
встречается; (4) dbt — единственный инструмент с буквально 0% у junior
во всей выборке, полностью middle+-навык.

Контр-пример, который стоит знать: Tableau встречается у Junior (50.0%)
чаще, чем у Middle+ (30.8%) — это не значит, что Tableau "легче" Power
BI (различие по Power BI между группами почти нулевое — 41.7% vs 40.7%),
а отражает то, что в выборке много junior-вакансий из
американского/госсекторного сегмента (Indeed), где Tableau —
исторически стандартный входной BI-инструмент.

### 4. Английский

| Уровень | N | % от 123 |
|---|---|---|
| Не указано вовсе | 76 | 61.8% |
| Требуется, CEFR не назван ("обязателен", "подразумевается") | 16 | 13.0% |
| "Свободный"/fluent/"strong" (без CEFR) | 13 | 10.6% |
| B2 (вкл. "B2+" и "мин. B2") | 9 | 7.3% |
| Не требуется | 4 | 3.3% |
| B1 | 4 | 3.3% |
| A2 | 1 | 0.8% |
| C1 | 0 | 0% |

62% вакансий вообще не упоминают требование к английскому — это не
значит, что оно не нужно (для remote/US-вакансий английский — умолчание
рынка), просто формально не прописано. Среди вакансий, где уровень
указан явно с CEFR (n=14), медианный уровень — B2. Для Украины и
Польши/Чехии, где английский называется отдельно от местного языка,
чаще всего требуется B1–B2, реже — "свободный" уровень на позициях с
международными стейкхолдерами (US/UK клиенты, C-level коммуникация).

### 5. Вилки зарплат

58.5% вакансий (72 из 123) не публикуют вилку вовсе. Там, где вилка
есть (51 из 123, 41.5%):

| Регион | Диапазон | Медиана | N |
|---|---|---|---|
| Украина (USD/мес, включая оценки Djinni "по похожим") | $1300–3700 | ~$2750 | 7 |
| Remote/US, годовой оклад | $10 000–225 000 | ~$123 000 | 29 |
| Remote/US, почасовая ставка (контракт) | $21–81/час | ~$50/час | 6 |
| Польша (PLN/год) | 130 900–218 200 | недостаточно данных (n=2) | 2 |
| Чехия (EUR/год) | €50 000–55 000 | недостаточно данных (n=1) | 1 |
| Германия (EUR/год) | €50 000–85 000 | недостаточно данных (n=1) | 1 |
| Нидерланды | €46 656–75 168/год; €4500–5500/мес (разные единицы) | недостаточно данных (n=2) | 2 |

Важная оговорка по Украине: из 7 значений только 2 (Starlight Media,
"Є гроші") — вилка, заявленная самим работодателем; остальные 5 — это
оценка Djinni "средняя вилка похожих вакансий", не цифра из конкретного
объявления. Нижняя граница Remote/US-диапазона ($10k/год) —
[Peroptyx](https://weworkremotely.com/remote-jobs/peroptyx-data-anlayst),
gig-оценка карт для AI, нетипичный кейс не для классической роли DA; без
неё диапазон $25 000–225 000, медиана почти не меняется.

### 6. Тестовые задания

10 из 123 вакансий (8.1%) явно упоминают тестовое задание/assessment до
оффера: [Meduzzen](https://djinni.co/jobs/831210-data-analyst-sql-python-operations-focus/)
(logic + Python assessment), [Veeva Systems](https://de.indeed.com/viewjob?jk=cea3f03c0216312d)
(сторонний personality assessment, 3 дня), три вакансии
[Picnic](https://jobs.picnic.app/en/vacancies/JBL6X0KG/analytics/commercial-and-analytics-projects-mid-level/amsterdam/north-holland/netherlands)
(online test + assessment day), [Halo Lab](https://djinni.co/jobs/830326-web-and-digital-data-analyst/)
и [boringseo.team](https://djinni.co/jobs/818597-marketing-data-analyst/)
("есть", детали не раскрыты), [HackerEarth](https://wellfound.com/jobs/4505509-data-analyst)
(challenge assessment обязателен), [Ruby Labs](https://jobs.ashbyhq.com/ruby-labs/02eda1b4-c84a-4ee8-8a3d-0fdcc93cf0a9)
(90 мин технический + 60 мин финальный), [Marketing Architects](https://remoteok.com/remote-jobs/remote-data-analyst-marketing-architects-1130731)
(~30-мин assessment, вероятно). Тестовые задания — скорее исключение,
чем норма: почти 92% вакансий явно про них не упоминают.

---

## Топ-15 навыков

| # | Навык | % вакансий | Где чаще (Junior/Middle) | Часов на освоение с нуля* |
|---|---|---|---|---|
| 1 | SQL (join, агрегации, window functions) | 75.6% | оба, но сложность растёт к middle | 60–80 |
| 2 | Python (pandas/numpy для аналитики) | 52.0% | заметно чаще middle (60% vs 33%) | 80–120 |
| 3 | Power BI (включая DAX/Power Query) | 38.2% | оба, почти нет разницы (42% vs 41%) | 40–60 |
| 4 | Tableau | 32.5% | чаще junior (50% vs 31%) | 40–60 |
| 5 | Excel / Google Sheets (продвинутый: формулы, сводные, Power Query) | 25.2% | оба, базовый порог входа | 30–40 |
| 6 | Отраслевой домен (fintech/gambling/healthcare/insurance/etc.) | 24.4% | оба | не измеряется в часах — нарабатывается на проектах |
| 7 | Cloud/DWH (Snowflake/BigQuery/Redshift/Databricks) | 23.6% | заметно чаще middle (28% vs 17%) | 20–30 (поверх SQL) |
| 8 | R | 18.7% | немного чаще middle (21% vs 17%) | 40–60 |
| 9 | Looker / Looker Studio | 15.4% | оба | 15–20 |
| 10 | dbt | 10.6% | только middle+ (0% у junior) | 15–25 |
| 11 | A/B-тестирование / дизайн экспериментов | 8.1% | почти всегда middle+ | 20–30 (поверх статистики) |
| 12 | Статистика (регрессия, hypothesis testing, causal inference) | 5.7% | чаще middle+ (7% vs 4%) | 60–80 |
| 13 | Работа со стейкхолдерами / бизнес-коммуникация | 4.1%** | чаще middle+ | не измеряется в часах |
| 14 | Продуктовые метрики (CAC/LTV/ROI/retention/churn) | 4.1% | чаще middle+ | 15–20 |
| 15 | Git (версионирование SQL/скриптов) | 0.8%*** | почти не формализуется в вакансиях DA | 8–10 |

\* Оценки часов — не из вакансий (там их никто не пишет), а разумный
ориентир для самостоятельного освоения с нуля при 10–25 ч/нед; будут
уточняться на Фазе 1 при проектировании модулей.
\*\* Заниженная цифра из-за формата таблицы — см. пункт 2 анализа выше,
на практике soft skills встречаются в текстах вакансий заметно чаще.
\*\*\* Git остаётся в топ-15 несмотря на почти нулевую формальную частоту —
см. раздел "Мифы" ниже, категория (б): это не входной барьер по
вакансиям, но подтверждённая ежедневная практика.

## Мифы

Правка по итогам отдельного ресёрча (не по вакансиям, а по тому, что
реально делают практикующие аналитики — Reddit-треды, карьерные блоги,
инженерные посты компаний, полные тексты уже собранных вакансий).
Низкочастотные по вакансиям пункты разделены на две категории:
**(а) редко упоминают, потому что реально не нужно джуну** — можно
смело не включать в базовую программу; и **(б) редко упоминают, потому
что подразумевается по умолчанию** — навык остаётся в программе,
несмотря на низкий % в требованиях вакансий, потому что реальная
ежедневная практика его требует.

### (а) Действительно не нужно на входном уровне

- **A/B-тестирование как отдельный обязательный модуль** — 8.1%
  вакансий явно его требуют, и почти исключительно middle+/senior роли
  (product/marketing analyst). Дизайн экспериментов и статзначимость —
  оправданы как модуль на middle-уровне, не как входной барьер курса.
- **dbt** — 10.6%, буквально 0% у junior (см. п.3 анализа). Курсы
  2025-2026 часто добавляют dbt как "модный" навык, но по факту он
  нишевый даже среди опытных позиций — оправдан как продвинутый
  модуль/факультатив, не базовое ядро.
- **Airflow / оркестрация ETL** — 1.6%. Это территория Data/Analytics
  Engineer, а не Data Analyst; в DA-вакансиях встречается как редкое
  "nice to have". Не нужен в программе для трудоустройства на позицию
  Data Analyst.
- **Углублённая статистика (формальная регрессия, causal inference)** —
  5.7% строго посчитанных случаев. Описательная статистика (среднее,
  медиана, дисперсия, базовые распределения) нужна почти всем, но
  формальный статистический аппарат — оправдан не раньше middle-уровня.

### (б) Подразумевается по умолчанию — остаётся в программе

- **Git** (0.8% явных упоминаний в вакансиях, но подтверждено ежедневной
  практикой). Источники: reddit-тред "2026 Tech Stack at your Job"
  (r/datascience) — практикующие аналитики и дата-сайентисты сами
  перечисляют git/GitHub/GitLab в стеке почти в каждом ответе, но не как
  "требование", а как фоновый факт наравне с почтой; личный блог
  аналитика (kellyjadams.com, "A Day in the Life of a Data Analyst") —
  прямая цитата "I use this for version control (SQL queries) at my
  work"; разбор dataexpert.io про Git-воркфлоу для дата-команд отдельно
  выделяет облегчённый GitHub Flow как стандарт именно для
  analytics/BI/dbt-задач (в противовес полному Gitflow для инженерных
  пайплайнов). Вывод: в вакансиях не пишут, потому что не считают нужным
  формализовать очевидное — программе нужен лёгкий модуль по
  версионированию (ветка + PR, не полноценный Gitflow).
- **Excel** — формально не низкочастотен (25.2%, уже входит в топ-15), но
  стоит явно зафиксировать разрыв между "только в четверти вакансий" и
  реальной практикой: reddit-тред r/dataanalysis "Anyone else ever see a
  dataset so jumbled you just need to bust out Ol' Reliable?" (886
  апвоутов) — десятки практикующих аналитиков, включая тех, кто владеет
  SQL/Python/R, прямо пишут "Excel is the greatest weapon mankind has
  ever invented", "everyone resorts back to excel"; отдельно человек,
  нанимающий джунов, отмечает как проблему отсутствие "Excel muscle" у
  новых сотрудников. Independent-подтверждение: интервью с data
  engineers на motherduck.com фиксирует запрос "can I export this to
  Excel" как неизбежную часть работы с бизнес-стейкхолдерами. Вывод: не
  снижать долю Excel в программе просто потому, что вакансии просят
  Power BI/Tableau чаще — по факту Excel не заменяется, а используется
  параллельно как fallback-инструмент каждый день.
- **Английский** — 62% вакансий вообще не упоминают требование (см.
  п.4 анализа), но источник kajodata.com (блог практикующего в найме в
  data-индустрии) прямо описывает механизм: формальный "B2 в вакансии" —
  часто "hollow corporate buzzword", а реальная планка ниже и практичнее
  — "can you communicate your thoughts, and can you listen with
  comprehension" в интернациональной команде. Отсутствие явного
  требования в вакансии не означает, что английский не нужен — остаётся
  в программе как практический навык коммуникации (читать
  документацию, писать краткие выводы, участвовать в созвонах), а не
  как формальная подготовка к CEFR-экзамену.
- **Работа в терминале / командной строке** — в вакансиях практически
  не встречается отдельным требованием (не выделялась как отдельная
  категория при подсчёте — растворена в единичных "bash scripting" из
  Cloud/DWH и Airflow категорий, обе <2%). Но тот же reddit-тред "Ol'
  Reliable" содержит прямое подтверждение от практикующего аналитика:
  "if a csv is borked, and needs manual cleaning, I use vim"; в
  "Tech Stack at your Job" несколько дата-специалистов явно указывают
  "some bash scripting" в рабочем стеке. Отдельная оговорка: большая
  часть материалов "terminal isn't scary" в интернете написана для
  data scientists/engineers, не аналитиков напрямую — сам факт
  существования этого жанра контента означает, что терминал — реальный
  барьер входа для новичков, который тем не менее приходится преодолевать
  на практике, а не то, что он не нужен. Вывод: базовая грамотность в
  терминале (cd/ls, запустить скрипт, минимальный vim/nano) — оправдана
  как короткий онбординг-модуль, не полноценный курс.

Источники по всем пунктам категории (б) собраны через отдельный
целевой ресёрч (Reddit через архивные снапшоты — прямой доступ к
reddit.com заблокирован для автоматического сбора — плюс карьерные
блоги); это не вакансийная статистика и не должно смешиваться с
процентами из разделов 1-6 выше.

## Слепые зоны

Ни один навык за пределами уже стандартного курсового ядра (SQL, Python,
Power BI, Tableau — все четыре и так входят в большинство программ) не
перешёл порог 30% в нашей выборке даже после доп. сбора. Это само по
себе результат: заявленный в задаче формат "рынок массово требует X, а
курсы об этом молчат" здесь не подтверждается на уровне конкретных
инструментов. Но есть паттерны, которые близки к порогу или системно
недооценены в курсах несмотря на частоту:

- **Отраслевой контекст/домен (24.4%, почти четверть вакансий)** — курсы
  почти никогда не учат работать в контексте конкретного домена
  (unit-экономика fintech, воронка iGaming, метрики healthcare), это
  ожидается как способность освоить "по ходу", но работодатели проверяют
  это на собеседовании чаще, чем формализуют в тексте.
- **Работа с "грязными"/неполными данными в проде** — качественное
  наблюдение по текстам вакансий (не формализованная категория с
  процентом): формулировки вроде "work with imperfect data" (bol.com),
  "validate business hypotheses" (Meduzzen), "investigate anomalies"
  (Starlight Media) встречаются заметно чаще, чем тема "очистка грязных
  данных" в типичной программе курса, где обычно работают с уже
  подготовленными датасетами.
- **Автономность / самостоятельная постановка задач** — повторяющаяся
  формулировка в вакансиях middle+ ("не просто отвечать на запросы, а
  самостоятельно находить, что анализировать" — OnTheGoSystems,
  boringseo.team, Meduzzen). Это не инструмент, а рабочая привычка,
  почти никогда не тренируется в учебных проектах с заранее заданным
  условием задачи.
- **"Remote" ≠ "открыто для Украины"** — не навык, а рыночная реальность,
  которую не проговаривают ни вакансии, ни курсы: в целевой проверке 21
  remote-вакансии только 14% реально открыты для найма из Украины/B2B
  (см. подраздел выше). Это должно стать явной темой в программе
  (Фаза 3 — карьера), а не молчаливым допущением.

Эти четыре пункта — кандидаты на то, чтобы стать отдельным блоком в
Фазе 1 (проектирование программы), а не просто дополнением к списку
инструментов.
