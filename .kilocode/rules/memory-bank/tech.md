# Tech

## Стек (из SKILL.md `.kilo/skills/PR/SKILL.md` и docx)
- **Backend**: Python 3.14.0 (venv: `backend/.venv`), FastAPI 0.162, Pydantic 2.14 + pydantic-settings, SQLAlchemy 2.1.6 (asyncio), asyncpg 0.32, Alembic 1.20, uvicorn 0.54. Установлено 2026-11-01 через `pip install -e ".[dev]"`.
- **Инструменты backend**: ruff 0.17 (select E,F,I,B,UP,SIM; line 88), black 26.10, mypy 2.4 (strict + pydantic plugin), pytest 9.2. Команды (из `backend/`): `& .venv\Scripts\ruff.exe check .`, `& .venv\Scripts\black.exe .`, `& .venv\Scripts\mypy.exe app`, `& .venv\Scripts\python.exe -m pytest`, запуск API: `& .venv\Scripts\python.exe -m uvicorn app.main:app --port 8000`.
- ⚠️ Celery/Redis пока НЕ установлены (отложены до Фазы 3 — воркеры парсинга).
- Deprecation-предупреждение: fastapi TestClient рекомендует httpx2 (starlette) — не критично.
- **БД (dev)**: PostgreSQL 18.1 — кластер `backend/.pgdata` (gitignored), поднят `pg_ctl` от текущего пользователя, порт 5432, superuser `postgres` / `qcs_dev_2026` (scram), БД `quote_costing`. Служба Windows `postgresql-x64-18` остановлена (нужен админ) — ⚠️ при её запуске конфликт порта 5432.
- **Auth**: bcrypt (хеши) + PyJWT (HS256, `app/core/security.py`), токен 480 мин (APP_ACCESS_TOKEN_EXPIRE_MINUTES), secret — APP_SECRET_KEY (в .env для прода!). Роли в `app/domain/enums.py` (UserRole). Скрипт: `& .venv\Scripts\python.exe -m scripts.create_user EMAIL PASSWORD ROLE`.
- Dev-пользователи: admin@qcs.dev/admin12345 (ADMIN), manager@qcs.dev/manager12345 (MANAGER), technologist@qcs.dev/technolog12345 (TECHNOLOGIST). ⚠️ email-validator отвергает special-use домены (.local, .test) — только обычные.
- ⚠️ Гоччи FastAPI: имя параметра `request` в эндпоинте зарезервировано (starlette Request) — тело называть `payload`.
- ⚠️ Гочча tool_baskets: несколько диапазонов сверл одного типа → UQ (operation_group, iso) падает; решено уникальным индексом по coalesce(diameter_from_mm, -1) (миграция 8b4cd046dc20, в модели Index с text()). Сверлильные корзины ищутся в движке по префиксу DRILL_CARBIDE/DRILL_HSS + диапазону Ø.
- ⚠️ Гочча zustand+persist в Next SSR: сторы с persist читают localStorage при создании на клиенте → SSR(null) vs клиент(данные) → hydration mismatch ("server rendered HTML didn't match"). Паттерн: `skipHydration: true` в options persist + компонент `StoreHydrator` (useEffect → `.persist.rehydrate()`) в RootLayout. Также даты не форматировать toLocaleString на сервере — ручной formatDate (pad dd.MM.yyyy HH:mm).
- ⚠️ Гочча persist-гонка при обновлении страницы: `rehydrate()` завершается МИКРОЗАДАЧЕЙ после синхронного флеша эффектов страниц (эффекты идут child→parent, но промис позже них) — гварды `if (!token) router.replace("/login")` успевали увидеть token=null и выкидывали юзера при каждом F5. Фикс: флаг `hydrated` в auth-сторе (выставляется в StoreHydrator после `Promise.resolve(rehydrate()).then(...)`), все гварды страниц: `if (!hydrated) return;` перед проверкой token; login при `hydrated && token` сам редиректит на next/constructor. `partialize` в persist — только token+user (не персистить флаг).
- ⚠️ Гочча three-bvh-csg: `Evaluator.evaluate()` возвращает **Brush (extends THREE.Mesh)**, НЕ геометрию. Цепочка: `brush = evaluator.evaluate(brush, cutter, SUBTRACTION)`; для рендера брать `brush.geometry` (каст `as unknown as THREE.BufferGeometry` из-за расхождения типов). Заворачивание результата в `new Brush(result)` → TypeError "Cannot convert undefined or null to object". Версии: three 0.187.0 (одна копия, deduped), three-bvh-csg 0.0.18, three-mesh-bvh 0.9.17 (варнит про maxLeafSize→targetLeafSize — не критично).
- ⚠️ Гочча LatheGeometry (токарные превью T1-T3): нормали профиля считаются как (dy, −dx) — наружная поверхность обязана обходиться СНИЗУ ВВЕРХ (CCW). Замкнутые контуры «вверх по расточке → вниз по наружке» (T2 втулка, T3 фланец с отв.) дают инверсию ВСЕХ нормалей: деталь «наизнанку», CSG-вычитание артефачит. Фикс: `ensureCcw()` в geometry25d.ts — знак площади шнурования < 0 → reverse точек перед `new THREE.LatheGeometry`. T1 (незамкнутая лестница CCW) и Box (T4/T5) не страдали.
- ⚠️ Гочча SQLite (тесты) vs PostgreSQL (прод): NUMERIC-affinity SQLite схлопывает `30000.00` → INTEGER 30000, и GENERATED-колонка `scheduled/NULLIF(total,0)` делит ЦЕЛОЧИСЛЕННО (30% → 0!). PostgreSQL NUMERIC делит корректно. Правило: производные проценты/отношения считать в Python (DB-agnostic), GENERATED-колонки не читать в сервисах.
- ⚠️ Гочча live-стека: осиротевшие uvicorn-процессы переживают сессию и держат порт 8000 (новый процесс молча не биндится, ready-паттерн успевает совпасть). При рассинхроне поведения: `Get-NetTCPConnection -LocalPort 8000 -State Listen` → OwningProcess ≠ pid отслеживаемого процесса → Stop-Process сироты + перезапуск.
- ⚠️ Тесты кириллицей из PowerShell: `Invoke-RestMethod -Body ([Text.Encoding]::UTF8.GetBytes($json)) -ContentType "application/json; charset=utf-8"`, иначе в БД ложатся «?????».
- ⚠️ Гочча pydantic from_attributes: если имя поля DTO ≠ имени ORM-атрибута (rates vs performance_rates), model_validate МОЛЧА подставляет default (пустой список) вместо ошибки. DTO с relationship строить явно в сервисе.
- ⚠️ Гочча Next 16 Cache Components: `useParams()`/`use(params)`/`useSearchParams()` в рендере клиентского компонента блокируют пререндер («client rendering was requested outside a Suspense boundary», «URL data ... outside of <Suspense>»). Способы: Suspense-обёртка; `export const instant = false` (только из server-модуля page.tsx, НЕ из "use client"); либо читать данные URL из `window.location` в useEffect (выбрано для print-страницы).
- Интеграционные тесты: SQLite+aiosqlite (StaticPool, dependency_overrides[get_session]); числовые/роли проверки RBAC: manager→403, аноним→401, admin→201/200/204.
- Управление кластером: старт `& "C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe" -D backend\.pgdata -l backend\.pgdata\server.log -o "-p 5432" start`, стоп `... stop -m fast`; psql: `& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -h localhost -U postgres -d quote_costing` (PGPASSWORD=qcs_dev_2026).
- **Env-подводный камень**: в ОС машины задана переменная `DEBUG=release`, поэтому Settings использует префикс `APP_` (`APP_DATABASE_URL`, `APP_DEBUG` в `backend/.env`, gitignored; шаблон `.env.example`).
- **Alembic**: `backend/migrations/` (async env.py на asyncpg, URL из settings). Первая миграция `633b28864543_master_data_schema` — 11 таблиц master data. Команды (из `backend/`): `& .venv\Scripts\alembic.exe revision --autogenerate -m "..."`, `... upgrade head`. `migrations/` исключены из Ruff/Black.
- Enums БД — VARCHAR + CHECK (native_enum=False, легко расширять). `shop_capacity_load.utilization_rate` — GENERATED ALWAYS AS (scheduled/NULLIF(total)). Seed: строка TURNING_CNC 30% (пример из docx).
- **Фоновые задачи**: Celery, Redis (брокер).
- **Frontend**: Next.js 16.4.3 (App Router, создан 2026-11-01 в `frontend/`), React 19.3, TypeScript 5 (strict), TailwindCSS v4, shadcn/ui v4 (preset base-nova на примитивах @base-ui/react 1.9; CVA, lucide-react), Zustand (state, добавить позже), Three.js/WebGL, PDF.js.
- ⚠️ Next.js 16 содержит breaking changes относительно привычных конвенций — перед написанием кода читать гайды в `frontend/node_modules/next/dist/docs/` (см. `frontend/AGENTS.md`).
- Команды frontend (из `frontend/`): `npm run dev`, `npm run build`, `npm run start`, `npm run lint` (eslint 9 + eslint-config-next).
- **Типизация**: строгая — mypy (Python) и TypeScript.
- **Линт/стиль**: Ruff + Black, PEP 8, явные type hints на всех функциях.
- **Доп. инфраструктура**: MinIO/S3 (файлы), Qdrant/Milvus (векторный поиск аналогов), PythonOCC/OpenCascade (CAD), Tesseract/YOLO/Werk24 (OCR/CV).

## Критические технические ограничения
1. Деньги — только `decimal.Decimal` → `NUMERIC(12,2)`. Запрещён `float` для total_price, cost_per_kg, machine_rate_min.
2. Геометрия (V, A, размеры) — `float`, округление физических размеров до 3 знаков.
3. Никаких хардкодов ставок/плотностей/Q/S — только master data таблицы (`machine_financial_profiles`, `material_machinability`, `operation_performance_rates`).
4. Математическое ядро — чистые функции на DTO; БД только в Services/UseCases; UoW для транзакций.
5. Всё async (`async def`, asyncpg, AsyncSession); блокирующий I/O — в Celery-воркеры.
6. JWT + RBAC (MANAGER/TECHNOLOGIST/ADMIN) через FastAPI dependencies; нарушения → 403.

## Настройка окружения
- **Запуск всего стека**: корневой `start.ps1` (PowerShell 5.1, UTF-8 BOM): PostgreSQL (pg_ctl по `backend/.pgdata`, пропуск если :5432 слушается) → backend uvicorn :8000 (окно + health-check) → frontend `npm run dev` :3000 (окно + HTTP-check); каждый сервис в отдельном свернутом окне PowerShell (закрытие окна = стоп сервиса), идемпотентно по занятым портам; exit 1 + список незапущенных при ошибке. Запуск: `powershell -ExecutionPolicy Bypass -File .\start.ps1`.
- ОС: Windows (PowerShell 5.1), проект в `D:\Proj_01\a1`.
- Node v24.19.0, npm 11.17.0; ExecutionPolicy = RemoteSigned (npx работает, Set-ExecutionPolicy не требуется).
- Git-репозиторий инициализирован в КОРНЕ (branch `main`, 2026-11-01); коммитов пока нет — корневой `.gitignore` покрывает venv/node_modules/.env/кэши.
- Backend-скелет: `backend/` (см. architecture.md); проверки пройдены: ruff ✅, black ✅, mypy strict ✅, pytest 1 passed ✅, uvicorn `GET /api/v1/health` → 200 ✅.
- Frontend: zustand и three установлены (npm audit: 21 vulnerabilities — транзитивные, не исправлено).
- Frontend-скелет: `frontend/` — Next.js 16 (src/, алиас `@/*`), shadcn инициализирован (`components.json`, `src/components/ui/button.tsx`, `src/lib/utils.ts`). Проверено: dev-сервер готов за 920мс, `GET /` → 200.
- npm audit: 16 moderate (транзитивные зависимости свежего каркаса) — не критично, не исправлено.
- Файлы >100 КБ: только точечное чтение через Select-String / ограниченные диапазоны Get-Content (правило из rules/rulse.md).

## Зависимости и внешние интеграции (план)
- **OpenSCAD 2021.01 (портативный, Готово к Фазе A)**: источник — официальный репозиторий https://github.com/openscad/openscad (releases, pinned-тег `openscad-2021.01`); скрипт `backend/scripts/download_openscad.ps1` (идемпотентен: проверка `--version` + размер архива, TLS12 для PS 5.1, ищет в zip каталог с `openscad.com`) → `backend/vendor/openscad-2021.01/openscad.com`; `backend/vendor/` в корневом .gitignore. ⚠️ В GitHub releases НЕТ стабильных релизов новее 2021.01 — Manifold-сборки распространяются только через openscad.org snapshots → флаг `--backend=Manifold` НЕ поддерживается (ядро CGAL; точности при `$fn=72` достаточно). Смок-тест: `difference()` двух цилиндров ~0.5 c, STL валиден. Будущий порядок поиска бинарника в config: `APP_OPENSCAD_BIN` → `backend/vendor/openscad-*` → PATH → `C:\Program Files\OpenSCAD` (локальная установка 2021.01 — фолбэк). План внедрения: `План внедрения OpenSCAD.md`.
- ⚠️ Гочча истёкшего JWT: токен 480 мин; после истечения гварды страниц (проверяют только НАЛИЧИЕ токена) не выкидывают юзера — страницы показывали «Invalid token» (401 из `deps.py`) на всех запросах. Фикс (2026-11-04): `apiFetch`/`apiDownload` при 401 (кроме `/auth/*` — неверный пароль тоже 401, был бы редирект-цикл) диспатчат `UNAUTHORIZED_EVENT`; слушатель в StoreHydrator делает `logout()` + `window.location.assign("/login")` (logout обнуляет persist → login не bounce-loop).
- ⚠️ Гочча OpenSCAD STL-экспорта: CLI без явного флага пишет **ASCII STL** (~660 байт/фасет против 50 у бинарного — в ~6.5× тяжелее при той же сетке); из-за этого лимит `APP_SCAD_MAX_STL_MB` срабатывал на текстовый объём, а не на сложность модели. С 2026-11-04 `scad_compiler._compile_sync` передаёт `--export-format binstl` (поддерживают И 2021.01, И 2026.11 Manifold; three.js STLLoader и trimesh читают оба формата, метрики не меняются).
- APS-система / модуль планирования → таблица `shop_capacity_load` (Ugroup).
- CAM-системы (Mastercam, SprutCAM, NX) → парсинг отчётов времени цикла.
- MES/MDC → цикл План/Факт.
- 1С → синхронизация списаний/счетов (далёкая перспектива).
- Werk24 (или аналог) → парсинг PDF-чертежей.

## Паттерны кода
- DDD/Clean Architecture, Repository + Unit of Work, DTO (Pydantic V2).
- DRY: повторно используемая геометрия/модификаторы — в утилитные функции.
- Docstrings с формулами для сложных CSG/булевых алгоритмов.
- Компоненты Frontend — принцип единственной ответственности.
- Comments в коде — только для сложных секций.
