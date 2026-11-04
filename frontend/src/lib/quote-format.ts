import type {
  CalculateRequest,
  Step,
  T1Dimensions,
  T2Dimensions,
  T3Dimensions,
  T4Dimensions,
  T5Dimensions,
  TemplateType,
} from "@/lib/constructor-types";

export const TEMPLATE_TITLES: Record<TemplateType, string> = {
  T1_STEPPED_SHAFT: "Вал ступенчатый (T1)",
  T2_BUSHING: "Втулка / стакан (T2)",
  T3_FLANGE: "Фланец / диск (T3)",
  T4_PLATE: "Плита / блок (T4)",
  T5_HOUSING: "Корпус (T5)",
};

export function formatMoney(value: string | number): string {
  const num = typeof value === "string" ? Number.parseFloat(value) : value;
  if (Number.isNaN(num)) return String(value);
  return num.toLocaleString("ru-RU", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function formatDate(iso: string): string {
  const date = new Date(iso);
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${pad(date.getDate())}.${pad(date.getMonth() + 1)}.${date.getFullYear()} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function stepsText(steps: Step[]): string {
  return steps.map((s) => `Ø${s.diameter}×${s.length}`).join(" + ");
}

/** Строки секции «Деталь»: шаблон + габариты (зеркало quote_export.py). */
export function templateRows(request: CalculateRequest): [string, string][] {
  const { type, dimensions } = request.base_template;
  const rows: [string, string][] = [
    ["Шаблон", TEMPLATE_TITLES[type] ?? type],
  ];
  // dimensions — неразличимый union, сужаем вручную по типу шаблона.
  if (type === "T1_STEPPED_SHAFT") {
    const dims = dimensions as T1Dimensions;
    rows.push(["Ступени, мм", stepsText(dims.steps)]);
  } else if (type === "T2_BUSHING") {
    const dims = dimensions as T2Dimensions;
    rows.push(["Наружные ступени, мм", stepsText(dims.outer_steps)]);
    if (dims.inner_steps.length > 0) {
      rows.push(["Расточка, мм", stepsText(dims.inner_steps)]);
    }
  } else if (type === "T3_FLANGE") {
    const dims = dimensions as T3Dimensions;
    rows.push([
      "Ø внешний × толщина, мм",
      `${dims.outer_diameter}×${dims.thickness}`,
    ]);
    rows.push(["Ø центральный, мм", String(dims.center_hole_diameter)]);
  } else if (type === "T5_HOUSING") {
    const dims = dimensions as T5Dimensions;
    rows.push([
      "Габариты, мм",
      `${dims.length}×${dims.width}×${dims.height}`,
    ]);
    rows.push(["Kвыб (доля в стружку)", String(dims.removal_ratio)]);
  } else {
    const dims = dimensions as T4Dimensions;
    rows.push([
      "Габариты, мм",
      `${dims.length}×${dims.width}×${dims.height}`,
    ]);
  }
  return rows;
}

/** Строки секции фич (зеркало quote_export.py). */
export function featureRows(request: CalculateRequest): [string, string][] {
  const rows: [string, string][] = [];
  for (const feature of request.features) {
    if (feature.type === "HOLE_ARRAY") {
      const through = feature.is_through ? "сквозные" : `гл. ${feature.depth}`;
      const cb =
        feature.counterbore_diameter && feature.counterbore_depth
          ? `, цек. Ø${feature.counterbore_diameter}×${feature.counterbore_depth}`
          : "";
      const thread = feature.thread ? `, ${feature.thread}` : "";
      rows.push([
        "Группа отверстий",
        `${feature.count}×Ø${feature.diameter} ${through} · ${feature.tolerance}${thread}${cb}`,
      ]);
    } else {
      rows.push([
        "Карман",
        `${feature.count}× ${feature.length}×${feature.width}×${feature.depth} · ${feature.tolerance}`,
      ]);
    }
  }
  return rows;
}
