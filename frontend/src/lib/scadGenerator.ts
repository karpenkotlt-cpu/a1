/**
 * Генератор SCAD-кода из состояния конструктора.
 *
 * Обязан отражать ПОЛНЫЕ шаблоны проекта (как lib/geometry25d.ts):
 * T1 steps, T2 outer_steps+inner_steps (расточка), T3 центральное
 * отверстие, T5 окна по removal_ratio, фичи HOLE_ARRAY/RECT_POCKET —
 * иначе превью и v_net перестанут соответствовать аналитике.
 *
 * Переменные снабжаются кастомайзер-комментариями OpenSCAD
 * (`// [min:step:max] Русский лейбл`) — из них строятся ползунки.
 */

import type {
  CalculateRequest,
  ConstructorFeature,
  T1Dimensions,
  T2Dimensions,
  T3Dimensions,
  T4Dimensions,
  T5Dimensions,
  TemplateType,
} from "@/lib/constructor-types";
import { detectCentralBore, detectOperationFamily, extractCentralBore } from "@/lib/scadFeatureExtractor";

const FN = 72;

export interface ScadGeneratorInput {
  templateType: TemplateType;
  t1: T1Dimensions;
  t2: T2Dimensions;
  t3: T3Dimensions;
  t4: T4Dimensions;
  t5: T5Dimensions;
  features: ConstructorFeature[];
}

function num(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}

/**
 * Хелперы позиционирования: болтовая окружность и сетка.
 * В OpenSCAD значения возвращают только function — module с вектором
 * как оператором (`[x, y];`) даёт Parser error, поэтому здесь функции.
 */
function holeHelpers(): string[] {
  return [
    "function circle_pos(count, i, radius) =",
    "  [radius * cos(360 * i / count), radius * sin(360 * i / count)];",
    "function grid_pos(count, i, span_a, span_b) =",
    "  let (cols = ceil(sqrt(count)), rows = ceil(count / cols),",
    "      col = i % cols, row = floor(i / cols))",
    "  [",
    "    cols == 1 ? 0 : (col - (cols - 1) / 2) * (span_a / cols),",
    "    rows == 1 ? 0 : (row - (rows - 1) / 2) * (span_b / rows)",
    "  ];",
  ];
}

type BaseTemplate = CalculateRequest["base_template"];

/**
 * Авто-подбор base_template для SCAD-режима: габариты — из bbox превью,
 * чтобы v_gross считался аналитически (припуски geometry.py), маршрут —
 * по группе операций кода (токарная/фрезерная). Расточка на оси → T2,
 * иначе INNER_OPERATION не попадёт в маршрут. Нет превью — текущий
 * шаблон как есть (фолбэк-аналитика).
 */
export function autoTemplateFromScad(
  templateType: TemplateType,
  scadCode: string,
  bbox: number[] | null,
  current: {
    t1: T1Dimensions;
    t2: T2Dimensions;
    t3: T3Dimensions;
    t4: T4Dimensions;
    t5: T5Dimensions;
  },
): BaseTemplate {
  const pick = (): BaseTemplate => {
    switch (templateType) {
      case "T1_STEPPED_SHAFT":
        return { type: templateType, dimensions: current.t1 };
      case "T2_BUSHING":
        return { type: templateType, dimensions: current.t2 };
      case "T3_FLANGE":
        return { type: templateType, dimensions: current.t3 };
      case "T4_PLATE":
        return { type: templateType, dimensions: current.t4 };
      default:
        return { type: templateType, dimensions: current.t5 };
    }
  };
  if (
    !bbox ||
    bbox.length !== 3 ||
    bbox.some((v) => !Number.isFinite(v) || v <= 0)
  ) {
    return pick();
  }
  const [x, y, z] = bbox;
  const family = detectOperationFamily(scadCode);
  if (family === "TURNING") {
    const d = Math.max(x, y);
    const bore = extractCentralBore(scadCode);
    if (bore) {
      // Расточка с литеральными размерами: T2 с реальной расточкой
      // из кода — INNER_OPERATION получает корректную a_inner
      return {
        type: "T2_BUSHING",
        dimensions: {
          outer_steps: [{ diameter: round(d), length: round(z) }],
          inner_steps: [
            {
              diameter: round(Math.min(bore.diameter, d)),
              length: round(Math.min(bore.length, z)),
            },
          ],
        },
      };
    }
    if (detectCentralBore(scadCode)) {
      // Расточка есть, но размеры — выражения/переменные:
      // T2, размеры расточки — из формы шаблона
      return {
        type: "T2_BUSHING",
        dimensions: {
          outer_steps: [{ diameter: round(d), length: round(z) }],
          inner_steps: current.t2.inner_steps,
        },
      };
    }
    if (z <= d / 3) {
      return {
        type: "T3_FLANGE",
        dimensions: {
          outer_diameter: round(d),
          thickness: round(z),
          center_hole_diameter: 0,
        },
      };
    }
    return {
      type: "T1_STEPPED_SHAFT",
      dimensions: { steps: [{ diameter: round(d), length: round(z) }] },
    };
  }
  if (family === "PRISMATIC") {
    return {
      type: "T4_PLATE",
      dimensions: { length: round(x), width: round(y), height: round(z) },
    };
  }
  return pick();
}

function round(value: number): number {
  return Math.round(value * 10) / 10;
}

/** Основной генератор: возвращает код с переменными кастомайзера. */
export function generateScadFromStore(input: ScadGeneratorInput): string {
  const { templateType } = input;
  const features = input.features.filter((f) => f.enabled);

  if (templateType === "T4_PLATE") {
    return plateScad(input.t4, features, "Плита (T4)", false);
  }
  if (templateType === "T5_HOUSING") {
    return housingScad(input.t5, features);
  }
  if (templateType === "T1_STEPPED_SHAFT") {
    return shaftScad(input.t1, features);
  }
  if (templateType === "T2_BUSHING") {
    return bushingScad(input.t2, features);
  }
  return flangeScad(input.t3, features);
}

function shaftScad(dims: T1Dimensions, features: ConstructorFeature[]): string {
  const head: string[] = [
    "// Вал ступенчатый (T1) — сгенерировано конструктором",
    `$fn = ${FN};`,
  ];
  const body: string[] = [];
  let zExpr = "0";
  dims.steps.forEach((step, i) => {
    const n = i + 1;
    head.push(
      `d${n} = ${num(step.diameter)}; // [5:1:500] Диаметр ступени ${n}, мм`,
      `l${n} = ${num(step.length)}; // [1:1:2000] Длина ступени ${n}, мм`,
    );
    body.push(`    translate([0, 0, ${zExpr}]) cylinder(h = l${n}, d = d${n});`);
    zExpr = i === 0 ? "l1" : `${zExpr} + l${n}`;
  });
  const totalL = dims.steps.reduce((acc, s) => acc + s.length, 0);
  const holes = turningHoles(features, Math.max(...dims.steps.map((s) => s.diameter)), totalL, 0);
  return [
    ...head,
    "",
    ...holeHelpers(),
    "difference() {",
    "  union() {",
    ...body,
    "  }",
    ...(holes.length ? ["  // Фичи: сверление с верхнего торца", ...holes] : []),
    "}",
  ].join("\n");
}

function bushingScad(dims: T2Dimensions, features: ConstructorFeature[]): string {
  const head: string[] = [
    "// Втулка (T2): наружные ступени + расточка — сгенерировано конструктором",
    `$fn = ${FN};`,
  ];
  const outer: string[] = [];
  const inner: string[] = [];
  let zOut = "0";
  dims.outer_steps.forEach((step, i) => {
    const n = i + 1;
    head.push(
      `od${n} = ${num(step.diameter)}; // [5:1:500] Наружный диаметр ступени ${n}, мм`,
      `ol${n} = ${num(step.length)}; // [1:1:1000] Длина ступени ${n}, мм`,
    );
    outer.push(`    translate([0, 0, ${zOut}]) cylinder(h = ol${n}, d = od${n});`);
    zOut = i === 0 ? "ol1" : `${zOut} + ol${n}`;
  });
  let zIn = "0";
  dims.inner_steps.forEach((step, i) => {
    const n = i + 1;
    head.push(
      `id${n} = ${num(step.diameter)}; // [2:1:500] Диаметр расточки ${n}, мм`,
      `il${n} = ${num(step.length)}; // [1:1:1000] Длина расточки ${n}, мм`,
    );
    inner.push(`  translate([0, 0, ${zIn} - 1]) cylinder(h = il${n} + 2, d = id${n});`);
    zIn = i === 0 ? "il1" : `${zIn} + il${n}`;
  });
  const totalL = dims.outer_steps.reduce((acc, s) => acc + s.length, 0);
  const dMax = Math.max(...dims.outer_steps.map((s) => s.diameter));
  const boreR = dims.inner_steps.length ? dims.inner_steps[0].diameter / 2 : 0;
  const holes = turningHoles(features, dMax, totalL, boreR);
  return [
    ...head,
    "",
    ...holeHelpers(),
    "difference() {",
    "  union() {",
    ...outer,
    "  }",
    ...(inner.length ? ["  // Центральная расточка (T2 → TURN_CNC_INT)", ...inner] : []),
    ...(holes.length ? ["  // Фичи: сверление", ...holes] : []),
    "}",
  ].join("\n");
}

function flangeScad(dims: T3Dimensions, features: ConstructorFeature[]): string {
  const head = [
    "// Фланец (T3) — сгенерировано конструктором",
    `$fn = ${FN};`,
    `d_out = ${num(dims.outer_diameter)}; // [20:1:800] Наружный диаметр, мм`,
    `h_part = ${num(dims.thickness)}; // [2:1:300] Толщина, мм`,
    `d_bore = ${num(dims.center_hole_diameter)}; // [0:1:600] Центральное отверстие, мм`,
  ];
  const boreR = dims.center_hole_diameter / 2;
  const holes = turningHoles(features, dims.outer_diameter, dims.thickness, boreR);
  return [
    ...head,
    "",
    ...holeHelpers(),
    "difference() {",
    "  cylinder(h = h_part, d = d_out);",
    ...(dims.center_hole_diameter > 0
      ? ["  // Центральное отверстие", "  translate([0, 0, -1]) cylinder(h = h_part + 2, d = d_bore);"]
      : []),
    ...(holes.length ? ["  // Фичи: сверление", ...holes] : []),
    "}",
  ].join("\n");
}

function plateScad(
  dims: T4Dimensions,
  features: ConstructorFeature[],
  title: string,
  withWindows: boolean,
): string {
  const head = [
    `// ${title} — сгенерировано конструктором`,
    `$fn = ${FN};`,
    `p_l = ${num(dims.length)}; // [10:5:1000] Длина, мм`,
    `p_w = ${num(dims.width)}; // [10:5:1000] Ширина, мм`,
    `p_h = ${num(dims.height)}; // [2:1:500] Высота, мм`,
  ];
  const cutters = prismaticCutters(features, dims.length, dims.width, dims.height);
  void withWindows;
  return [
    ...head,
    "",
    ...holeHelpers(),
    "difference() {",
    "  translate([-p_l / 2, -p_w / 2, 0]) cube([p_l, p_w, p_h]);",
    ...(cutters.length ? ["  // Фичи", ...cutters] : []),
    "}",
  ].join("\n");
}

function housingScad(dims: T5Dimensions, features: ConstructorFeature[]): string {
  // Число окон — та же логика, что в geometry25d.buildPreview
  const windows = dims.removal_ratio < 0.35 ? 1 : dims.removal_ratio < 0.7 ? 2 : 3;
  const wl = dims.length * 0.35;
  const ww = dims.width * 0.35;
  const head = [
    "// Корпус (T5): окна по removal_ratio — сгенерировано конструктором",
    `$fn = ${FN};`,
    `p_l = ${num(dims.length)}; // [10:5:1000] Длина, мм`,
    `p_w = ${num(dims.width)}; // [10:5:1000] Ширина, мм`,
    `p_h = ${num(dims.height)}; // [5:1:500] Высота, мм`,
    `removal = ${dims.removal_ratio.toFixed(2)}; // [0.05:0.05:0.95] Доля удаления материала`,
  ];
  const cutters: string[] = ["  // Сквозные окна сверху (как в TEMPLATE-превью)"];
  for (let i = 0; i < windows; i += 1) {
    const x = (i - (windows - 1) / 2) * (dims.length * 0.45);
    cutters.push(
      `  translate([${num(x)}, 0, -1]) cube([${num(wl)}, ${num(ww)}, p_h + 2]);`,
    );
  }
  const feats = prismaticCutters(features, dims.length, dims.width, dims.height);
  return [
    ...head,
    "",
    ...holeHelpers(),
    "difference() {",
    "  translate([-p_l / 2, -p_w / 2, 0]) cube([p_l, p_w, p_h]);",
    ...cutters,
    ...(feats.length ? ["  // Фичи", ...feats] : []),
    "}",
  ].join("\n");
}

/**
 * Отверстия тел вращения: болтовая окружность, вход с верхнего торца.
 * Радиус — как в geometry25d: (Rнар + Rраст)/2 при расточке, иначе 0.65·R.
 */
function turningHoles(
  features: ConstructorFeature[],
  outerDiameter: number,
  totalLength: number,
  boreRadius: number,
): string[] {
  const lines: string[] = [];
  const outerR = outerDiameter / 2;
  const boltR = boreRadius > 0 ? (outerR + boreRadius) / 2 : outerR * 0.65;
  for (const feature of features) {
    if (feature.type !== "HOLE_ARRAY") continue;
    if (feature.is_through) {
      lines.push(
        `  for (i = [0 : ${feature.count} - 1])`,
        `    let (p = circle_pos(${feature.count}, i, ${num(boltR)}))`,
        `      translate([p[0], p[1], -1])`,
        `        cylinder(h = ${num(totalLength + 2)}, d = ${num(feature.diameter)}, $fn = 48);`,
      );
    } else {
      lines.push(
        `  for (i = [0 : ${feature.count} - 1])`,
        `    let (p = circle_pos(${feature.count}, i, ${num(boltR)}))`,
        `      translate([p[0], p[1], ${num(totalLength - feature.depth)}])`,
        `        cylinder(h = ${num(feature.depth + 1)}, d = ${num(feature.diameter)}, $fn = 48);`,
      );
    }
    if (feature.counterbore_diameter && feature.counterbore_depth) {
      lines.push(
        `  for (i = [0 : ${feature.count} - 1])`,
        `    let (p = circle_pos(${feature.count}, i, ${num(boltR)}))`,
        `      translate([p[0], p[1], ${num(totalLength - feature.counterbore_depth)}])`,
        `        cylinder(h = ${num(feature.counterbore_depth + 1)}, d = ${num(feature.counterbore_diameter)}, $fn = 48);`,
      );
    }
  }
  return lines;
}

/** Фичи призматических тел: сетка отверстий/карманов с верхней плоскости. */
function prismaticCutters(
  features: ConstructorFeature[],
  length: number,
  width: number,
  height: number,
): string[] {
  const lines: string[] = [];
  for (const feature of features) {
    if (feature.type === "HOLE_ARRAY") {
      if (feature.is_through) {
        lines.push(
          `  for (i = [0 : ${feature.count} - 1])`,
          `    let (p = grid_pos(${feature.count}, i, ${num(length * 0.7)}, ${num(width * 0.7)}))`,
          `      translate([p[0], p[1], -1])`,
          `        cylinder(h = ${num(height + 2)}, d = ${num(feature.diameter)}, $fn = 48);`,
        );
      } else {
        lines.push(
          `  for (i = [0 : ${feature.count} - 1])`,
          `    let (p = grid_pos(${feature.count}, i, ${num(length * 0.7)}, ${num(width * 0.7)}))`,
          `      translate([p[0], p[1], ${num(height - feature.depth)}])`,
          `        cylinder(h = ${num(feature.depth + 1)}, d = ${num(feature.diameter)}, $fn = 48);`,
        );
      }
      if (feature.counterbore_diameter && feature.counterbore_depth) {
        lines.push(
          `  for (i = [0 : ${feature.count} - 1])`,
          `    let (p = grid_pos(${feature.count}, i, ${num(length * 0.7)}, ${num(width * 0.7)}))`,
          `      translate([p[0], p[1], ${num(height - feature.counterbore_depth)}])`,
          `        cylinder(h = ${num(feature.counterbore_depth + 1)}, d = ${num(feature.counterbore_diameter)}, $fn = 48);`,
        );
      }
    } else {
      lines.push(
        `  for (i = [0 : ${feature.count} - 1])`,
        `    let (p = grid_pos(${feature.count}, i, ${num(length * 0.7)}, 0))`,
        `      translate([p[0], 0, ${num(height - feature.depth)}])`,
        `        cube([${num(feature.length)}, ${num(feature.width)}, ${num(feature.depth + 1)}]);`,
      );
    }
  }
  return lines;
}
