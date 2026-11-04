"use client";

import type {
  CalculateRequest,
  CalculationResult,
} from "@/lib/constructor-types";

interface RiskState {
  level: "green" | "yellow" | "red";
  reasons: string[];
}

/**
 * Экспресс-оценка риска КП (Контур А): маржа, жёсткие допуски,
 * экзотический материал, корпус с большим съёмом; при наличии результата —
 * ещё и цена ниже пола переменных издержек (демпинг).
 * 0 баллов — зелёный, 1-2 — жёлтый, 3+ — красный.
 */
export function assessRisk(
  request: CalculateRequest,
  result?: CalculationResult | null,
): RiskState {
  const reasons: string[] = [];
  let score = 0;

  const margin = parseFloat(request.margin_percent);
  if (margin < 15) {
    score += 2;
    reasons.push(`низкая маржа ${margin}%`);
  } else if (margin < 25) {
    score += 1;
    reasons.push(`маржа ${margin}%`);
  }

  const tolerances = request.features.map((f) => f.tolerance ?? "");
  if (tolerances.some((t) => t.startsWith("IT6"))) {
    score += 2;
    reasons.push("допуск IT6");
  } else if (tolerances.some((t) => t.startsWith("IT7"))) {
    score += 1;
    reasons.push("допуск IT7");
  }

  if (request.material.iso_group !== "P") {
    score += 1;
    reasons.push(`материал ISO ${request.material.iso_group}`);
  }

  if (
    request.base_template.type === "T5_HOUSING" &&
    "removal_ratio" in request.base_template.dimensions &&
    request.base_template.dimensions.removal_ratio > 0.7
  ) {
    score += 1;
    reasons.push("корпус: съём >70%");
  }

  if (
    result?.floor_price_per_part != null &&
    parseFloat(result.price_per_part) <
      parseFloat(result.floor_price_per_part)
  ) {
    score += 3;
    reasons.push("цена ниже пола издержек (демпинг)");
  }

  return { level: score >= 3 ? "red" : score >= 1 ? "yellow" : "green", reasons };
}

const LIGHTS: Record<RiskState["level"], { color: string; title: string }> = {
  green: { color: "#10b981", title: "Риск низкий" },
  yellow: { color: "#f59e0b", title: "Риск средний" },
  red: { color: "#ef4444", title: "Риск высокий" },
};

export function RiskLight({
  request,
  result,
}: {
  request: CalculateRequest;
  result?: CalculationResult | null;
}) {
  const { level, reasons } = assessRisk(request, result);
  const active = LIGHTS[level];
  return (
    <div className="flex items-center gap-2" title={reasons.join(", ")}>
      <span className="flex gap-1">
        {(["red", "yellow", "green"] as const).map((l) => (
          <span
            key={l}
            className="inline-block h-2.5 w-2.5 rounded-full"
            style={{
              background: l === level ? LIGHTS[l].color : "#e4e4e7",
              boxShadow: l === level ? `0 0 4px ${LIGHTS[l].color}` : undefined,
            }}
          />
        ))}
      </span>
      <span className="text-xs font-medium text-zinc-600">
        {active.title}
        {reasons.length > 0 && (
          <span className="font-normal text-zinc-400">: {reasons.join(", ")}</span>
        )}
      </span>
    </div>
  );
}
