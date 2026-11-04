export type Role = "MANAGER" | "TECHNOLOGIST" | "ADMIN";

import type { CalculateRequest, CalculationResult } from "@/lib/constructor-types";

export interface Quote {
  id: number;
  name: string;
  project_id: string;
  batch_size: number;
  material_id: number | null;
  price_per_part: string;
  batch_total_price: string;
  author_email: string;
  created_at: string;
}

export interface QuoteDetail extends Quote {
  request: CalculateRequest;
  result: CalculationResult;
}

export interface ToolBasket {
  id: number;
  operation_group: string;
  material_iso_group: string;
  tool_set_cost: string;
  tool_life_min: string;
  regrindable: boolean;
  diameter_from_mm: string | null;
  diameter_to_mm: string | null;
}

export interface OperationRate {
  id: number;
  material_iso_group: string;
  q_rough_cm3_min: string;
  s_finish_dm2_min: string;
}

export interface OperationRow {
  id: number;
  code: string;
  name: string;
  operation_type: string;
  work_center_group: string;
  min_tool_diameter_mm: string | null;
  setup_time_base_min: string;
  rates: OperationRate[];
}

export interface WorkCenterRow {
  id: number;
  code: string;
  name: string;
  machine_type: string;
  group_code: string;
  is_active: boolean;
  machine_rate_per_min: string | null;
  operator_rate_per_hour: string | null;
}

export interface CoefficientRow {
  id: number;
  coef_type: string;
  code: string;
  multiplier: string;
  description: string | null;
}

export interface AuxiliaryOperation {
  id: number;
  code: string;
  name: string;
  fixed_time_min: string;
  rate_per_min: string;
  is_active: boolean;
}

export interface DrillingRate {
  id: number;
  diameter_from_mm: string;
  diameter_to_mm: string;
  carbide_feed_mm_min: string;
  hss_feed_mm_min: string;
}

export interface AnalogueRow {
  quote_id: number;
  name: string;
  batch_size: number;
  price_per_part: string;
  author_email: string;
  created_at: string;
  deviation_percent: number;
}

export interface CapacityLoadRow {
  id: number;
  work_center_group: string;
  horizon_days: number;
  total_fund_minutes: string;
  scheduled_minutes: string;
  utilization_percent: number | null;
}

export const SERVICE_TYPE_TITLES: Record<string, string> = {
  HEAT_TREATMENT: "Термообработка",
  GALVANIZING: "Гальваника",
  ANODIZING: "Анодирование",
  LASER_CUT: "Лазерная резка",
  PAINTING: "Окраска",
};

export const UNIT_TITLES: Record<string, string> = {
  KG: "за кг",
  DM2: "за дм²",
  METER: "за пог. м",
  PIECE: "за шт",
};

export interface CooperationService {
  id: number;
  service_type: string;
  unit: string;
  price_per_unit: string;
  contractor: string | null;
  min_lot_qty: string;
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
}

export interface Material {
  id: number;
  grade: string;
  gost: string | null;
  iso_group: string;
  density_g_cm3: string;
  machinability_factor: string;
  cost_per_kg: string;
  scrap_price_per_kg: string;
  k_mach_finish: string | null;
  tool_wear: string | null;
}
