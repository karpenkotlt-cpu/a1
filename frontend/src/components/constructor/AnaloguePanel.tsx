"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import type {
  CalculateRequest,
  T1Dimensions,
  T2Dimensions,
  T3Dimensions,
  T4Dimensions,
} from "@/lib/constructor-types";
import { ApiError, apiFetch } from "@/lib/api";
import type { AnalogueRow } from "@/lib/types";

/** Зеркало _bbox_mm бэкенда: токарные → (Ømax, L), коробки → (L, W, H). */
function buildQuery(request: CalculateRequest) {
  const { type, dimensions } = request.base_template;
  if (type === "T4_PLATE" || type === "T5_HOUSING") {
    const dims = dimensions as T4Dimensions; // T4 и T5 одинаковы по габариту
    return {
      template_type: type,
      iso_group: request.material.iso_group,
      length_mm: dims.length,
      width_mm: dims.width,
      height_mm: dims.height,
    };
  }
  if (type === "T3_FLANGE") {
    const dims = dimensions as T3Dimensions;
    return {
      template_type: type,
      iso_group: request.material.iso_group,
      d_max_mm: dims.outer_diameter,
      length_mm: dims.thickness,
    };
  }
  // dimensions — неразличимый union, сужаем вручную по типу шаблона.
  const steps =
    type === "T2_BUSHING"
      ? (dimensions as T2Dimensions).outer_steps
      : (dimensions as T1Dimensions).steps;
  return {
    template_type: type,
    iso_group: request.material.iso_group,
    d_max_mm: Math.max(...steps.map((s) => s.diameter)),
    length_mm: steps.reduce((sum, s) => sum + s.length, 0),
  };
}

export function AnaloguePanel({
  request,
  token,
}: {
  request: CalculateRequest | null;
  token: string | null;
}) {
  const [rows, setRows] = useState<AnalogueRow[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch() {
    if (!request || !token) return;
    setLoading(true);
    setError(null);
    try {
      setRows(
        await apiFetch<AnalogueRow[]>("/quotes/similar", token, {
          method: "POST",
          body: buildQuery(request),
        }),
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ошибка поиска");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-2">
      <p className="text-xs text-zinc-400">
        Поиск сохранённых КП с тем же шаблоном, материалом и габаритом
        (отклонение ≤ 35% по любой оси) — быстрая оценка «по аналогу».
      </p>
      <Button
        variant="outline"
        size="sm"
        disabled={!request || loading}
        onClick={() => void handleSearch()}
      >
        {loading ? "Поиск…" : "Найти аналоги"}
      </Button>
      {error && <p className="text-xs text-red-600">{error}</p>}
      {rows !== null && (
        <div className="space-y-1">
          {rows.length === 0 && (
            <p className="text-xs text-zinc-500">Аналоги не найдены</p>
          )}
          {rows.map((row) => (
            <div
              key={row.quote_id}
              className="flex items-baseline justify-between gap-2 text-xs"
            >
              <span className="min-w-0 truncate text-zinc-700">{row.name}</span>
              <span className="shrink-0 tabular-nums text-zinc-500">
                {row.batch_size} шт · {row.price_per_part} ₽ · Δ{" "}
                {row.deviation_percent}%
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
