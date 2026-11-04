# Architecture

## Общая архитектура
4 независимых слоя (отказоустойчивость: зависший 3D-файл не кладёт БД):

1. **Frontend (SPA)**: React + Three.js/WebGL (рендеринг 3D в браузере, визуализация отверстий и токарных профилей) + PDF.js (разметка зон допусков на 2D). TailwindCSS.
2. **Backend API**: Python FastAPI. Ролевая модель (RBAC), версионирование расчётов, хранение истории.
3. **Computational Worker** (очередь Celery/Redis):
   - CAD-ядро (PythonOCC/OpenCascade): анализ STEP/IGES.
   - CV/OCR-модуль (Tesseract/YOLO/внешнее API типа Werk24): чтение штампа, поиск квалитетов (IT6, Ra0.8), ТТ.
4. **БД**: PostgreSQL (справочники + расчёты) + MinIO/S3 (чертежи, 3D-модели) + Qdrant/Milvus (векторный поиск деталей-аналогов по геометрии).

## Ключевые architectural решения (СТРОГО обязательны)
- **Clean Architecture / DDD**: математическое ядро `FeatureCostingEngine` — чистые функции, принимают Pydantic DTO и возвращают DTO. ЗАПРЕЩЕНЫ вызовы БД/SQLAlchemy-сессий внутри доменного слоя. Все запросы к БД — только в слое Services/UseCases. ORM-модели не передавать в доменный слой.
- **Unit of Work + Repository**: все мутации БД (сохранение quote + features + routing) в одной транзакции; `session.commit()` только в конце UoW, `rollback()` на исключениях.
- **Async I/O**: все эндпоинты и запросы к БД (`asyncpg`, `AsyncSession`) — `async def`. Блокирующий I/O в главном потле запрещён.
- **Точность денег**: НИКОГДА `float` для финансовых данных (`total_price`, `cost_per_kg`, `machine_rate_min`) — только `decimal.Decimal` → `NUMERIC(12,2)` в PostgreSQL. Геометрия (Vnet, Vrem, Asurf) — `float`, физические размеры округлять до 3 знаков (микроны).
- **Без хардкода**: ставки станков, плотности материалов, скорости Q/S — только из таблиц master data.

## Информационная модель (5 справочников Master Data)
1. **Материалы и Сортамент**: марка (Сталь 45, Д16Т, 12Х18Н10Т), плотность ρ, профиль (круг/лист/труба/шестигранник), сетка типоразмеров, цена за кг (Pmat), Kmach, цена стружки (Pscrap).
2. **Оборудование (Рабочие центры)**: тип (токарный ЧПУ, 3-ос. фрезерный, 5-ос., эрозия), рабочая зона X/Y/Z, мощность шпинделя, nmax, стоимость + срок амортизации, энергопотребление, Tпз_баз.
3. **Операции и Переходы**: тип операции, станок, формула To, Q (см³/мин черновая) / S (мм²/мин чистовая), Tв_уст по весовым категориям.
4. **Инструментальные корзины**: группа операции × группа материала, стоимость комплекта (Ctool), стойкость (Tlife 45-60 мин).
5. **Коэффициенты и Кооперация**: наценки за квалитеты/Ra/нежесткость (L/D>5), цены подрядчиков (термо за кг, гальваника за дм², лазер за пог. м).

## Математическое ядро (Costing Engine)
Разбито на 3 модуля геометрии:
- **Механообработка (2.5D CSG)**: Vgross − Σ(ΔVf) → Vnet, Vrem; To = Vrem/(Q·Kmach) + Asurf/(S·Kmach·Kгеом·Kдопуск).
- **Листообработка (T6)**: развёртка + nesting (Knesting 0.75-0.85), To_laser = Pcut/Vcut + Npierce·tpierce, To_bend по числу гибов; расход газа O2/N2 в прямых затратах.
- **Сварка**: по катету (k) и длине (Lweld): Aseam = k²/2, Massweld = k²/2·L·Kусиления(1.15), Tarc = Mass/Gweld, Tшт_weld = Tarc/Karc(0.3-0.45) + зачистка.

## Формулы нормирования (сводка)
- Tшт-к = Tшт + Tпз/n; Tшт = (To + Tв)·(1 + (αобс+αотд)/100%), α ≈ 6-9%.
- To попереходно: точение To = Lр·i/(n·sоб); фрезерование To = Lр·i/Fмин.
- Tв = Tуст_снят(Mgross, тип зажима) + Nуст·Tпереворот + Nинстр·Tсмена + Tизм(квалитет, партия) — не перекрывается машинным временем.
- Заготовка: Dзаг = Dpart + 2·Δrad; Lзаг = Lpart + Δторц + Δрез(2-3мм) + Lкулачки/Nзаг.
- Материал: Cmat = Mgross·Pmat·Kлог_отх(1.05-1.10) − (Mgross−Mnet)·Kсбора(0.7)·Pscrap.
- Ставка минуты: Rtotal_min = Ramort + Renergy + Rlabor_gross·1.3/Kmultimachine + Roverhead_shop + Roverhead_plant.
- Динамическая цена: Price_final = [Cmat + Ccoop + Σ(Tшт_i/60·R_i + Ctool_i + Tпз_i/(60·N)·R_i)]·(1 + Margin_base·Kmargin(Ugroup)/100%).
- Floor Price: Cmat + Ccoop + To/60·Rmach + Tsum/60·Rlabor + Ctool·1.05 — ниже цены не бывает.

## APS / динамическая маржа
- Ugroup = запланированные минуты группы / эффективный фонд на горизонте 30 дней; обновляется APS каждые N минут (таблица `shop_capacity_load`, функция `get_dynamic_margin_multiplier`).
- Kmargin: U<40% → 0.4-0.7 (Marginal Costing); 40-80% → 1.0 (Target Costing); 80-95% → 1.25-1.5; >95% → 1.8-2.5 (Surge Pricing, Rlabor×2 за сверхурочные).
- Узкое место маршрута = max(Ugroup) по всем станкам маршрута.

## Шаблоны 2.5D-конструктора
T1 Ступенчатый вал/Ось/Шток (массив ступеней Di×Li×ITi×Rai; пруток/поковка) · T2 Втулка/Кольцо/Стакан (Dout/din ступени; пруток или труба) · T3 Фланец/Диск/Крышка (L/D<0.5, бурт, центральное отв., массив отв. по делительной окружности) · T4 Плита/Планка/Блок (L×W×H, флаг обработки граней) · T5 Корпус/Кронштейн (Kвыб, карманы/окна; до 70-85% металла в стружку) · T6 Листовая + Гибка (s, развёртка, Pcut, Npierce, Nbends).

Фичи-модификаторы: группы отверстий, цековки/зенковки, прямоугольные карманы/пазы/шпонки, цилиндрические колодцы, уступы по контуру, лыски/шестигранники, канавки. Штрафные мультипликаторы: KIT/Ra (чистовой обход), Kгеом.

## Безопасность
- JWT-аутентификация: `POST /api/v1/auth/login` (email+пароль → access_token HS256, 480 мин), `GET /api/v1/auth/me`. Хеши bcrypt.
- RBAC через FastAPI Depends: `get_current_user` (Bearer → User, 401 при отсутствии/инвалидности), `require_roles(*roles)` (403). MANAGER — read-only master data + POST /quotes, /calculate; TECHNOLOGIST — PATCH маршрутов/ставок; ADMIN — полный CRUD (реализовано на /materials).

## API-контракты
- **Реализован** `POST /api/v1/calculate/25d-feature` (RBAC MANAGER+): discriminated union base_template (T1_STEPPED_SHAFT/T2_BUSHING/T3_FLANGE/T4_PLATE/**T5_HOUSING**) + features (HOLE_ARRAY с опц. counterbore_diameter/depth, RECT_POCKET); material снапшотом в запросе (k_mach_rough/k_mach_finish/density/cost/scrap), Q/S + Tпз + ставка группы + KIT + drilling_rates (вкл. hss_feed) — из БД (Services). Ответ: v_net/v_gross/v_removed_cm3, m_net/m_gross_kg, material_cost, machine_time_min, setup_time_min, price_per_part, batch_total_price (Decimal, margin_percent в запросе), tool_cost, **cooperation_cost + cooperations[]**, margin_multiplier + capacity_utilization_percent + **bottleneck_group** (APS: Kmargin по max(Ugroup) всех групп маршрута) + **floor_price_per_part** (пол переменных издержек: Cmat+Ccoop+ΣTo·R без α/Tпз+труд+Ctool; в print/Excel не выводится — внутренняя метрика). T5: Vnet = L·W·H·(1−removal_ratio) − ΣVфич; операция MILL_CNC_FACE. **Кооперация**: `cooperation: [{service_id, qty_override}]` — цены только из БД (Services резолвит, 422 при неизвестном id); авто-qty: KG→m_net, DM2→(a_outer+a_inner)/100, PIECE→1, METER→требует qty_override (ValueError→422); MOQ амортизируется min_lot/batch; Ccoop добавляется к себестоимости ДО маржи (по docx).
- **Реализовано** `POST /api/v1/quotes` {name, material_id, request: CalculateRequestDTO} → серверный пересчёт + сохранение снапшотов (JSON) в таблицу quotes (миграция 45a320f16275); `GET /quotes` (список), `GET /quotes/{id}` (detail со снапшотами), `DELETE /quotes/{id}` (автор или ADMIN, иначе 403), `GET /quotes/{id}/export.xlsx` → КП в Excel (openpyxl, `services/quote_export.py`: секции Деталь/Материал/Результаты/Цена). Фронт: SaveQuote в конструкторе, `/quotes` с «Открыть» → `hydrateFromRequest` и «Excel» → `apiDownload` (blob).
- Отступление от docx-контракта: `k_mach` → `k_mach_rough` + `k_mach_finish` (docx-матрица различает Kq/Ks).
- **Реализовано** `GET /api/v1/tool-baskets` (все авторизованные) и `PATCH /tool-baskets/{id}` (ADMIN: tool_set_cost/tool_life_min/regrindable; группа и диапазоны Ø не редактируются v1). Фронт: `/tools` — таблица 18 корзин с inline-редактированием; `/materials` — inline PATCH (grade/gost/iso/ρ/Kq/цены).
- **Реализовано** (файл `app/api/v1/master_data.py`, сервис `MasterDataService`): `GET /operations` (операции + вложенные rates Q/S по ISO-группам), `PATCH /operations/{id}` (setup_time_base_min), `PATCH /operation-rates/{id}` (q_rough/s_finish), `GET /work-centers` (+ machine_rate_per_min из профиля), `PATCH /work-centers/{id}` (machine_rate_per_min, upsert MachineFinancialProfile), `GET /coefficients`, `PATCH /coefficients/{id}` (multiplier), `GET /auxiliary-operations`, `PATCH /auxiliary-operations/{id}` (fixed_time_min/rate_per_min/is_active), `GET /drilling-rates` (сортировка по Ø), `PATCH /drilling-rates/{id}` (carbide/hss feed), полный CRUD `/cooperation-services` (POST 201/PATCH/DELETE 204 ADMIN; CooperationServiceType×PriceUnit валидируются enum'ами). Все GET — авторизованным, PATCH/POST/DELETE — ADMIN, 404 если нет записи. Фронт: `/rates` — 6 секций (`components/rates/`: Operations, WorkCenters, Coefficients, Auxiliary, Drilling, Cooperation с формой добавления); печатное КП `/quotes/[id]/print` (клиентский `QuotePrintView` + `lib/quote-format.ts` — зеркало секций Excel-экспорта + маршрут operations[]; print-стили Tailwind, кнопка «PDF» в /quotes открывает в новой вкладке).

## OpenSCAD-интеграция (ПЛАН 2026-11-03, не реализовано; полный план — `План внедрения OpenSCAD.md`)
Утверждённые решения (не ломают контракты; всё аддитивно, kill-switch `APP_OPENSCAD_ENABLED`):
- **GeometryOverride**: 3-й опциональный параметр `FeatureCostingEngine.calculate(request, rates, geometry_override=None)` — costing.py/geometry.py не меняются; запрос без `scad_code` → ответ побитово прежний.
- DTO: `CalculateRequestDTO.scad_code: str | None` (опционально — старые снапшоты quotes валидируются); `base_template` остаётся ОБЯЗАТЕЛЬНЫМ (для SCAD-режимов фронт подбирает шаблон из bbox — сохраняет TEMPLATE_OPERATION/INNER_OPERATION и расчёт сверления/корзин).
- Разделение: STL-превью — отдельный `POST /scad/preview` (RBAC как у calculate); расчёт STL не возвращает; лестница тиражей компилирует SCAD ОДИН раз (не ×7).
- Геометрия: v_gross всегда АНАЛИТИЧЕСКИЙ (формулы припусков geometry.py); сетка (trimesh) даёт v_net и a_total; a_inner = Σπ·d·L по извлечённым фичам (не «конверт заготовки»).
- Clean Architecture: subprocess-компиляция — `services/scad_compiler.py` (asyncio.to_thread, timeout 15 c, LRU-кэш, temp-dir, CREATE_NO_WINDOW, запрет import()/surface() флагом); чистые метрики — `domain/engine/scad_metrics.py`.
- Фронт: 3 режима (TEMPLATE — текущий three-bvh-csg НЕ трогается / SCAD_CUSTOMIZER — ползунки из кастомайзер-комментариев `// [min:step:max]` / SCAD_RAW_CODE — вставка кода); фичи из `// @feature HOLE_ARRAY ...` тегов — сразу, из эвристического парсинга difference() — только с подтверждением пользователя.
- Бинарник: github.com/openscad/openscad releases → `backend/vendor/openscad-2021.01/` (скрипт готов, см. tech.md); 2021.01 = последний стабильный в релизах, без Manifold.

## Расчётное ядро (реализовано, `app/domain/engine/`)
- geometry.py: CSG-объёмы T1-T5 + фичи, заготовка с припусками (радиальный 2.5×2, торцевой 2.5×2, пропил 3); Asurf разделён на **a_outer** (наружные цилиндры+торцы) и **a_inner** (расточка T2, центральное отверстие T3); ⚠️ единицы: объёмы мм³, Q см³/мин → t_rough = Vrem/1000/(Q·Kq); масса = V·ρ/1e6.
- costing.py (мульти-операции): main + optional inner (T2 → TURN_CNC_INT, S=2.2); To_main = Vrem/(Q·Kq) + a_outer/(S_main·Ks)·KIT + Σсверление; To_inner = a_inner/(S_inner·Ks)·KIT; каждая ×1.08; Tпз суммарный по операциям; ответ содержит operations[] (code/name/time/setup/rate/cost/**tool_cost**) + tool_cost итого. **Инструмент (модель заказчика)**: расход = To(без α)×(Ctool/Tlife)×Kwear×1.05; переточка (regrindable): минутная стоимость ×0.733 (=Ctool·2.2/(3·Tlife)); сверлильные корзины DRILL_CARBIDE/DRILL_HSS по диапазонам Ø, подача сверления по drill_type (HSS из drilling_rates.hss_feed); спец-инструмент special_tool_cost — 100% на партию (÷batch). Cmat=Mgross·Pmat−(Mgross−Mnet)·0.7·Pscrap; цена=(Cmat+Σ(Tшт_i+Tпз_i/N)·R_i+tool+special/N)×(1+margin). Aux-операции (auxiliary_operations) — фикс. время × трудовая ставка.

## Информационная модель — реализованная схема БД (миграции 633b28864543 → 8d38f4d26908)
Справочники (все с TimestampMixin created_at/updated_at), seed из docx:
1. **materials** (13 строк): grade (unique), gost, iso_group (P/M/K/N/S/H), density_g_cm3, machinability_factor (Kq), cost_per_kg, scrap_price_per_kg. Эталон — «Сталь 45» (7.82 г/см³, K=1.00).
2. **material_assortment**: FK materials (CASCADE), profile (ROD/PLATE/TUBE/HEXAGON), size_mm; UQ(material, profile, size).
3. **material_machinability** (13 строк, operation_group='ALL'): machinability_factor (Kq черновой), **k_finish_factor (Ks чистовой)**, **tool_wear_factor (Kwear)** — диапазон: алюминий 3.20/2.50/0.35 … титан 0.28/0.38/3.20 … закалённые 0.18/0.35/3.80.
4. **work_centers** (6): TURN_CNC_01, TURN_MANUAL_01, MILL_3AX_01, MC_5AXIS_01, GRIND_01, WEDM_01 (machine_type, group_code для APS, мощность).
5. **machine_financial_profiles**: 1:1 FK; заполнен только MC_5AXIS_01 (25М₽/7 лет/14кВт → **47.99 ₽/мин**, оператор 36₽/ч при k=2, ОПР 65%+ОХР 30%).
6. **operations** (10): code TURN_CNC_EXT/TURN_CNC_INT/TURN_MANUAL/MILL_CNC_FACE/D16/D10/D5/D3/MILL_5AXIS_3D/GRIND_CYL; + **min_tool_diameter_mm** (2–50), + **setup_time_base_min** (25–60).
7. **operation_performance_rates** (10 × ISO P): Q 0.45–48 см³/мин, S 0.22–6.50 дм²/мин (基准 — Сталь 45; для других материалов умножать на Kq/Ks).
8. **tool_baskets**: operation_group × material_iso_group (UQ), tool_set_cost, tool_life_min (пока НЕ заполнен — данных в docx нет).
9. **coefficients** (7): TOLERANCE IT12-14=0.65 / IT10-11=1.00 / IT8-9=1.65 / IT7=2.60 / IT6=4.20; GEOMETRY THIN_WALL=0.45 (Q×), INTERRUPTED_CUT=0.65 (Q×, Kwear×1.70).
10. **cooperation_services**: пока НЕ заполнен (цен в извлечённых частях docx нет).
11. **shop_capacity_load**: work_center_group (unique), horizon_days (default 30), utilization_rate GENERATED STORED. Seed: TURNING_CNC 30%.

## Структура исходного кода (монорепо `D:\Proj_01\a1`, git branch `main`)
```
backend/                      # FastAPI + Clean Architecture
  pyproject.toml              # зависимости + Ruff/Black/mypy(strict)/pytest
  .env / .env.example         # APP_DATABASE_URL, APP_DEBUG (префикс APP_!)
  alembic.ini + migrations/   # async-миграции (первая: master data, 11 таблиц)
  app/
    main.py                   # app factory, include_router /api/v1
    core/config.py            # pydantic-settings (env_prefix="APP_")
    db/session.py             # async engine + get_session (AsyncSession)
    db/models/                # ORM: base, enums, material, equipment, operation, tooling, coefficient, aps
    api/v1/                   # router.py, health.py (эндпоинты)
    domain/                   # ЧИСТОЕ ядро: dto/, engine/ (FeatureCostingEngine) — без БД
    services/                 # UseCases — здесь транзакции и вызовы repositories
    repositories/             # Repository + Unit of Work
  tests/test_health.py
frontend/                     # Next.js 16 (App Router, src/, @/*)
  src/app/constructor/page.tsx  # 2.5D-конструктор: workspace 30/45/25 + debounce-пересчёт
  src/components/constructor/   # Viewport25d (R3F+CSG), TemplateForm, FeatureTree, CostBreakdown
  src/lib/geometry25d.ts        # превью-геометрия: LatheGeometry (T1-T3), Box (T4), раскладка фич
  src/lib/constructor-types.ts  # DTO-зеркала контракта /calculate/25d-feature
  src/stores/constructor.ts     # zustand+persist "qcs-constructor" (черновик, дефолт = docx-пример T2)
  src/app/login/page.tsx      # JWT-логин (email+пароль → токен в zustand persist)
  src/app/materials/page.tsx  # справочник: shadcn-таблица, CRUD только для ADMIN
  src/lib/api.ts              # apiFetch-обёртка (Bearer, ApiError, 204/JSON)
  src/lib/types.ts            # User, Role, Material (k_mach_finish/tool_wear включены)
  src/stores/auth.ts          # zustand + persist ("qcs-auth")
  src/components/ui/          # shadcn: button, input, label, card, table
.gitignore                    # корневой (venv, node_modules, .env, кэши)
```
 Правило: энпоинт → service → repository; domain импортирует только DTO. Frontend вызывает API через `apiFetch` (базовый URL: NEXT_PUBLIC_API_URL, по умолчанию http://localhost:8000/api/v1); backend CORS: allow_origins из settings.cors_origins. 3D-превью: three-bvh-csg (вычитание фич), три-типа Brush ≠ THREE.BufferGeometry по типам — каст `as unknown as THREE.BufferGeometry`. Паттерн CRUD-справочников: GET всем + PATCH ADMIN + inline-редактирование в таблице (см. tool-baskets/master_data); DTO с ORM-relationship строить явно в сервисе (не model_validate — from_attributes молча даст default при несовпадении имени поля).
