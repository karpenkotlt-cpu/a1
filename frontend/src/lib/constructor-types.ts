export type TemplateType =
  | "T1_STEPPED_SHAFT"
  | "T2_BUSHING"
  | "T3_FLANGE"
  | "T4_PLATE"
  | "T5_HOUSING";

/** Режим конструктора: шаблонные ползунки либо код OpenSCAD. */
export type ConstructorMode =
  | "TEMPLATE"
  | "SCAD_CUSTOMIZER"
  | "SCAD_RAW_CODE";

export interface Step {
  diameter: number;
  length: number;
}

export interface T1Dimensions {
  steps: Step[];
}

export interface T2Dimensions {
  outer_steps: Step[];
  inner_steps: Step[];
}

export interface T3Dimensions {
  outer_diameter: number;
  thickness: number;
  center_hole_diameter: number;
}

export interface T4Dimensions {
  length: number;
  width: number;
  height: number;
}

export interface T5Dimensions {
  length: number;
  width: number;
  height: number;
  removal_ratio: number;
}

export interface HoleArrayFeature {
  type: "HOLE_ARRAY";
  id: string;
  enabled: boolean;
  count: number;
  diameter: number;
  depth: number;
  is_through: boolean;
  tolerance: string;
  thread: string | null;
  counterbore_diameter: number | null;
  counterbore_depth: number | null;
  drill_type: "CARBIDE" | "HSS";
}

export interface RectPocketFeature {
  type: "RECT_POCKET";
  id: string;
  enabled: boolean;
  count: number;
  length: number;
  width: number;
  depth: number;
  tool_diameter: number;
  tolerance: string;
}

export type ConstructorFeature = HoleArrayFeature | RectPocketFeature;

export type CalculateFeature =
  | Omit<HoleArrayFeature, "id" | "enabled">
  | Omit<RectPocketFeature, "id" | "enabled">;

export interface MaterialInput {
  iso_group: string;
  k_mach_rough: string;
  k_mach_finish: string;
  density_g_cm3: string;
  cost_per_kg: string;
  scrap_price_per_kg: string;
  tool_wear: string;
}

export interface CooperationLine {
  service_id: number;
  qty_override: string | null;
}

export interface CalculateRequest {
  project_id: string;
  batch_size: number;
  material: MaterialInput;
  base_template: {
    type: TemplateType;
    dimensions:
      | T1Dimensions
      | T2Dimensions
      | T3Dimensions
      | T4Dimensions
      | T5Dimensions;
  };
  features: CalculateFeature[];
  margin_percent: string;
  special_tool_cost: string;
  cooperation?: CooperationLine[];
  /** Код OpenSCAD: геометрия расчёта берётся из STL-сетки (backend). */
  scad_code?: string;
}

export interface ScadPreviewMeta {
  bbox_mm: number[];
  v_net_cm3: number;
  compile_ms: number;
}

export interface OperationBreakdown {
  code: string;
  name: string;
  machine_time_min: number;
  setup_time_min: number;
  machine_rate_per_min: string;
  cost: string;
  tool_cost?: string;
}

export interface CooperationBreakdown {
  name: string;
  unit: string;
  qty: string;
  unit_price: string;
  cost: string;
}

export interface BatchPrice {
  batch_size: number;
  price_per_part: string;
  batch_total_price: string;
}

export interface CalculationResult {
  v_net_cm3: number;
  v_gross_cm3: number;
  v_removed_cm3: number;
  m_net_kg: number;
  m_gross_kg: number;
  material_cost: string;
  machine_time_min: number;
  setup_time_min: number;
  price_per_part: string;
  batch_total_price: string;
  tool_cost?: string;
  cooperation_cost?: string;
  operations?: OperationBreakdown[];
  cooperations?: CooperationBreakdown[];
  margin_multiplier?: number;
  capacity_utilization_percent?: number | null;
  bottleneck_group?: string | null;
  floor_price_per_part?: string | null;
}

export const TOLERANCE_OPTIONS = [
  "IT12-14",
  "IT10-11",
  "IT8-9",
  "IT7",
  "IT6",
] as const;
