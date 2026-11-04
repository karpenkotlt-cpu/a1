"use client";

import type {
  BatchPrice,
  CalculateRequest,
  CalculationResult,
} from "@/lib/constructor-types";
import { PriceStructurePie } from "@/components/constructor/PriceStructurePie";
import { RiskLight } from "@/components/constructor/RiskLight";

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-2 text-sm">
      <span className="text-zinc-500">{label}</span>
      <span className="font-medium tabular-nums">{value}</span>
    </div>
  );
}

export function CostBreakdown({
  result,
  loading,
  error,
  ladder,
  batchSize,
  request,
}: {
  result: CalculationResult | null;
  loading: boolean;
  error: string | null;
  ladder: BatchPrice[];
  batchSize: number;
  request: CalculateRequest | null;
}) {
  return (
    <section className="space-y-3 rounded-xl border bg-white p-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">Стоимость</h2>
        {loading && <span className="text-xs text-zinc-400">пересчёт…</span>}
      </div>
      {request && <RiskLight request={request} result={result} />}
      {error && (
        <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          {error}
        </p>
      )}
      {!result && !error && (
        <p className="text-sm text-zinc-500">
          Выберите материал — расчёт обновляется автоматически при любом
          изменении.
        </p>
      )}
      {result && (
        <div className="space-y-2">
          <div className="rounded-lg bg-zinc-900 p-3 text-white">
            <div className="text-xs text-zinc-400">Цена за деталь</div>
            <div className="text-2xl font-semibold tabular-nums">
              {result.price_per_part} ₽
            </div>
          </div>
          <Row
            label="Партия (итого)"
            value={`${result.batch_total_price} ₽`}
          />
          {result.floor_price_per_part != null && (
            <Row
              label="Пол цены (переменные)"
              value={`${result.floor_price_per_part} ₽`}
            />
          )}
          {result.floor_price_per_part != null &&
            parseFloat(result.price_per_part) <
              parseFloat(result.floor_price_per_part) && (
              <p className="rounded-md bg-red-50 px-2 py-1 text-xs text-red-700">
                Цена ниже пола переменных издержек (демпинг) — согласуйте
                пересмотр условий
              </p>
            )}
          {result.margin_multiplier !== undefined &&
            result.margin_multiplier !== 1 && (
              <p className="rounded-md bg-amber-50 px-2 py-1 text-xs text-amber-700">
                Динамическая маржа: Kmargin ×{result.margin_multiplier} · загрузка
                {result.bottleneck_group ? ` ${result.bottleneck_group}` : " группы"}{" "}
                {result.capacity_utilization_percent?.toFixed(1) ?? "?"}% (APS)
              </p>
            )}
          {request && (
            <div className="py-1">
              <PriceStructurePie result={result} request={request} />
            </div>
          )}
          <div className="my-2 border-t" />
          <Row label="Чистая масса" value={`${result.m_net_kg} кг`} />
          <Row label="Масса заготовки" value={`${result.m_gross_kg} кг`} />
          <Row label="Съём Vrem" value={`${result.v_removed_cm3} см³`} />
          <Row label="Материал" value={`${result.material_cost} ₽`} />
          {result.tool_cost && parseFloat(result.tool_cost) > 0 && (
            <Row label="Инструмент" value={`${result.tool_cost} ₽`} />
          )}
          {result.cooperation_cost &&
            parseFloat(result.cooperation_cost) > 0 && (
              <Row
                label="Кооперация"
                value={`${result.cooperation_cost} ₽`}
              />
            )}
          <Row
            label="Машинное время Tшт"
            value={`${result.machine_time_min} мин`}
          />
          <Row label="Наладка Tпз (на партию)" value={`${result.setup_time_min} мин`} />
          {result.operations && result.operations.length > 0 && (
            <div className="pt-1">
              <div className="mb-1 border-t" />
              <div className="mb-1 text-xs font-medium text-zinc-500">
                Маршрут обработки
              </div>
              {result.operations.map((operation) => (
                <div
                  key={operation.code}
                  className="flex items-baseline justify-between gap-2 py-0.5 text-xs"
                >
                  <span className="text-zinc-600">
                    {operation.name}
                    {operation.tool_cost &&
                    parseFloat(operation.tool_cost) > 0 ? (
                      <span className="text-zinc-400">
                        {" "}
                        (инстр. {operation.tool_cost} ₽)
                      </span>
                    ) : null}
                  </span>
                  <span className="tabular-nums text-zinc-800">
                    {operation.machine_time_min} мин · {operation.cost} ₽
                  </span>
                </div>
              ))}
            </div>
          )}
          {result.cooperations && result.cooperations.length > 0 && (
            <div className="pt-1">
              <div className="mb-1 border-t" />
              <div className="mb-1 text-xs font-medium text-zinc-500">
                Кооперация
              </div>
              {result.cooperations.map((line, index) => (
                <div
                  key={`${line.name}-${index}`}
                  className="flex items-baseline justify-between gap-2 py-0.5 text-xs"
                >
                  <span className="text-zinc-600">{line.name}</span>
                  <span className="tabular-nums text-zinc-800">
                    {line.qty} {line.unit} · {line.cost} ₽
                  </span>
                </div>
              ))}
            </div>
          )}
          {ladder.length > 0 && (
            <div className="pt-1">
              <div className="mb-1 border-t" />
              <div className="mb-1 text-xs font-medium text-zinc-500">
                Цены по тиражам (за деталь)
              </div>
              {ladder.map((rung) => {
                const current = rung.batch_size === batchSize;
                return (
                  <div
                    key={rung.batch_size}
                    className={`flex items-baseline justify-between gap-2 py-0.5 text-xs ${
                      current ? "font-semibold text-zinc-900" : "text-zinc-600"
                    }`}
                  >
                    <span>
                      {rung.batch_size} шт
                      {current && (
                        <span className="ml-1 text-[10px] text-emerald-600">
                          текущая
                        </span>
                      )}
                    </span>
                    <span className="tabular-nums">
                      {rung.price_per_part} ₽
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
