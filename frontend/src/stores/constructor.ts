"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import type {
  CalculateRequest,
  ConstructorFeature,
  ConstructorMode,
  ScadPreviewMeta,
  T1Dimensions,
  T2Dimensions,
  T3Dimensions,
  T4Dimensions,
  T5Dimensions,
  TemplateType,
} from "@/lib/constructor-types";

/** Выбранные услуги кооперации: service_id → кол-во ("" = авто по единице). */
export type CooperationSelections = Record<number, string>;

interface ConstructorState {
  templateType: TemplateType;
  t1: T1Dimensions;
  t2: T2Dimensions;
  t3: T3Dimensions;
  t4: T4Dimensions;
  t5: T5Dimensions;
  features: ConstructorFeature[];
  materialId: number | null;
  batchSize: number;
  marginPercent: string;
  specialToolCost: string;
  cooperationSelections: CooperationSelections;
  mode: ConstructorMode;
  scadCode: string;
  /** Кэш последнего превью (не персистится: STL тяжёлый). */
  scadStl: string | null;
  scadMeta: ScadPreviewMeta | null;
  scadError: string | null;
  setTemplateType: (templateType: TemplateType) => void;
  setT1: (t1: T1Dimensions) => void;
  setT2: (t2: T2Dimensions) => void;
  setT3: (t3: T3Dimensions) => void;
  setT4: (t4: T4Dimensions) => void;
  setT5: (t5: T5Dimensions) => void;
  addFeature: (feature: ConstructorFeature) => void;
  updateFeature: (id: string, patch: Partial<ConstructorFeature>) => void;
  removeFeature: (id: string) => void;
  setMaterialId: (materialId: number | null) => void;
  setBatchSize: (batchSize: number) => void;
  setMarginPercent: (marginPercent: string) => void;
  setSpecialToolCost: (specialToolCost: string) => void;
  toggleCooperation: (serviceId: number) => void;
  setCooperationQty: (serviceId: number, qty: string) => void;
  setMode: (mode: ConstructorMode) => void;
  setScadCode: (scadCode: string) => void;
  setScadPreview: (stlBase64: string, meta: ScadPreviewMeta) => void;
  setScadError: (error: string | null) => void;
  resetScadMode: () => void;
  hydrateFromRequest: (
    request: CalculateRequest,
    materialId: number | null,
  ) => void;
}

const DOCX_T2: T2Dimensions = {
  outer_steps: [
    { diameter: 160, length: 20 },
    { diameter: 100, length: 60 },
  ],
  inner_steps: [
    { diameter: 72, length: 35 },
    { diameter: 60, length: 45 },
  ],
};

/** Персистим только данные черновика; кэш превью — в памяти сессии. */
type ConstructorPersisted = Pick<
  ConstructorState,
  | "templateType"
  | "t1"
  | "t2"
  | "t3"
  | "t4"
  | "t5"
  | "features"
  | "materialId"
  | "batchSize"
  | "marginPercent"
  | "specialToolCost"
  | "cooperationSelections"
  | "mode"
  | "scadCode"
>;

export const useConstructorStore = create<ConstructorState>()(
  persist<ConstructorState, [], [], ConstructorPersisted>(
    (set) => ({
      templateType: "T2_BUSHING",
      t1: { steps: [{ diameter: 50, length: 100 }] },
      t2: DOCX_T2,
      t3: { outer_diameter: 200, thickness: 30, center_hole_diameter: 60 },
      t4: { length: 200, width: 100, height: 40 },
      t5: { length: 200, width: 100, height: 60, removal_ratio: 0.6 },
      features: [
        {
          type: "HOLE_ARRAY",
          id: "docx-holes-flange",
          enabled: true,
          count: 6,
          diameter: 11,
          depth: 20,
          is_through: true,
          tolerance: "IT11",
          thread: null,
          counterbore_diameter: null,
          counterbore_depth: null,
          drill_type: "CARBIDE",
        },
        {
          type: "HOLE_ARRAY",
          id: "docx-holes-cover",
          enabled: true,
          count: 4,
          diameter: 6,
          depth: 15,
          is_through: false,
          tolerance: "IT7",
          thread: "M6",
          counterbore_diameter: null,
          counterbore_depth: null,
          drill_type: "CARBIDE",
        },
      ],
      materialId: null,
      batchSize: 20,
      marginPercent: "35.00",
      specialToolCost: "0.00",
      cooperationSelections: {},
      mode: "TEMPLATE",
      scadCode: "",
      scadStl: null,
      scadMeta: null,
      scadError: null,
      setTemplateType: (templateType) => set({ templateType }),
      setT1: (t1) => set({ t1 }),
      setT2: (t2) => set({ t2 }),
      setT3: (t3) => set({ t3 }),
      setT4: (t4) => set({ t4 }),
      setT5: (t5) => set({ t5 }),
      addFeature: (feature) =>
        set((state) => ({ features: [...state.features, feature] })),
      updateFeature: (id, patch) =>
        set((state) => ({
          features: state.features.map((feature) =>
            feature.id === id ? ({ ...feature, ...patch } as ConstructorFeature) : feature,
          ),
        })),
      removeFeature: (id) =>
        set((state) => ({
          features: state.features.filter((feature) => feature.id !== id),
        })),
      setMaterialId: (materialId) => set({ materialId }),
      setBatchSize: (batchSize) => set({ batchSize }),
      setMarginPercent: (marginPercent) => set({ marginPercent }),
      setSpecialToolCost: (specialToolCost) => set({ specialToolCost }),
      toggleCooperation: (serviceId) =>
        set((state) => {
          const next = { ...state.cooperationSelections };
          if (serviceId in next) {
            delete next[serviceId];
          } else {
            next[serviceId] = "";
          }
          return { cooperationSelections: next };
        }),
      setCooperationQty: (serviceId, qty) =>
        set((state) => ({
          cooperationSelections: {
            ...state.cooperationSelections,
            [serviceId]: qty,
          },
        })),
      setMode: (mode) => set({ mode }),
      setScadCode: (scadCode) => set({ scadCode }),
      setScadPreview: (stlBase64, meta) =>
        set({ scadStl: stlBase64, scadMeta: meta, scadError: null }),
      setScadError: (scadError) => set({ scadError }),
      resetScadMode: () =>
        set({
          mode: "TEMPLATE",
          scadCode: "",
          scadStl: null,
          scadMeta: null,
          scadError: null,
        }),
      hydrateFromRequest: (request, materialId) => {
        const templateType = request.base_template.type;
        const dimensions = request.base_template.dimensions;
        set((state) => ({
          templateType,
          t1: templateType === "T1_STEPPED_SHAFT"
            ? (dimensions as T1Dimensions)
            : state.t1,
          t2: templateType === "T2_BUSHING"
            ? (dimensions as T2Dimensions)
            : state.t2,
          t3: templateType === "T3_FLANGE"
            ? (dimensions as T3Dimensions)
            : state.t3,
          t4: templateType === "T4_PLATE"
            ? (dimensions as T4Dimensions)
            : state.t4,
          t5: templateType === "T5_HOUSING"
            ? (dimensions as T5Dimensions)
            : state.t5,
          features: request.features.map(
            (feature) =>
              ({
                ...feature,
                id: crypto.randomUUID(),
                enabled: true,
              }) as ConstructorFeature,
          ),
          materialId,
          batchSize: request.batch_size,
          marginPercent: request.margin_percent,
          specialToolCost: request.special_tool_cost ?? "0.00",
          cooperationSelections: Object.fromEntries(
            (request.cooperation ?? []).map((line) => [
              line.service_id,
              line.qty_override ?? "",
            ]),
          ),
          // Сохранённое SCAD-КП открывается в режиме кода
          mode: request.scad_code ? "SCAD_RAW_CODE" : "TEMPLATE",
          scadCode: request.scad_code ?? "",
          scadStl: null,
          scadMeta: null,
          scadError: null,
        }));
      },
    }),
    {
      name: "qcs-constructor",
      version: 2,
      skipHydration: true,
      partialize: (state): ConstructorPersisted => ({
        templateType: state.templateType,
        t1: state.t1,
        t2: state.t2,
        t3: state.t3,
        t4: state.t4,
        t5: state.t5,
        features: state.features,
        materialId: state.materialId,
        batchSize: state.batchSize,
        marginPercent: state.marginPercent,
        specialToolCost: state.specialToolCost,
        cooperationSelections: state.cooperationSelections,
        mode: state.mode,
        scadCode: state.scadCode,
      }),
      migrate: (persisted) => {
        // Черновики v1 (без SCAD-полей) поднимаются с дефолтами
        const draft = (persisted ?? {}) as Partial<ConstructorPersisted>;
        return {
          ...draft,
          mode: draft.mode ?? "TEMPLATE",
          scadCode: draft.scadCode ?? "",
        } as ConstructorPersisted;
      },
    },
  ),
);
