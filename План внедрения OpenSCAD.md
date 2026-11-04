# План внедрения OpenSCAD (без нарушения работоспособности)

Источник: `Внедрение OpenSCAD.md` (паттерн «SCAD-транслятор + GeometryOverride»).
Этот документ — адаптация предложения к реальному коду проекта с исправлением мест,
которые ломают архитектуру/контракты, и с улучшениями.

## 0. Что нельзя ломать (контракт стабильности)

1. `POST /calculate/25d-feature` и `/calculate/25d-feature/ladder`: поведение при запросе
   БЕЗ `scad_code` должно остаться побитово прежним (золотые числа, 47 тестов).
2. Цепочка `calculation_service.py → FeatureCostingEngine → costing.py`:
   TEMPLATE_OPERATION / INNER_OPERATION, drilling_bands (D16..D3), tool_baskets × Kwear,
   кооперация, APS-маржа, Floor Price — не меняются.
3. Clean Architecture: домен (`app/domain/**`) — чистые функции, НИКАКОГО subprocess/БД внутри.
4. Async-правило: блокирующий I/O (subprocess openscad, загрузка STL) — не в главном потоке
   события (`asyncio.to_thread`), Celery пока не установлен.
5. Снапшоты quotes: старые JSON должны валидироваться (новое поле — только опциональное).
6. Frontend: TEMPLATE-режим (three-bvh-csg) остаётся как есть и как фолбэк — он работает.
7. Persist-стор `qcs-constructor`: старые черновики должны подниматься (новые поля — с дефолтами).

Факты окружения (проверено 2026-11-03):
- **Источник — официальный репозиторий https://github.com/openscad/openscad/** (решение
  пользователя). В `releases` публикуются только стабильные релизы; последний — `openscad-2021.01`
  (сборки с Manifold-ядром новее 2023 г. в GitHub releases отсутствуют — они распространяются
  через openscad.org; поэтому `--backend=Manifold` не используем, см. D5).
- Создан и выполнен `backend/scripts/download_openscad.ps1`: качает портативный
  `OpenSCAD-2021.01-x86-64.zip` из pinned-релиза репозитория и распаковывает в
  **`backend/vendor/openscad-2021.01/openscad.com`** (в git не попадает — добавлено в .gitignore;
  скрипт идемпотентен, проверяет `--version`). Смок-тест пройден: difference() двух цилиндров
  компилируется ~0.5 c, STL валиден.
- Локальная установка `C:\Program Files\OpenSCAD` (та же 2021.01) — только фолбэк, если
  vendor-каталога нет; в PATH бинарник отсутствует.
- `trimesh` и `numpy` в `backend/pyproject.toml` отсутствуют — добавить.
- В `calculation_service.ladder()` движок вызывается ×7 (тиражи) — компиляция SCAD должна
  выполняться ОДИН раз на запрос, а не в каждом `_run`.

## 1. Ключевые решения и отличия от исходного предложения

| # | Предложение в материале | Решение в этом плане | Почему |
|---|---|---|---|
| 1 | STL возвращается из `compile_and_measure_scad()` вместе с расчётом | Отдельный лёгкий эндпоинт `POST /scad/preview` (STL + bbox + v_net); расчёт возвращает те же поля, что и раньше | Бинарный STL (1–5 МБ base64) не нужен ни в лестнице тиражей, ни в CostBreakdown; разделяем частоту превью и частоту расчёта |
| 2 | `subprocess` в `app/domain/engine/scad_geometry_adapter.py` | Компиляция — `app/services/scad_compiler.py` (инфраструктура); чистые метрики — `app/domain/engine/scad_metrics.py`; движок принимает готовый `GeometryMetrics` | Домен остаётся чистым (правило архитектуры); тестируемость без бинарника |
| 3 | `geometry.py` считает `v_gross` из extents сетки по новым формулам | `v_gross` остаётся АНАЛИТИЧЕСКИМ — по тем же формулам припусков `geometry.py` (RADIAL 2.5×2, FACE 2.5×2, CUT 3). Сетка даёт только `v_net` и `a_total` | Золотые числа заготовки не «плывут»; один и тот же припуск для шаблона и SCAD-режима |
| 4 | `a_inner = a_total − a_конверта заготовки` | `a_inner` = Σπ·d·L по извлечённым отверстиям/расточке (фичи или парсер), `a_outer = a_total − a_inner`; если фич нет — `a_inner = 0` | Формула материала даёт технологически неверную «внутреннюю» площадь (конверт заготовки — не поверхность детали); семантика `a_inner` = расточка/отверстия, как в аналитике |
| 5 | `base_template` заменяется режимом `mode` | `base_template` остаётся ОБЯЗАТЕЛЬНЫМ: фронт для SCAD-режимов отправляет авто-подобранный шаблон (габариты из bbox, T1–T3 для тел вращения, T4/T5 для призматических) | `TEMPLATE_OPERATION`/`INNER_OPERATION` (расточка только у T2) продолжают работать без единого изменения; вьюпорт/печать/Excel не меняют структуру |
| 6 | Синхронный `subprocess.run` в запросе | `await asyncio.to_thread(...)` + `timeout=N` (kill зависшей компиляции), `CREATE_NO_WINDOW` на win32 | Async-правило; OpenSCAD без таймаута может зависнуть на рекурсии |
| 7 | Перезапись текста кода при движении ползунка Customizer | Базовый код неизменен + переменные через CLI-флаг `-D name=value`; LRU-кэш по хэшу(базовый код + переменные) | Кэш-хиты при перетаскивании ползунка; пользовательский код не «перезаписывается» молча (в Фазе B допустим и вариант перезаписи — он уже реализован в материале) |
| 8 | `syncFeaturesFromCustomScad` молча пополняет `features[]` | Явные теги `// @feature HOLE_ARRAY ...` применяются сразу; эвристический парсинг `difference(){ cylinder(...) }` — только через баннер подтверждения «Найдено N переходов — Применить?» | Регексп по чужому коду ошибается; молчаливая перезаписьUser-фич ломает доверие и расчёт |
| 9 | Генератор SCAD из упрощённых шаблонов (один d_out/d_in) | Генератор обязан отражать ПОЛНЫЕ шаблоны проекта: `outer_steps[]`/`inner_steps[]` (T2), центральное отверстие T3, окна T5 по `removal_ratio` (как в `geometry25d.ts`) | Иначе превью и v_net перестанут соответствовать аналитике тех же данных |
| 10 | Нет kill-switch | `APP_OPENSCAD_ENABLED` (default true) + автопоиск бинарника: `APP_OPENSCAD_BIN` → `backend/vendor/openscad-*/openscad.com` (из репозитория, ставится скриптом) → PATH → `C:\Program Files\OpenSCAD`; capability `scad_available` в `/health` | Мгновенный откат; фронт прячет SCAD-кнопки, если бинарника нет |
| 11 | WASM-компиляция в WebWorker как равнозначный вариант | Фаза D (опционально): openscad-wasm ~30 МБ; v1 — только серверная компиляция | Не тащить 30 МБ в бандл до подтверждения ценности |

Существенное уточнение по `a_inner`/расточке: `INNER_OPERATION` (TURN_CNC_INT) включается
только при `type == "T2_BUSHING"`. Поэтому авто-детектор шаблона обязан ставить T2, если в
коде есть центральная расточка (вычитаемый цилиндр на оси) — иначе расточка не попадёт в
маршрут. Это фиксируем тестом.

## 2. Целевой поток данных

```
Zustand (qcs-constructor)
  mode: 'TEMPLATE' | 'SCAD_CUSTOMIZER' | 'SCAD_RAW_CODE'
  scadCode: string            ← двусторонняя синхронизация с ползунками Customizer
  features[]                  ← пополняется из @feature-тегов (с подтверждением)
        │
        ├──debounce 400ms──► POST /scad/preview {scad_code}            [новый]
        │                     ← {stl_base64, bbox_mm, v_net_cm3, compile_ms}
        │                     → Viewport25d: STLLoader → BufferGeometry
        │                       (Bounds/Edges(25°)/Grid/Gizmo — прежняя сцена)
        │
        └──debounce 400ms──► POST /calculate/25d-feature (+/ladder)    [расширен]
                              request.scad_code? ──► scad_compiler (1 раз!)
                                 → MeshMeasurements → scad_metrics.build_override()
                                 → GeometryMetrics(v_net, v_gross-аналитич., a_outer, a_inner)
                              FeatureCostingEngine.calculate(request, rates, override?)
                              → costing.py БЕЗ ИЗМЕНЕНИЙ → тот же CalculationResultDTO
```

Подмена геометрии — опциональным третьим параметром:

```python
# costing.py — единственный diff (2 строки):
geo = geometry_override if geometry_override is not None else geometry.net_metrics(request)
```

## 3. Пофазный план

### Фаза A — Backend (фронт не затронут; все существующие тесты остаются зелёными)

| Шаг | Файл | Изменение |
|-----|------|-----------|
| A0 | `backend/scripts/download_openscad.ps1` | ✅ ГОТОВО (2026-11-03): загрузка pinned-релиза из github.com/openscad/openscad → `backend/vendor/openscad-2021.01/`; `.gitignore` дополнен; смок-тест компиляции пройден. Обновление версии = сменить `$Version`/`$Url`/`$ExpectedBytes` в скрипте |
| A1 | `app/core/config.py` | `openscad_bin: str = ""` (автопоиск: env → `backend/vendor/openscad-*` → PATH → Program Files), `openscad_timeout_s: int = 15`, `openscad_enabled: bool = True`, `scad_max_code_bytes`, `scad_max_stl_mb` |
| A2 | `pyproject.toml` | `+trimesh>=4` (тянет numpy); mypy-override `trimesh.*` при необходимости |
| A3 | `app/domain/dto/calculation.py` | `CalculateRequestDTO.scad_code: str \| None = Field(default=None, max_length=100_000)` — опционально, старые снапшоты quotes валидируются |
| A4 | `app/services/scad_compiler.py` (новый) | `compile_to_stl(code) -> CompiledStl` через `asyncio.to_thread`: temp-dir, `[bin, "-o", stl, scad]` (без `--backend` для 2021.01; флаг добавлять только если версия ≥2023), `creationflags=0x08000000`, timeout → `ScadCompileError`; LRU-кэш (hash(code) → результат, cap 32); `measure(stl_bytes) -> MeshMeasurements(extents, volume_mm3, area_mm2)` через trimesh; санитизация: код >N байт → 422, `import(`/`surface(` опционально запрещаются флагом конфига |
| A5 | `app/domain/engine/scad_metrics.py` (новый) | Чистая функция `build_geometry_override(template_type, dims, mesh, features) -> GeometryMetrics`: `v_net = mesh.volume` (мм³); `v_gross` — аналитическая формула заготовки по габаритам шаблона (вызывает существующие константы `geometry.py`); `a_inner = Σ π·d·L` по HOLE_ARRAY-фичам (+центральная расточка T2/T3), `a_outer = mesh.area − a_inner`; валидация `v_gross ≥ v_net` иначе ValueError→422 |
| A6 | `app/domain/engine/costing.py` | 3-й опциональный параметр `geometry_override: GeometryMetrics \| None = None` (см. §2) |
| A7 | `app/services/calculation_service.py` | В `calculate()` и `ladder()`: если `request.scad_code` — компилировать/мерить ОДИН раз до `_run` и передавать override; `ladder` не должен компилировать ×7 |
| A8 | `app/api/v1/scad.py` (новый) + `router.py` | `POST /scad/preview` {scad_code} → {stl_base64, bbox_mm[3], v_net_cm3, compile_ms}; RBAC = как у calculate; `scad_available: bool` в `/health` (или отдельный GET /scad/capability) |
| A9 | `tests/test_scad.py` (новый) | Unit `scad_metrics` на фиксированных числах; интеграция с реальным бинарником `@pytest.mark.skipif(not shutil.which...)` + путь Program Files (сверка v_net цилиндра с аналитикой, допуск 0.5%); негативные: синтаксическая ошибка→422, таймаут (код с глубокой рекурсией), пустой меш; регрессия: тот же запрос без/с `scad_code=None` → идентичный ответ |

Готовность фазы A: `pytest` green (47 + новые), ruff/black/mypy green, smoke curl по `/scad/preview`
и расчёту с `scad_code` (числа объяснимы), kill-switch работает.

### Фаза B — Frontend: SCAD-режимы (TEMPLATE-ветка не трогается)

| Шаг | Файл | Изменение |
|-----|------|-----------|
| B1 | `lib/constructor-types.ts` | `+scad_code?: string` в CalculateRequest; `+ConstructorMode` |
| B2 | `stores/constructor.ts` | `+mode: "TEMPLATE" \| "SCAD_CUSTOMIZER" \| "SCAD_RAW_CODE"`, `+scadCode: string`, `+scadStl/scadMeta` (кэш последнего превью), `setMode/setScadCode/resetScadMode`; persist поднимает старые черновики (поля с дефолтами) |
| B3 | `lib/scadGenerator.ts` (новый) | `generateScadFromStore(state)`: ПОЛНЫЕ шаблоны (T1 steps, T2 outer_steps+inner_steps, T3 центр. отверстие, T5 окна по removal_ratio), `$fn=72`, переменные с кастомайзер-комментариями `// [min:step:max] Русский лейбл` |
| B4 | `lib/scadCustomizer.ts` (новый) | `extractCustomizerParams(code)`, `updateScadVariable(code, name, value)` (из материала; поправить регулярку материала — в нём битый escape `\[$...)`) |
| B5 | `components/constructor/Viewport25d.tsx` | Тулбар режимов; `mode==="TEMPLATE"` → текущий PartMesh (three-bvh-csg) без изменений; SCAD-режимы → новый `ScadPartMesh` (debounce-вызов /scad/preview, STLLoader→BufferGeometry, Center, `Edges threshold=25`); при недоступности OpenSCAD — плашка и фолбэк на TEMPLATE-превью |
| B6 | `app/constructor/page.tsx` | При SCAD-режимах: `request.scad_code = scadCode`, `base_template` — авто-подбор из bbox превью (токарное тело → T1/T2/T3 с габаритами из bbox; центральная расточка → T2; призматическое → T4), габариты.dimensions заполняются из bbox чтобы v_gross считался аналитически корректно |

Готовность фазы B: `npm run build` + `lint` green; в TEMPLATE-режиме рендер идентичен прежнему;
вставка кода из материала (`d_out/d_bore/h_part/hole_*`) → ползунки + превью + расчёт.

### Фаза C — Экстрактор технологических признаков + сохранение

| Шаг | Изменение |
|-----|-----------|
| C1 | `lib/scadFeatureExtractor.ts` (новый): 1) `// @feature HOLE_ARRAY count= d= depth= through= drill=` — приоритет, применяется сразу; 2) best-effort: вычитаемые `cylinder(h=,d=/r=)` внутри `difference()` + `for(i=[0:n-1])` → кандидаты; центральный осевой цилиндр → маркер расточки (T2) |
| C2 | Баннер подтверждения для эвристических кандидатов («Найдено 3 перехода сверления — Применить / Игнорировать»); features[] никогда не перезаписывается молча |
| C3 | Авто-детектор группы операций для RAW-кода: `rotate_extrude()/cylinder()` в корне → токарная группа; `cube()/linear_extrude()` → фрезерная (выбор base_template в B6) |
| C4 | `hydrateFromRequest`: `request.scad_code` → режим RAW_CODE + код в стор (открытие сохранённых КП работает); печатное КП — блок «Модель OpenSCAD» (габариты + первые строки кода); Excel без изменений (поле уезжает в снапшот автоматически) |
| C5 | Сквозной чек: сохранение SCAD-КП → переоткрытие → пересчёт даёт те же числа (компиляция детерминирована) |

### Фаза D — Оптимизации (опционально, по отдельному решению)

- D1: `-D name=value` вместо перезаписи текста кода → стабильный хэш базового кода, кэш-хиты при движении ползунков.
- D2: openscad-wasm в WebWorker для мгновенного превью без сервера (~30 МБ бандла — решить осознанно).
- D3: Кэш STL в IndexedDB по хэшу кода (экономия при переключении вкладок).
- D4: RiskLight: +баллы, если `scad_code` присутствует, а `features=[]` (риск пропуска сверления → недооценка) с подсказкой «добавьте @feature-тег».
- D5: ~~Апгрейд OpenSCAD до Manifold-ядра~~ **РЕАЛИЗОВАН 2026-11-03 по измерению**:
  CGAL 2021.01 рендерил типовую деталь (60 отверстий, $fn=96) 228 с → таймауты у
  реальных кодов. `download_openscad.ps1` перев_pin на снапшот `2026.11.01` с
  files.openscad.org (`backend/vendor/openscad-2026.11.01/`); `scad_compiler`
  детектит версию (≥2024) и подставляет `--backend=Manifold` — та же деталь
  1.0–2.1 с (×100+); таймаут поднят 15 → 60 с. Резолвер предпочитает новейший
  vendor-каталог; 2021.01 остаётся фолбэком.

- D6/D7/D8: **Подсветка граней, зависящих от ползунка (ОТЛОЖЕНО; согласовано
  2026-11-03, старт — по отдельной команде).** Ограничение, из которого исходить:
  STL не несёт связи «грань ↔ переменная», связка строится на клиенте.

  - **D6 — hover-подсветка через манифест генератора (~0.5–1 день; режим
    SCAD_CUSTOMIZER).** `generateScadFromStore` дополнительно возвращает
    манифест: `interface ScadRegion { variable: string; kind: "cylinder_side" |
    "box" | "hole_wall"; origin: [number,number,number]; axis: "x"|"y"|"z";
    radius?: number; zRange?: [number,number]; box?: [number,number,number] }`.
    Регионы известны генератору уже сейчас (zExpr ступеней, boltR, grid-позиции):
    `od_n/ol_n` → боковая стенка ступени n, `id_n/il_n` → стенка расточки,
    `d_out/h_part/d_bore` → соответствующие поверхности T3, `p_l/p_w/p_h` →
    грани бокса T4/T5, `removal` → окна T5. На `onMouseEnter` ползунка
    (`param.name` уже извлекается `scadCustomizer`) Viewport25d выбирает грани
    по эвристике «центроид грани в регионе» (радиус ±0.5 мм, диапазон по оси)
    и рисует оверлей-геометрию (полупрозрачный emissive, смещение по нормали
    против z-fighting, убрать на mouseLeave). Мгновенно, без компиляции.
  - **D7 — точная подсветка «что изменилось» через diff сеток (~1–2 дня; любой
    режим, включая RAW).** В стор добавить `scadStlPrev` (предыдущий base64);
    при обновлении превью: BVH по старой геометрии (`three-mesh-bvh` — уже в
    дереве через three-bvh-csg), для каждой вершины новой —
    `closestPointToPoint` → смещение; грань изменена, если любая из 3 вершин
    сдвинулась > max(0.05 мм, 1e-4·диагональ bbox). Подсветка вспышкой
    (~1.5 с затухание). STL от STLLoader неиндексированный → per-face отбор
    тривиален; на сетках >400k треугольников диф считать, но подсветку
    ограничить порогом граней (иначе перегруз draw-call'ов).
  - **D8 — предиктивная подсветка до драга для RAW-кода (~2–3 дня; опционально,
    только если D6+D7 мало).** `POST /scad/preview {scad_code, probe: {var,
    delta}}` → сервер компилирует текущий и пробный варианты, считает
    симметричную разность (manifold3d), возвращает маску граней текущей сетки;
    кэш на (code_hash, var). ×2 компиляции на hover → лениво, только после
    первого наведения, с дебаунсом.

  Критерии приёмки D6/D7: hover ползунка ступени подсвечивает только её
  поверхность (<5% посторонних граней на шаблонах T1–T5); drag `d_bore` в RAW
  подсвечивает стенки расточки; TEMPLATE-режим и бэкенд не затрагиваются;
  eslint/build green. Файлы: `scadGenerator.ts` (манифест), `Viewport25d.tsx`
  (hover/diff/оверлей), `stores/constructor.ts` (`scadStlPrev`), D8 —
  `scad_compiler.py`/`scad.py`. Известные ограничения: D6 — эвристика (перекрытия
  регионов дают ложные срабатывания), D7 — подсветка после факта изменения,
  не предсказание.

## 4. Риски и откаты

| Риск | Митиг/откат |
|------|------------|
| OpenSCAD-код пользователя вешает компиляцию | timeout 15 c + поток через to_thread; 422 «превышено время» |
| Недооценка сверления в RAW-коде без фич | D4-эвристика + видимый бейдж «переходы не распознаны» |
| Разъезд v_net сетки и аналитики для одного шаблона | Тест A9 сверяет в пределах 0.5%; v_gross всегда аналитический |
| Взлом/мусор в сохранённых quotes | Поле проходит pydantic-валидацию (длина, строка); перекомпиляция на сервере изолирована temp-dir |
| Нет бинарника на стендe | capability-флаг: фронт прячет SCAD-режимы, расчёт TEMPLATE работает |
| Всё вместе | `APP_OPENSCAD_ENABLED=false` — полное выключение за один флаг; изменения аддитивны |

## 5. Чек-лист приёмки

- [x] `backend/scripts/download_openscad.ps1` отработал на чистой машине (vendor-каталог
      поднят, `openscad.com --version` = pinned-версии).
- [x] Все прежние 47 тестов green; запрос без `scad_code` → ответ побитово прежний
      (итог прогона Фазы A: 64 passed = 47 прежних + 17 новых; ruff/black/mypy green).
- [x] `POST /scad/preview` компилирует пример из материала (первая компиляция
      CGAL-ядра 2021.01 ≈ 3.5 с на difference цилиндров — ускорение = D5/Manifold;
      повтор из LRU-кэша 12 мс < 50 мс).
- [x] Расчёт с `scad_code`: v_net из сетки (отклонение от аналитики 0.07% < 0.5%),
      v_gross равен аналитике тех же габаритов (тест `test_calculate_with_scad_gross_matches_template_mode`).
- [x] Лестница тиражей компилирует SCAD один раз (тест `test_ladder_compiles_scad_once`:
      LRU miss == 1 на 7 прогонов движка).
- [x] TEMPLATE-режим фронтенда визуально неизменен (ветка PartMesh/three-bvh-csg
      не тронута; persist v2 + migrate: старые черновики поднимаются, STL-кэш
      не персистится).
- [x] Старые сохранённые КП открываются (scad_code опционален в DTO); новые
      SCAD-КП сохраняются/открываются/печатаются (тест `test_scad_quote_snapshot_roundtrip`;
      блок «Модель OpenSCAD» в печатном КП).
- [x] ruff, black, mypy strict, eslint (0 ошибок), `npm run build` — green
      (2026-11-03: backend 65 passed = 47 прежних + 18 новых).

Реализационные заметки по итогам (отличия от буквы плана — сохраняют контракты):
- Таймаут компиляции: `Popen` + stderr в файл + `taskkill /T /F` (дерево) —
  `subprocess.run(timeout=)` на Windows зависает: потомки держат pipe-дескрипторы.
- Capability — отдельный публичный `GET /scad/capability` (не `/health`):
  тест health фиксирует точный ответ `{"status": "ok"}`.
- Недоступность бинарника: расчёт → 422 с текстом, превью → 503; kill-switch
  `APP_OPENSCAD_ENABLED=false` — тихий фолбэк расчёта на TEMPLATE-аналитику.
- Persist-стор: version 2 + migrate; кэш превью (base64 STL) не персистится.
- Авто-подбор шаблона: семейство операций + осевая расточка → T2
  (`autoTemplateFromScad` на общем детекторе `scadFeatureExtractor`).

Оценка effort: Фаза A ≈ 1–1.5 дня, B ≈ 1–1.5 дня, C ≈ 1 день, D — по желанию.
