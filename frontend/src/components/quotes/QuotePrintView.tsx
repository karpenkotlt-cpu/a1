"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, apiFetch } from "@/lib/api";
import type {
  CalculateRequest,
  T1Dimensions,
  T2Dimensions,
  T3Dimensions,
  T4Dimensions,
  T5Dimensions,
} from "@/lib/constructor-types";
import {
  featureRows,
  formatDate,
  formatMoney,
  templateRows,
} from "@/lib/quote-format";
import type { QuoteDetail } from "@/lib/types";
import { useAuthStore } from "@/stores/auth";

const cellBorder = "border border-zinc-400 px-2 py-1";

function scadEnvelope(request: CalculateRequest): string {
  // base_template.type/dimensions — не discriminated union: сужаем кастом
  const { type, dimensions } = request.base_template;
  if (type === "T1_STEPPED_SHAFT" || type === "T2_BUSHING") {
    const steps =
      type === "T1_STEPPED_SHAFT"
        ? (dimensions as T1Dimensions).steps
        : (dimensions as T2Dimensions).outer_steps;
    const d = Math.max(...steps.map((s) => s.diameter));
    const l = steps.reduce((acc, s) => acc + s.length, 0);
    return `Ø${Math.round(d)} × ${Math.round(l)} мм`;
  }
  if (type === "T3_FLANGE") {
    const flange = dimensions as T3Dimensions;
    return `Ø${flange.outer_diameter} × ${flange.thickness} мм`;
  }
  const box = dimensions as T4Dimensions | T5Dimensions;
  return `${box.length} × ${box.width} × ${box.height} мм`;
}

function scadCodePreview(code: string, maxLines: number): string {
  const lines = code.split(/\r?\n/);
  const head = lines.slice(0, maxLines).join("\n");
  return lines.length > maxLines
    ? `${head}\n… всего ${lines.length} строк (модель сохранена в КП полностью)`
    : head;
}

function Section({
  title,
  rows,
}: {
  title: string;
  rows: [string, string][];
}) {
  return (
    <section className="mt-6">
      <h2 className="mb-1 font-semibold">{title}</h2>
      <table className="w-full border-collapse text-sm">
        <tbody>
          {rows.map(([label, value]) => (
            <tr key={label}>
              <td className={`${cellBorder} w-64 bg-zinc-50 print:bg-white`}>
                {label}
              </td>
              <td className={cellBorder}>{value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

export default function QuotePrintView() {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  const hydrated = useAuthStore((s) => s.hydrated);
  const logout = useAuthStore((s) => s.logout);
  // id читаем из URL после монтирования: useParams() в рендере блокирует
  // пререндер (Cache Components) — bailout без Suspense падает на билде.
  const [id, setId] = useState<string | null>(null);
  const [detail, setDetail] = useState<QuoteDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const match = window.location.pathname.match(/\/quotes\/(\d[\d]*)\/print/);
    setId(match ? match[1] : null);
  }, []);

  const load = useCallback(async () => {
    if (!token || !id) return;
    try {
      setDetail(await apiFetch<QuoteDetail>(`/quotes/${id}`, token));
      setError(null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        logout();
        router.replace(`/login?next=/quotes/${id}/print`);
        return;
      }
      setError(err instanceof Error ? err.message : "Ошибка загрузки");
    }
  }, [token, id, logout, router]);

  useEffect(() => {
    if (id === null || !hydrated) return;
    if (!token) {
      router.replace(`/login?next=/quotes/${id}/print`);
      return;
    }
    void load();
  }, [hydrated, token, id, router, load]);

  if (error) {
    return (
      <div className="min-h-screen bg-zinc-50 p-8">
        <p className="rounded-md border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
          {error}
        </p>
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="min-h-screen bg-zinc-50 p-8 text-sm text-zinc-500">
        Загрузка…
      </div>
    );
  }

  const { request, result } = detail;
  const operations = result.operations ?? [];

  return (
    <div className="min-h-screen bg-zinc-100 print:bg-white">
      <div className="flex items-center justify-between px-6 py-3 print:hidden">
        <Button
          variant="outline"
          size="sm"
          onClick={() => router.push("/quotes")}
        >
          ← К расчётам
        </Button>
        <Button size="sm" onClick={() => window.print()}>
          Печать / PDF
        </Button>
      </div>
      <div className="mx-auto mb-8 w-full max-w-[794px] bg-white p-10 text-black shadow print:max-w-none print:p-6 print:shadow-none">
        <header className="border-b-2 border-black pb-3">
          <h1 className="text-xl font-bold tracking-wide">
            КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ
          </h1>
          <p className="mt-1 text-base font-semibold">{detail.name}</p>
          <p className="mt-1 text-sm">
            № {detail.project_id} · от {formatDate(detail.created_at)} · партия{" "}
            {detail.batch_size} шт.
          </p>
        </header>

        <Section
          title="Деталь"
          rows={[...templateRows(request), ...featureRows(request)]}
        />

        {request.scad_code && (
          <section className="mt-6">
            <h2 className="mb-1 font-semibold">Модель OpenSCAD</h2>
            <table className="w-full border-collapse text-sm">
              <tbody>
                <tr>
                  <td
                    className={`${cellBorder} w-64 bg-zinc-50 print:bg-white`}
                  >
                    Габариты модели
                  </td>
                  <td className={cellBorder}>{scadEnvelope(request)}</td>
                </tr>
                <tr>
                  <td
                    className={`${cellBorder} bg-zinc-50 print:bg-white`}
                  >
                    V нетто по сетке, см³
                  </td>
                  <td className={cellBorder}>{result.v_net_cm3}</td>
                </tr>
              </tbody>
            </table>
            <pre className="mt-2 overflow-hidden rounded border border-zinc-300 bg-zinc-50 p-2 font-mono text-[10px] leading-tight text-zinc-700">
              {scadCodePreview(request.scad_code, 10)}
            </pre>
          </section>
        )}

        <Section
          title="Материал"
          rows={[
            ["ISO-группа", request.material.iso_group],
            ["Kq (черновой)", String(request.material.k_mach_rough)],
            ["Ks (чистовой)", String(request.material.k_mach_finish)],
            ["Плотность, г/см³", String(request.material.density_g_cm3)],
            ["Цена, ₽/кг", formatMoney(request.material.cost_per_kg)],
            ["Стружка, ₽/кг", formatMoney(request.material.scrap_price_per_kg)],
          ]}
        />

        <Section
          title="Результаты расчёта"
          rows={[
            ["Чистая масса, кг", String(result.m_net_kg)],
            ["Масса заготовки, кг", String(result.m_gross_kg)],
            ["Съём Vrem, см³", String(result.v_removed_cm3)],
            ["Материал, ₽/дет", formatMoney(result.material_cost)],
            ["Машинное время Tшт, мин", String(result.machine_time_min)],
            ["Наладка Tпз, мин", String(result.setup_time_min)],
            ["Инструмент, ₽/дет", formatMoney(result.tool_cost ?? "0")],
            [
              "Кооперация, ₽/дет",
              formatMoney(result.cooperation_cost ?? "0"),
            ],
          ]}
        />

        {(result.cooperations ?? []).length > 0 && (
          <Section
            title="Кооперация"
            rows={(result.cooperations ?? []).map((line) => [
              line.name,
              `${line.qty} ${line.unit} × ${formatMoney(line.unit_price)} = ${formatMoney(line.cost)} ₽`,
            ])}
          />
        )}

        {operations.length > 0 && (
          <section className="mt-6">
            <h2 className="mb-1 font-semibold">Маршрут обработки</h2>
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr>
                  <th className={cellBorder}>Операция</th>
                  <th className={cellBorder}>Tшт, мин</th>
                  <th className={cellBorder}>Tпз, мин</th>
                  <th className={cellBorder}>Ставка, ₽/мин</th>
                  <th className={cellBorder}>Инстр., ₽</th>
                  <th className={cellBorder}>Стоимость, ₽</th>
                </tr>
              </thead>
              <tbody>
                {operations.map((op) => (
                  <tr key={op.code}>
                    <td className={cellBorder}>{op.name}</td>
                    <td className={`${cellBorder} text-right`}>
                      {op.machine_time_min}
                    </td>
                    <td className={`${cellBorder} text-right`}>
                      {op.setup_time_min}
                    </td>
                    <td className={`${cellBorder} text-right`}>
                      {op.machine_rate_per_min}
                    </td>
                    <td className={`${cellBorder} text-right`}>
                      {formatMoney(op.tool_cost ?? "0")}
                    </td>
                    <td className={`${cellBorder} text-right`}>
                      {formatMoney(op.cost)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}

        <section className="mt-6">
          <h2 className="mb-1 font-semibold">Цена</h2>
          <table className="w-full border-collapse text-sm">
            <tbody>
              <tr>
                <td className={`${cellBorder} w-64`}>Цена за деталь, ₽</td>
                <td className={`${cellBorder} text-right`}>
                  {formatMoney(result.price_per_part)}
                </td>
              </tr>
              <tr className="font-bold">
                <td className={`${cellBorder} bg-zinc-200 print:bg-white`}>
                  ИТОГО за партию {detail.batch_size} шт., ₽
                </td>
                <td
                  className={`${cellBorder} bg-zinc-200 text-right text-base print:bg-white`}
                >
                  {formatMoney(result.batch_total_price)}
                </td>
              </tr>
            </tbody>
          </table>
          <p className="mt-2 text-xs text-zinc-600">
            Предложение действительно 15 календарных дней. Цены указаны с
            учётом наценки {String(request.margin_percent)}%.
          </p>
        </section>
      </div>
    </div>
  );
}
