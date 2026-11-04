"use client";

import type {
  CalculateRequest,
  CalculationResult,
} from "@/lib/constructor-types";

interface Segment {
  label: string;
  value: number;
  color: string;
  /** Доп. подпись: у маржи показываем и наценку, и долю в цене. */
  note?: string;
}

/**
 * Структура цены: сегменты себестоимости + маржа (docx: Live Cost
 * Breakdown). Диаграмма — CSS conic-gradient, без chart-зависимостей.
 */
export function PriceStructurePie({
  result,
  request,
}: {
  result: CalculationResult;
  request: CalculateRequest;
}) {
  const batch = request.batch_size;
  const segments: Segment[] = [
    {
      label: "Материал",
      value: parseFloat(result.material_cost),
      color: "#3b82f6",
    },
    {
      label: "Обработка",
      value: (result.operations ?? []).reduce(
        (sum, op) => sum + parseFloat(op.cost),
        0,
      ),
      color: "#a1a1aa",
    },
    {
      label: "Инструмент",
      value: parseFloat(result.tool_cost ?? "0"),
      color: "#f59e0b",
    },
  ];
  const coop = parseFloat(result.cooperation_cost ?? "0");
  if (coop > 0) {
    segments.push({ label: "Кооперация", value: coop, color: "#8b5cf6" });
  }
  const special = parseFloat(request.special_tool_cost || "0") / batch;
  if (special > 0) {
    segments.push({ label: "Спец-оснастка", value: special, color: "#ec4899" });
  }
  const production = segments.reduce((sum, s) => sum + s.value, 0);
  const margin = Math.max(parseFloat(result.price_per_part) - production, 0);
  // Движок применяет margin_percent как НАЦЕНКУ (price = cost·(1+k)),
  // а доля в круге — от ЦЕНЫ: наценка 20% ↔ маржа 0.2/1.2 ≈ 16.7%.
  // Показываем оба числа, чтобы не путать с введённой маржей.
  const markupPercent =
    production > 0 ? (margin / production) * 100 : 0;
  segments.push({
    label: "Маржа",
    value: margin,
    color: "#10b981",
    note: `наценка ${markupPercent.toFixed(1)}%`,
  });

  const total = segments.reduce((sum, s) => sum + s.value, 0);
  if (total <= 0) return null;

  let acc = 0;
  const stops = segments
    .filter((s) => s.value > 0)
    .map((s) => {
      const from = (acc / total) * 100;
      acc += s.value;
      const to = (acc / total) * 100;
      return `${s.color} ${from.toFixed(2)}% ${to.toFixed(2)}%`;
    });

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3">
        <div
          className="h-20 w-20 shrink-0 rounded-full"
          style={{ background: `conic-gradient(${stops.join(", ")})` }}
          role="img"
          aria-label="Структура цены"
        />
        <div className="min-w-0 flex-1 space-y-0.5">
          {segments
            .filter((s) => s.value > 0)
            .map((s) => (
              <div
                key={s.label}
                className="flex items-baseline justify-between gap-2 text-xs"
              >
                <span className="flex items-center gap-1.5 text-zinc-600">
                  <span
                    className="inline-block h-2 w-2 rounded-full"
                    style={{ background: s.color }}
                  />
                  {s.label}
                </span>
                <span className="tabular-nums text-zinc-800">
                  {s.value.toFixed(2)} ₽ ·{" "}
                  {s.note ? (
                    <span>
                      {s.note} / {((s.value / total) * 100).toFixed(0)}% цены
                    </span>
                  ) : (
                    <span>{((s.value / total) * 100).toFixed(0)}%</span>
                  )}
                </span>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}
