файлы OpenSCAD: [https\://github.com/openscad/openscad/](https://github.com/openscad/openscad/)  
Описание OpenSCAD: [https\://openscad.org/news.html](https://openscad.org/news.html)

В текущей реализации у вас заложен отличный архитектурный принцип: **Zustand-стор является единым источником истины**, а вьюпорт (Viewport25d) и бэкенд-калькулятор (geometry.py \+ costing.py) работают параллельно от одного состояния.  
Однако сейчас вы уперлись в два ограничения:

> 1. На фронтенде three-bvh-csg \+ LatheGeometry хрупки (проблемы с нормалями ensureCcw, артефакты булевых операций при пересечении граней, невозможность легко собрать композитную деталь из нескольких примитивов или вставить произвольный .scad код).  
> 2. На бэкенде app/domain/engine/geometry.py считает объемы аналитическими формулами только для жестко зашитых шаблонов T1..T5. Если пользователь вставит свой код OpenSCAD или соберет кастомную форму, аналитические формулы T1..T5 не смогут её обсчитать.

Чтобы заменить three-bvh-csg на **OpenSCAD** с поддержкой **3 режимов** (Шаблоны T1..T5, Параметрический Customizer по переменным и Вставка готового .scad кода) и при этом **на 100% сохранить работу цепочки calculation\_service.py → costing.py (маршруты, сверление D16..D3, корзины инструментов и ставки)**, нужно применить паттерн **Двунаправленного SCAD-транслятора \+ Переопределения геометрии (GeometryOverride)**.

## **1\. Новая схема потока данных (Сохранение обратной совместимости)**

Мы не ломаем существующий контракт CalculateRequest, а расширяем его и переводим генерацию геометрии на связку **SCAD-скрипт \+ Парсер метаданных**:

Plaintext  
                       ┌─────────────────────────────────────────────────────────────┐  
                       │          Zustand Store: useConstructorStore                 │  
                       │  • mode: 'TEMPLATE' \| 'SCAD\_CUSTOMIZER' \| 'SCAD\_RAW\_CODE'   │  
                       │  • templateType (T1..T5) \+ t1..t5 \+ features\[\]              │  
                       │  • scadCode: string (синхронизируется в обе стороны\!)       │  
                       │  • customizerVars: ScadParam\[\] (парсятся из кода на лету)   │  
                       └──────────────┬───────────────────────────────┬──────────────┘  
                                      │                               │  
           1\. Компиляция STL (WASM в WebWorker                        │ 2\. Debounce 400 мс (CalculateRequest)  
              или быстрый эндпоинт /scad/preview)                     ▼  
                                      │               ┌──────────────────────────────┐  
                                      ▼               │ POST /calculate/25d-feature  │  
                       ┌────────────────────────────┐ │ POST /.../ladder             │  
                       │   Viewport25d (R3F Canvas) │ └───────────────┬──────────────┘  
                       │ • Вместо three-bvh-csg —   │                 │  
                       │   чистый BufferGeometry    │                 ▼  
                       │   из скомпилированного STL │ ┌──────────────────────────────┐  
                       │ • Поверх: EdgesGeometry(25)│ │ Backend: geometry.py         │  
                       │ • Bounds \+ Gizmo \+ Grid    │ │ • Если mode \== 'TEMPLATE':   │  
                       └────────────────────────────┘ │   считает аналитически ИЛИ   │  
                                                      │   через trimesh/manifold3d   │  
                                                      │ • Если 'SCAD\_\*': берет точные│  
                                                      │   V\_gross, V\_net, V\_rem, A   │  
                                                      │   из STL-сетки OpenSCAD, а   │  
                                                      │   отверстия — из features\[\]  │  
                                                      │   или парсера cylinder()\!    │  
                                                      └───────────────┬──────────────┘  
                                                                      ▼  
                                                      ┌──────────────────────────────┐  
                                                      │ costing.py (БЕЗ ИЗМЕНЕНИЙ\!)  │  
                                                      │ • TEMPLATE\_OPERATION         │  
                                                      │ • drilling\_bands (D16..D3)   │  
                                                      │ • tool\_baskets × K\_wear      │  
                                                      └──────────────────────────────┘

## **2\. Главный секрет: Как сохранить расчет сверления и инструментов при вставке произвольного кода OpenSCAD**

Ваша цепочка costing.py опирается на две вещи:

> 1. **Базовая операция (TEMPLATE\_OPERATION):** зависит от того, тело вращения перед нами (TURN\_CNC\_EXT / TURN\_CNC\_INT) или призматическая корпусная деталь (MILL\_CNC\_FACE).  
> 2. **Сверлильные переходы и корзины (drilling\_bands / tool\_baskets):** зависят от массива features\[\] (count, diameter, depth, is\_through, drill\_type).

Чтобы при вставке готового кода OpenSCAD калькулятор не «ослеп» и автоматически понял, какие сверла и операции применить, мы внедряем **Парсер технологических признаков OpenSCAD (scadFeatureExtractor.ts)**:

> 1. **Авто-определение типа базовой операции (Turning vs Milling):**  
   * Если в коде OpenSCAD корневым элементом идет rotate\_extrude() или cylinder() по центру — в стор автоматически ставится профиль токарной обработки (T1 или T2, если внутри вычитается сквозной цилиндр $\rightarrow$ подключается TURN\_CNC\_INT).  
   * Если в основе cube() или linear\_extrude() — выбирается фрезерная группа (T4 / T5 $\rightarrow$ MILL\_CNC\_FACE).  
> 2. **Авто-извлечение сверлильных переходов (HOLE\_ARRAY) прямо из текста .scad:** Когда пользователь вставляет чужой код OpenSCAD или крутит ползунки Customizer'а, регулярный анализатор находит внутри блока difference() { ... } вычитаемые цилиндры (cylinder(h=..., d=...) или r=...) и **автоматически пополняет массив features\[\] в вашем Zustand-сторе**\! Также поддерживаются специальные технологические теги в комментариях (стандарт OpenSCAD Customizer):  
>    OpenSCAD  
>    // Вставленный или сгенерированный код детали:  
>    d\_out \= 120; // \[20:1:300\] Наружный диаметр, мм  
>    d\_bore \= 50; // \[10:1:200\] Расточка, мм  
>    h\_part \= 45; // \[5:1:200\] Высота детали, мм  
>    hole\_d \= 12; // \[3:0.5:30\] Диаметр отв. (сверление), мм  
>    hole\_cnt \= 6; // \[1:1:24\] Число отверстий

>    difference() {  
>        cylinder(h \= h\_part, d \= d\_out, \$fn\=64);  
>        translate(\[0,0,-1\]) cylinder(h \= h\_part+2, d \= d\_bore, \$fn\=64);  
>        // @feature HOLE\_ARRAY count=hole\_cnt d=hole\_d depth=h\_part through=true drill=CARBIDE  
>        for (i \= \[0 : hole\_cnt-1\])  
>            rotate(\[0, 0, i \* 360 / hole\_cnt\])  
>                translate(\[42, 0, \-1\]) cylinder(h \= h\_part+2, d \= hole\_d, \$fn\=32);  
>    }

## **3\. Изменения по файлам проекта (Готовый код для внедрения)**

### **Файл 1: frontend/src/lib/scadGenerator.ts (Замена geometry25d.ts)**

Этот модуль заменяет buildPreview(spec) и ensureCcw(). Он делает две вещи:

> 1. Превращает ваши текущие шаблоны T1..T5 \+ features из стора в чистый, читаемый код OpenSCAD с поддержкой Customizer-переменных в шапке.  
> 2. Парсит любой вставленный пользователем .scad код: вытаскивает из него переменные для UI-ползунков (чтобы настраивать геометрию по чертежу без правки кода\!) и синхронизирует отверстия с массивом features для расчета сверл.

TypeScript  
// frontend/src/lib/scadGenerator.ts  
import { ConstructorState, FeatureSpec } from "./constructor-types";

export interface ScadCustomParam {  
  name: string;  
  value: number;  
  min?: number;  
  max?: number;  
  step?: number;  
  label: string;  
}

/\*\*  
 \* 1\. Генератор кода OpenSCAD из текущего состояния шаблонов T1..T5 и фич стора.  
 \* Полностью заменяет LatheGeometry / BoxGeometry / three-bvh-csg.  
 \*/  
export function generateScadFromStore(state: ConstructorState): string {  
  const enabledFeatures \= state.features.filter((f) \=\> f.enabled);  
  const lines: string\[\] \= \[  
    "// \=== ПАРАМЕТРЫ ДЕТАЛИ (OpenSCAD Customizer) \===",  
    "\$fn \= 72;",  
  \];

  let positiveBody \= "";  
  let totalHeight \= 50;

  switch (state.templateType) {  
    case "T1": {  
      // T1: Ступенчатый вал (аналог LatheGeometry по лестнице ступеней)  
      const steps \= state.t1.steps \|\| \[{ d: 60, l: 40 }, { d: 40, l: 50 }\];  
      steps.forEach((s, i) \=\> {  
        lines.push(\`step\_\${i \+ 1}\_d \= \${s.d}; // \[5:1:500\] Диаметр ступени \${i \+ 1}, мм\`);  
        lines.push(\`step\_\${i \+ 1}\_l \= \${s.l}; // \[5:1:1000\] Длина ступени \${i \+ 1}, мм\`);  
      });  
      totalHeight \= steps.reduce((acc, s) \=\> acc \+ s.l, 0);

      let zOffset \= 0;  
      const cyls \= steps.map((s, i) \=\> {  
        const line \= \`        translate(\[0, 0, \${zOffset}\]) cylinder(h \= step\_\${i \+ 1}\_l, d \= step\_\${i \+ 1}\_d);\`;  
        zOffset \+= s.l;  
        return line;  
      });  
      positiveBody \= \`    union() {\\n\${cyls.join("\\n")}\\n    }\`;  
      break;  
    }

    case "T2":  
    case "T3": {  
      // T2 Втулка / T3 Фланец (больше никаких проблем с ensureCcw\!)  
      const spec \= state.templateType \=== "T2" ? state.t2 : state.t3;  
      const dOut \= spec.d\_out \|\| 120;  
      const dIn \= spec.d\_in \|\| 50;  
      const length \= spec.length \|\| 60;  
      totalHeight \= length;

      lines.push(\`d\_out \= \${dOut}; // \[10:1:600\] Наружный диаметр, мм\`);  
      lines.push(\`d\_in \= \${dIn}; // \[0:1:500\] Внутренний диаметр (расточка), мм\`);  
      lines.push(\`length \= \${length}; // \[2:1:1000\] Длина детали, мм\`);

      if (state.templateType \=== "T3" && spec.d\_collar && spec.l\_collar) {  
        lines.push(\`d\_collar \= \${spec.d\_collar}; // \[10:1:500\] Диаметр бурта, мм\`);  
        lines.push(\`l\_collar \= \${spec.l\_collar}; // \[2:1:300\] Высота бурта, мм\`);  
        positiveBody \= \`    difference() {  
        union() {  
            cylinder(h \= length \- l\_collar, d \= d\_out);  
            translate(\[0, 0, length \- l\_collar\]) cylinder(h \= l\_collar, d \= d\_collar);  
        }  
        translate(\[0, 0, \-1\]) cylinder(h \= length \+ 2, d \= d\_in);  
    }\`;  
      } else {  
        positiveBody \= \`    difference() {  
        cylinder(h \= length, d \= d\_out);  
        if (d\_in \> 0\) translate(\[0, 0, \-1\]) cylinder(h \= length \+ 2, d \= d\_in);  
    }\`;  
      }  
      break;  
    }

    case "T4":  
    case "T5": {  
      // T4 Плита / T5 Корпус с окнами выборки  
      const spec \= state.templateType \=== "T4" ? state.t4 : state.t5;  
      const L \= spec.length \|\| 200;  
      const W \= spec.width \|\| 140;  
      const H \= spec.height \|\| 30;  
      totalHeight \= H;

      lines.push(\`plate\_L \= \${L}; // \[10:1:2000\] Длина плиты L, мм\`);  
      lines.push(\`plate\_W \= \${W}; // \[10:1:1500\] Ширина плиты W, мм\`);  
      lines.push(\`plate\_H \= \${H}; // \[2:1:500\] Высота H, мм\`);

      if (state.templateType \=== "T5") {  
        const remRatio \= state.t5.removal\_ratio ?? 0.4;  
        const wall \= Math.max(6, Math.round(Math.min(L, W) \* 0.08));  
        const pocketsCount \= remRatio \< 0.35 ? 1 : remRatio \< 0.7 ? 2 : 3;  
        lines.push(\`wall\_t \= \${wall}; // \[3:1:50\] Толщина стенки корпуса, мм\`);  
        lines.push(\`floor\_t \= \${Math.max(5, Math.round(H \* 0.2))}; // \[2:1:50\] Толщина дна, мм\`);

        positiveBody \= \`    difference() {  
        translate(\[-plate\_L/2, \-plate\_W/2, 0\]) cube(\[plate\_L, plate\_W, plate\_H\]);  
        // Окна выборки корпуса T5 (\${pocketsCount} шт.)  
        for (i \= \[0 : \${pocketsCount \- 1}\]) {  
            pocket\_l \= (plate\_L \- wall\_t \* (\${pocketsCount \+ 1})) / \${pocketsCount};  
            x\_pos \= \-plate\_L/2 \+ wall\_t \+ i \* (pocket\_l \+ wall\_t);  
            translate(\[x\_pos, \-plate\_W/2 \+ wall\_t, floor\_t\])  
                cube(\[pocket\_l, plate\_W \- 2\*wall\_t, plate\_H\]);  
        }  
    }\`;  
      } else {  
        positiveBody \= \`    translate(\[-plate\_L/2, \-plate\_W/2, 0\]) cube(\[plate\_L, plate\_W, plate\_H\]);\`;  
      }  
      break;  
    }  
  }

  // Генерация вычитаний фич (сверление с верхнего торца faceY \= totalHeight)  
  const cutterBlocks: string\[\] \= \[\];  
  enabledFeatures.forEach((f, idx) \=\> {  
    const pfx \= \`f\${idx \+ 1}\`;  
    lines.push(\`\${pfx}\_d \= \${f.diameter}; // \[1:0.5:200\] Фича \#\${idx \+ 1}: Диаметр, мм\`);  
    lines.push(\`\${pfx}\_depth \= \${f.depth}; // \[1:1:500\] Фича \#\${idx \+ 1}: Глубина, мм\`);  
    lines.push(\`\${pfx}\_count \= \${f.count}; // \[1:1:64\] Фича \#\${idx \+ 1}: Количество\`);

    const zStart \= f.is\_through ? "-1" : \`\${totalHeight} \- \${pfx}\_depth\`;  
    const cutH \= f.is\_through ? \`\${totalHeight \+ 2}\` : \`\${pfx}\_depth \+ 1\`;

    if (state.templateType \=== "T1" \|\| state.templateType \=== "T2" \|\| state.templateType \=== "T3") {  
      // Раскладка по делительной окружности (boltCircle)  
      const pcdRadius \= f.pcd ? f.pcd / 2 : 40;  
      cutterBlocks.push(\`        // @feature HOLE\_ARRAY id=\${f.id}  
        for (i \= \[0 : \${pfx}\_count \- 1\])  
            rotate(\[0, 0, i \* 360 / \${pfx}\_count\])  
                translate(\[\${pcdRadius}, 0, \${zStart}\])  
                    cylinder(h \= \${cutH}, d \= \${pfx}\_d);\`);  
    } else {  
      // Раскладка сеткой (grid) для плит T4/T5  
      cutterBlocks.push(\`        // @feature HOLE\_ARRAY id=\${f.id}  
        for (i \= \[0 : \${pfx}\_count \- 1\])  
            translate(\[ (i \- (\${pfx}\_count-1)/2) \* (\${pfx}\_d \* 2.2), 0, \${zStart} \])  
                cylinder(h \= \${cutH}, d \= \${pfx}\_d);\`);  
    }  
  });

  const fullCode \= \[  
    ...lines,  
    "",  
    "difference() {",  
    positiveBody,  
    cutterBlocks.length \> 0 ? \`    union() {\\n\${cutterBlocks.join("\\n")}\\n    }\` : "",  
    "}",  
  \].join("\\n");

  return fullCode;  
}

/\*\*  
 \* 2\. Парсер параметров OpenSCAD Customizer:  
 \* Ищет строки вида: \`var\_name \= 120; // \[10:1:500\] Описание параметра\`  
 \* и строит из них удобные поля ввода для менеджера\!  
 \*/  
export function extractCustomizerParams(scadCode: string): ScadCustomParam\[\] {  
  const regex \= /^(\[a-zA-Z0-9\_\]+)\\s\*=\\s\*(\[0-9.\]+)\\s\*;\\s\*(?:\\/\\/\\s\*(?:  
$$([0-9.]+):([0-9.]+):([0-9.]+)$$  
)?\\s\*(.\*))?\$/gm;  
  const params: ScadCustomParam\[\] \= \[\];  
  let match: RegExpExecArray \| null;

  while ((match \= regex.exec(scadCode)) \!== null) {  
    const \[, name, valStr, minStr, stepStr, maxStr, comment\] \= match;  
    if (name \=== "\$fn") continue;  
    params.push({  
      name,  
      value: parseFloat(valStr),  
      min: minStr ? parseFloat(minStr) : undefined,  
      step: stepStr ? parseFloat(stepStr) : 1,  
      max: maxStr ? parseFloat(maxStr) : undefined,  
      label: comment?.trim() \|\| name,  
    });  
  }  
  return params;  
}

/\*\*  
 \* 3\. Точечное обновление значения переменной внутри текста .scad кода,  
 \* когда менеджер меняет цифру в UI-инпуте Customizer'а.  
 \*/  
export function updateScadVariable(scadCode: string, varName: string, newValue: number): string {  
  const pattern \= new RegExp(\`^(\${varName}\\\\s\*=\\\\s\*)(\[0-9.\]+)(\\\\s\*;.\*)\$\`, "m");  
  return scadCode.replace(pattern, \`\$1\${newValue}\$3\`);  
}

### **Файл 2: Обновленный Viewport25d.tsx (Замена three-bvh-csg на OpenSCAD STL \+ те же Bounds, EdgesGeometry, Gizmo)**

Вьюпорт сохраняет всю вашу сцену (Bounds, EdgesGeometry(result, 25), Grid 10/50 мм, OrbitControls, GizmoHelper), но вместо глючного Evaluator.evaluate рендерит точную геометрию OpenSCAD и оснащен переключателем режимов (**«Настройка параметров»** / **«Код OpenSCAD»**):

TypeScript  
// frontend/src/components/constructor/Viewport25d.tsx  
import React, { useEffect, useMemo, useState } from "react";  
import { Canvas } from "@react-three/fiber";  
import { Bounds, Center, Edges, GizmoHelper, GizmoViewport, Grid, OrbitControls } from "@react-three/drei";  
import \* as THREE from "three";  
import { STLLoader } from "three-stdlib";  
import { useConstructorStore } from "@/store/constructor";  
import { extractCustomizerParams, updateScadVariable } from "@/lib/scadGenerator";

const PartMesh: React.FC\<{ stlBase64: string \| null }\> \= ({ stlBase64 }) \=\> {  
  const geometry \= useMemo(() \=\> {  
    if (\!stlBase64) return null;  
    const bin \= window.atob(stlBase64);  
    const bytes \= new Uint8Array(bin.length);  
    for (let i \= 0; i \< bin.length; i++) bytes\[i\] \= bin.charCodeAt(i);

    const loader \= new STLLoader();  
    const geom \= loader.parse(bytes.buffer);  
    geom.computeVertexNormals();  
    geom.center(); // Заменяет ваш centerAll() из geometry25d.ts\!  
    return geom;  
  }, \[stlBase64\]);

  if (\!geometry) return null;

  return (  
    \<Center\>  
      \<mesh geometry={geometry} rotation={\[-Math.PI / 2, 0, 0\]} castShadow receiveShadow\>  
        \<meshStandardMaterial color="\#64748b" metalness={0.45} roughness={0.35} /\>  
        {/\* Сохраняем вашу читаемость контуров через порог 25 градусов \*/}  
        \<Edges threshold={25} color="\#0f172a" /\>  
      \</mesh\>  
    \</Center\>  
  );  
};

export default function Viewport25d() {  
  // Подписка на единый стор (никаких пропсов, как и было в архитектуре)  
  const {  
    mode,  
    scadCode,  
    stlBase64,  
    scadMetrics,  
    setMode,  
    setScadCode,  
    syncFeaturesFromCustomScad,  
  } \= useConstructorStore();

  const \[showCodeDrawer, setShowCodeDrawer\] \= useState(false);

  // Автоматически парсим переменные из текущего кода для окна ввода параметров\!  
  const customParams \= useMemo(() \=\> extractCustomizerParams(scadCode), \[scadCode\]);

  const handleParamChange \= (varName: string, val: number) \=\> {  
    const updated \= updateScadVariable(scadCode, varName, val);  
    setScadCode(updated);  
    syncFeaturesFromCustomScad(updated);  
  };

  return (  
    \<div className="relative w-full h-full flex flex-col bg-slate-950 rounded-xl overflow-hidden border border-slate-800"\>  
      {/\* Верхний тулбар вьюпорта: переключение режимов OpenSCAD \*/}  
      \<div className="z-10 flex items-center justify-between px-3 py-2 bg-slate-900/90 border-b border-slate-800 text-xs"\>  
        \<div className="flex items-center gap-1.5"\>  
          \<button  
            onClick={() \=\> { setMode("TEMPLATE"); setShowCodeDrawer(false); }}  
            className={\`px-2.5 py-1 rounded font-medium \${  
              mode \=== "TEMPLATE" && \!showCodeDrawer ? "bg-blue-600 text-white" : "bg-slate-800 text-slate-300"  
            }\`}  
          \>  
            Шаблоны T1–T5  
          \</button\>  
          \<button  
            onClick={() \=\> { setMode("SCAD\_CUSTOM"); setShowCodeDrawer(false); }}  
            className={\`px-2.5 py-1 rounded font-medium \${  
              mode \=== "SCAD\_CUSTOM" && \!showCodeDrawer ? "bg-blue-600 text-white" : "bg-slate-800 text-slate-300"  
            }\`}  
          \>  
            Параметры модели ({customParams.length})  
          \</button\>  
          \<button  
            onClick={() \=\> { setMode("SCAD\_CUSTOM"); setShowCodeDrawer(\!showCodeDrawer); }}  
            className={\`px-2.5 py-1 rounded font-medium \${  
              showCodeDrawer ? "bg-amber-600 text-white" : "bg-slate-800 text-slate-300"  
            }\`}  
          \>  
            {showCodeDrawer ? "Скрыть код .scad" : "\</\> Вставить код OpenSCAD"}  
          \</button\>  
        \</div\>

        {scadMetrics && (  
          \<div className="text-\[11px\] text-slate-400 font-mono"\>  
            Габарит: \<b className="text-slate-200"\>{scadMetrics.bbox.join("×")} мм\</b\> \| Vчист:{" "}  
            \<b className="text-emerald-400"\>{scadMetrics.v\_net\_cm3} см³\</b\>  
          \</div\>  
        )}  
      \</div\>

      {/\* Основная область: Вьюпорт R3F \+ выдвижная панель параметров / кода \*/}  
      \<div className="relative flex-1 flex overflow-hidden"\>  
        {/\* 1\. Панель быстрого ввода параметров (если включен режим настройки модели по переменным) \*/}  
        {mode \=== "SCAD\_CUSTOM" && \!showCodeDrawer && customParams.length \> 0 && (  
          \<div className="w-64 bg-slate-900/95 border-r border-slate-800 p-3 overflow-y-auto space-y-2.5 z-10"\>  
            \<div className="text-\[11px\] font-bold uppercase text-blue-400 tracking-wider"\>  
              Настройка размеров по чертежу  
            \</div\>  
            {customParams.map((p) \=\> (  
              \<div key={p.name} className="space-y-1"\>  
                \<div className="flex justify-between text-xs"\>  
                  \<span className="text-slate-300 truncate" title={p.label}\>{p.label}\</span\>  
                  \<span className="font-mono text-blue-300"\>{p.value}\</span\>  
                \</div\>  
                \<div className="flex gap-1.5 items-center"\>  
                  {p.min \!== undefined && p.max \!== undefined && (  
                    \<input  
                      type="range"  
                      min={p.min}  
                      max={p.max}  
                      step={p.step \|\| 1}  
                      value={p.value}  
                      onChange={(e) \=\> handleParamChange(p.name, parseFloat(e.target.value))}  
                      className="flex-1 accent-blue-500 h-1 bg-slate-700 rounded-lg cursor-pointer"  
                    /\>  
                  )}  
                  \<input  
                    type="number"  
                    step={p.step \|\| 1}  
                    value={p.value}  
                    onChange={(e) \=\> handleParamChange(p.name, parseFloat(e.target.value) \|\| 0)}  
                    className="w-16 px-1.5 py-0.5 bg-slate-800 border border-slate-700 rounded text-xs font-mono text-right text-white"  
                  /\>  
                \</div\>  
              \</div\>  
            ))}  
          \</div\>  
        )}

        {/\* 2\. Выдвижной редактор для вставки готового кода детали OpenSCAD \*/}  
        {showCodeDrawer && (  
          \<div className="w-80 bg-slate-900/95 border-r border-slate-800 flex flex-col z-10"\>  
            \<div className="p-2 bg-slate-800/60 text-\[11px\] text-slate-300 flex justify-between items-center"\>  
              \<span\>Вставьте код OpenSCAD (переменные станут полями ввода):\</span\>  
            \</div\>  
            \<textarea  
              value={scadCode}  
              onChange={(e) \=\> {  
                setScadCode(e.target.value);  
                syncFeaturesFromCustomScad(e.target.value);  
              }}  
              spellCheck={false}  
              className="flex-1 w-full p-3 bg-slate-950 text-emerald-400 font-mono text-xs focus:outline-none resize-none"  
              placeholder="// Вставьте код OpenSCAD сюда..."  
            /\>  
          \</div\>  
        )}

        {/\* 3\. R3F Canvas (Сохранена вся оригинальная структура сцены\!) \*/}  
        \<div className="flex-1 h-full relative"\>  
          \<Canvas shadows camera={{ position: \[180, 140, 180\], fov: 45 }}\>  
            \<ambientLight intensity={0.65} /\>  
            \<directionalLight position={\[150, 250, 150\]} intensity={1.1} castShadow /\>  
            \<directionalLight position={\[-150, \-100, \-100\]} intensity={0.4} /\>

            \<Bounds fit clip observe margin={1.25}\>  
              \<PartMesh stlBase64={stlBase64} /\>  
            \</Bounds\>

            \<Grid  
              infiniteGrid  
              cellSize={10}  
              sectionSize={50}  
              fadeDistance={800}  
              cellColor="\#334155"  
              sectionColor="\#475569"  
            /\>  
            \<OrbitControls makeDefault /\>  
            \<GizmoHelper alignment="bottom-right" margin={\[60, 60\]}\>  
              \<GizmoViewport axisColors={\["\#ef4444", "\#22c55e", "\#3b82f6"\]} labelColor="white" /\>  
            \</GizmoHelper\>  
          \</Canvas\>  
        \</div\>  
      \</div\>  
    \</div\>  
  );  
}

### **Файл 3: Интеграция на Backend в app/domain/engine/geometry.py и calculation\_service.py**

На бэкенде мы добавляем в CalculateRequest необязательное поле scad\_code: Optional\[str\] \= None.

* Если scad\_code не передан (или режим TEMPLATE), ваш geometry.py считает всё как раньше, либо уточняет объемы через OpenSCAD/Trimesh.  
* Если пользователь модифицировал деталь через OpenSCAD или вставил свой код, функция compute\_geometry\_from\_scad() компилирует .scad через локальный бинарник openscad.com (или manifold3d), вычисляет **точные v\_gross, v\_net, v\_rem, a\_outer, a\_inner** и передает тот же самый объект GeometryResult дальше в ваш costing.py\!

Python  
\# app/domain/engine/scad\_geometry\_adapter.py  
import subprocess  
import sys  
import tempfile  
import base64  
import math  
from pathlib import Path  
import trimesh

\# Импортируйте ваш существующий датакласс результата геометрии из app/domain/engine/geometry.py  
from app.domain.engine.geometry import GeometryResult

def compile\_and\_measure\_scad(  
    scad\_code: str,  
    template\_type: str,  
    allowance\_mm: float \= 3.0  
) \-\> tuple\[GeometryResult, str\]:  
    """  
    Компилирует SCAD-код без Docker (через локальный openscad.com),  
    возвращает ваш стандартный GeometryResult для costing.py \+ base64 STL для Viewport25d.  
    """  
    with tempfile.TemporaryDirectory() as tmpdir:  
        tmp\_path \= Path(tmpdir)  
        scad\_file \= tmp\_path / "part.scad"  
        stl\_file \= tmp\_path / "part.stl"  
        scad\_file.write\_text(scad\_code, encoding="utf-8")

        \# Путь к portable-бинарнику в папке проекта или системном PATH  
        bin\_name \= "openscad.com" if sys.platform \== "win32" else "openscad"  
        cmd \= \[bin\_name, "--backend=Manifold", "--export-format", "binstl", "-o", str(stl\_file), str(scad\_file)\]  
        flags \= 0x08000000 if sys.platform \== "win32" else 0  \# CREATE\_NO\_WINDOW

        res \= subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=flags)  
        if res.returncode \!= 0 and b"unrecognized option" in res.stderr:  
            cmd.remove("--backend=Manifold")  
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=flags)

        mesh \= trimesh.load(stl\_file, file\_type="stl")  
        stl\_b64 \= base64.b64encode(stl\_file.read\_bytes()).decode("ascii")

    \# 1\. Габариты детали и расчет объема заготовки (V\_gross)  
    extents\_mm \= mesh.extents  \# \[X, Y, Z\]  
    if template\_type in ("T1", "T2", "T3"):  
        \# Для токарных деталей заготовка — кругляк (цилиндр вокруг максимального диаметра)  
        d\_max \= max(extents\_mm\[0\], extents\_mm\[1\]) \+ 2.0 \* allowance\_mm  
        l\_stock \= extents\_mm\[2\] \+ 2.0 \* allowance\_mm  
        v\_gross\_cm3 \= (math.pi \* (d\_max \*\* 2) / 4.0) \* l\_stock \* 1e-3  
        a\_outer\_dm2 \= (math.pi \* d\_max \* extents\_mm\[2\]) \* 1e-4  
    else:  
        \# Для фрезерных деталей T4/T5 заготовка — прямоугольная плита  
        lx \= extents\_mm\[0\] \+ 2.0 \* allowance\_mm  
        ly \= extents\_mm\[1\] \+ 2.0 \* allowance\_mm  
        lz \= extents\_mm\[2\] \+ 2.0 \* allowance\_mm  
        v\_gross\_cm3 \= (lx \* ly \* lz) \* 1e-3  
        a\_outer\_dm2 \= 2.0 \* (lx \* ly \+ lx \* lz \+ ly \* lz) \* 1e-4

    \# 2\. Чистый объем и объем удаляемой стружки прямо из сетки OpenSCAD  
    v\_net\_cm3 \= max(0.01, float(mesh.volume) \* 1e-3)  
    v\_rem\_cm3 \= max(0.0, v\_gross\_cm3 \- v\_net\_cm3)  
    total\_area\_dm2 \= float(mesh.area) \* 1e-4  
    a\_inner\_dm2 \= max(0.0, total\_area\_dm2 \- a\_outer\_dm2)

    \# 3\. Возвращаем ваш родной GeometryResult — costing.py даже не заметит подмены\!  
    geom\_result \= GeometryResult(  
        v\_gross=round(v\_gross\_cm3, 3),  
        v\_net=round(v\_net\_cm3, 3),  
        v\_rem=round(v\_rem\_cm3, 3),  
        a\_outer=round(a\_outer\_dm2, 3),  
        a\_inner=round(a\_inner\_dm2, 3),  
    )  
    return geom\_result, stl\_b64

### **Как подключается в calculation\_service.py (3 строчки кода):**

Python  
\# Внутри вашего метода расчета в calculation\_service.py:  
if request.scad\_code and request.mode \== "SCAD\_CUSTOM":  
    \# Считаем объемы и площади напрямую из модели OpenSCAD  
    geom, stl\_b64 \= compile\_and\_measure\_scad(  
        scad\_code=request.scad\_code,  
        template\_type=request.template\_type  
    )  
else:  
    \# Ваш существующий аналитический расчет из app/domain/engine/geometry.py  
    geom \= compute\_analytical\_geometry(request)  
    stl\_b64 \= None

\# Дальше идет ваш неизменный код costing.py:  
\# 1\. Выбор главной операции по TEMPLATE\_OPERATION (TURN\_CNC\_EXT / MILL\_CNC\_FACE / TURN\_CNC\_INT)  
\# 2\. Расчет сверления по request.features (drilling\_bands D16/D10/D5/D3 \+ CARBIDE/HSS)  
\# 3\. Подбор корзин tool\_baskets и умножение на K\_wear \* 1.05

## **4\. Что вы получаете в итоге при таком подходе**

> 1. **Никакой ломки существующего бэкенда:** Эндпоинты POST /calculate/25d-feature и POST /calculate/25d-feature/ladder, структура CostBreakdown, подбор сверл по диапазонам диаметров и расчет инструментальных корзин продолжают работать один в один.  
> 2. **Три способа работы в одном окне:**  
   * Менеджер может как раньше кликать по шаблонам T1..T5 и добавлять фичи в левой панели (а OpenSCAD строит идеальное 3D-превью без багов three-bvh-csg).  
   * Может переключиться на вкладку **«Параметры модели»** и крутить сгенерированные ползунки любых размеров.  
   * Технолог или продвинутый пользователь может нажать **\</\> Вставить код OpenSCAD**, вставить код сколь угодно сложной мульти-примитивной детали (с комментариями // \[min:step:max\]), и система мгновенно сгенерирует из этого кода **поля ввода для менеджера**, отрендерит деталь во Viewport25d и посчитает точную стоимость и маршрут.