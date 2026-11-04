"use client";

import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { AnaloguePanel } from "@/components/constructor/AnaloguePanel";
import { CooperationPicker } from "@/components/constructor/CooperationPicker";
import { CostBreakdown } from "@/components/constructor/CostBreakdown";
import { FeatureTree } from "@/components/constructor/FeatureTree";
import { SaveQuote } from "@/components/constructor/SaveQuote";
import { TemplateForm } from "@/components/constructor/TemplateForm";
import { Label } from "@/components/ui/label";
import { ApiError, apiFetch } from "@/lib/api";
import { autoTemplateFromScad } from "@/lib/scadGenerator";
import type {
  BatchPrice,
  CalculateFeature,
  CalculateRequest,
  CalculationResult,
  MaterialInput,
} from "@/lib/constructor-types";
import type { CooperationService, Material } from "@/lib/types";
import { useAuthStore } from "@/stores/auth";
import { useConstructorStore } from "@/stores/constructor";

const Viewport25d = dynamic(
  () => import("@/components/constructor/Viewport25d"),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full items-center justify-center text-sm text-zinc-400">
        Загрузка 3D…
      </div>
    ),
  },
);

const ALLOWED_ROLES = ["MANAGER", "TECHNOLOGIST", "ADMIN"];

function materialToInput(material: Material): MaterialInput {
  return {
    iso_group: material.iso_group,
    k_mach_rough: material.machinability_factor,
    k_mach_finish: material.k_mach_finish ?? material.machinability_factor,
    density_g_cm3: material.density_g_cm3,
    cost_per_kg: material.cost_per_kg,
    scrap_price_per_kg: material.scrap_price_per_kg,
    tool_wear: material.tool_wear ?? "1.00",
  };
}

export default function ConstructorPage() {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  const hydrated = useAuthStore((s) => s.hydrated);
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  const templateType = useConstructorStore((s) => s.templateType);
  const t1 = useConstructorStore((s) => s.t1);
  const t2 = useConstructorStore((s) => s.t2);
  const t3 = useConstructorStore((s) => s.t3);
  const t4 = useConstructorStore((s) => s.t4);
  const t5 = useConstructorStore((s) => s.t5);
  const features = useConstructorStore((s) => s.features);
  const mode = useConstructorStore((s) => s.mode);
  const scadCode = useConstructorStore((s) => s.scadCode);
  const scadMeta = useConstructorStore((s) => s.scadMeta);
  const materialId = useConstructorStore((s) => s.materialId);
  const setMaterialId = useConstructorStore((s) => s.setMaterialId);
  const batchSize = useConstructorStore((s) => s.batchSize);
  const setBatchSize = useConstructorStore((s) => s.setBatchSize);
  const marginPercent = useConstructorStore((s) => s.marginPercent);
  const specialToolCost = useConstructorStore((s) => s.specialToolCost);
  const setSpecialToolCost = useConstructorStore((s) => s.setSpecialToolCost);
  const setMarginPercent = useConstructorStore((s) => s.setMarginPercent);
  const cooperationSelections = useConstructorStore(
    (s) => s.cooperationSelections,
  );

  const [materials, setMaterials] = useState<Material[]>([]);
  const [cooperationServices, setCooperationServices] = useState<
    CooperationService[]
  >([]);
  const [result, setResult] = useState<CalculationResult | null>(null);
  const [ladder, setLadder] = useState<BatchPrice[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const seq = useRef(0);

  useEffect(() => {
    if (!hydrated) return;
    if (!token) {
      router.replace("/login?next=/constructor");
      return;
    }
    if (user && !ALLOWED_ROLES.includes(user.role)) {
      router.replace("/materials");
    }
  }, [hydrated, token, user, router]);

  useEffect(() => {
    if (!token) return;
    apiFetch<Material[]>("/materials", token)
      .then(setMaterials)
      .catch(() => setMaterials([]));
    apiFetch<CooperationService[]>("/cooperation-services", token)
      .then(setCooperationServices)
      .catch(() => setCooperationServices([]));
  }, [token]);

  const material = materials.find((m) => m.id === materialId) ?? null;

  // SCAD-режим: код в запрос + base_template из bbox превью (v_gross —
  // аналитический). До успешного превью — фолбэк на TEMPLATE-аналитику.
  const scadActive =
    mode !== "TEMPLATE" && scadCode.trim().length > 0 && scadMeta !== null;

  const request = useMemo<CalculateRequest | null>(() => {
    if (!material) return null;
    const dimensions =
      templateType === "T1_STEPPED_SHAFT"
        ? t1
        : templateType === "T2_BUSHING"
          ? t2
          : templateType === "T3_FLANGE"
            ? t3
            : templateType === "T5_HOUSING"
              ? t5
              : t4;
    const activeFeatures: CalculateFeature[] = features
      .filter((feature) => feature.enabled)
      .map((feature) => {
        const { id: _id, enabled: _enabled, ...rest } = feature;
        return rest;
      });
    const baseTemplate = scadActive
      ? autoTemplateFromScad(templateType, scadCode, scadMeta?.bbox_mm ?? null, {
          t1,
          t2,
          t3,
          t4,
          t5,
        })
      : { type: templateType, dimensions };
    return {
      project_id: crypto.randomUUID(),
      batch_size: batchSize,
      material: materialToInput(material),
      base_template: baseTemplate,
      features: activeFeatures,
      margin_percent: marginPercent,
      special_tool_cost: specialToolCost || "0.00",
      cooperation: Object.entries(cooperationSelections).map(
        ([serviceId, qty]) => ({
          service_id: Number(serviceId),
          qty_override: qty === "" ? null : qty,
        }),
      ),
      ...(scadActive ? { scad_code: scadCode } : {}),
    };
  }, [
    material,
    templateType,
    t1,
    t2,
    t3,
    t4,
    t5,
    features,
    batchSize,
    marginPercent,
    specialToolCost,
    cooperationSelections,
    scadActive,
    scadCode,
    scadMeta,
  ]);

  const requestKey = request ? JSON.stringify(request) : "";

  useEffect(() => {
    if (!request || !token) return;
    const current = ++seq.current;
    const timer = setTimeout(() => {
      setLoading(true);
      Promise.all([
        apiFetch<CalculationResult>("/calculate/25d-feature", token, {
          method: "POST",
          body: request,
        }),
        apiFetch<BatchPrice[]>("/calculate/25d-feature/ladder", token, {
          method: "POST",
          body: request,
        }).catch(() => [] as BatchPrice[]),
      ])
        .then(([calc, ladderRows]) => {
          if (seq.current !== current) return;
          setResult(calc);
          setLadder(ladderRows);
          setError(null);
        })
        .catch((err: unknown) => {
          if (seq.current !== current) return;
          setResult(null);
          setLadder([]);
          setError(
            err instanceof ApiError
              ? err.message
              : "Ошибка расчёта, проверьте параметры",
          );
        })
        .finally(() => {
          if (seq.current === current) setLoading(false);
        });
    }, 400);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestKey, token]);

  return (
    <div className="flex min-h-screen flex-col bg-zinc-50">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-[1600px] items-center justify-between px-6 py-4">
          <h1 className="text-lg font-semibold">2.5D-конструктор расчёта</h1>
          <div className="flex items-center gap-3 text-sm text-zinc-600">
            <a href="/quotes" className="rounded-md border px-3 py-1.5 hover:bg-zinc-100">
              Расчёты
            </a>
            <span>
              {user?.email} · {user?.role}
            </span>
            <button
              type="button"
              className="rounded-md border px-3 py-1.5 hover:bg-zinc-100"
              onClick={() => {
                logout();
                router.replace("/login?next=/constructor");
              }}
            >
              Выйти
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto grid w-full max-w-[1600px] flex-1 grid-cols-1 gap-4 p-4 lg:grid-cols-[30%_45%_25%]">
        <div className="flex min-h-[420px] flex-col overflow-hidden rounded-xl border bg-white lg:h-[calc(100vh-120px)]">
          <div className="flex-1">
            <Viewport25d />
          </div>
          <p className="border-t px-3 py-2 text-xs text-zinc-400">
            Предпросмотр: расположение фич приблизительное (важны количество,
            диаметр и глубина)
          </p>
        </div>

        <div className="space-y-4 overflow-y-auto lg:h-[calc(100vh-120px)] lg:pr-1">
          <TemplateForm />
          <FeatureTree />
          <section className="space-y-3 rounded-xl border bg-white p-4">
            <h2 className="font-semibold">Кооперация</h2>
            <CooperationPicker services={cooperationServices} />
          </section>
          <section className="space-y-3 rounded-xl border bg-white p-4">
            <h2 className="font-semibold">Аналоги</h2>
            <AnaloguePanel request={request} token={token} />
          </section>
        </div>

        <div className="space-y-4 overflow-y-auto lg:h-[calc(100vh-120px)]">
          <section className="space-y-3 rounded-xl border bg-white p-4">
            <h2 className="font-semibold">Параметры расчёта</h2>
            <div className="space-y-1">
              <Label className="text-xs text-zinc-500">Материал</Label>
              <select
                value={materialId ?? ""}
                onChange={(event) =>
                  setMaterialId(
                    event.target.value === "" ? null : Number(event.target.value),
                  )
                }
                className="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm"
              >
                <option value="">— выберите материал —</option>
                {materials.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.grade} ({m.iso_group})
                  </option>
                ))}
              </select>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <Label className="text-xs text-zinc-500">Партия, шт</Label>
                <input
                  type="number"
                  min={1}
                  value={batchSize}
                  onChange={(event) =>
                    setBatchSize(Math.max(1, Number(event.target.value) || 1))
                  }
                  className="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-zinc-500">Маржа, %</Label>
                <input
                  type="number"
                  min={0}
                  step={0.5}
                  value={marginPercent}
                  onChange={(event) => setMarginPercent(event.target.value)}
                  className="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-zinc-500">Спец-инстр., ₽</Label>
                <input
                  type="number"
                  min={0}
                  step={10}
                  title="Уникальный специнструмент: 100% стоимости на партию"
                  value={specialToolCost}
                  onChange={(event) =>
                    setSpecialToolCost(event.target.value || "0")
                  }
                  className="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm"
                />
              </div>
            </div>
          </section>
          <CostBreakdown
            result={result}
            loading={loading}
            error={error}
            ladder={ladder}
            batchSize={batchSize}
            request={request}
          />
          <SaveQuote request={request} materialId={materialId} />
        </div>
      </main>
    </div>
  );
}
