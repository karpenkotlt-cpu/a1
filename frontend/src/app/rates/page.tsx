"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { AuxiliarySection } from "@/components/rates/AuxiliarySection";
import { CapacitySection } from "@/components/rates/CapacitySection";
import { CoefficientsSection } from "@/components/rates/CoefficientsSection";
import { CooperationSection } from "@/components/rates/CooperationSection";
import { DrillingSection } from "@/components/rates/DrillingSection";
import { OperationsSection } from "@/components/rates/OperationsSection";
import { WorkCentersSection } from "@/components/rates/WorkCentersSection";
import { Card } from "@/components/ui/card";
import { ApiError, apiFetch } from "@/lib/api";
import type {
  AuxiliaryOperation,
  CapacityLoadRow,
  CoefficientRow,
  CooperationService,
  DrillingRate,
  OperationRow,
  WorkCenterRow,
} from "@/lib/types";
import { useAuthStore } from "@/stores/auth";

export default function RatesPage() {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  const hydrated = useAuthStore((s) => s.hydrated);
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const [operations, setOperations] = useState<OperationRow[]>([]);
  const [centers, setCenters] = useState<WorkCenterRow[]>([]);
  const [coefficients, setCoefficients] = useState<CoefficientRow[]>([]);
  const [auxiliary, setAuxiliary] = useState<AuxiliaryOperation[]>([]);
  const [drilling, setDrilling] = useState<DrillingRate[]>([]);
  const [cooperation, setCooperation] = useState<CooperationService[]>([]);
  const [capacity, setCapacity] = useState<CapacityLoadRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const isAdmin = user?.role === "ADMIN";

  const load = useCallback(async () => {
    if (!token) return;
    try {
      const [ops, wcs, coefs, aux, drill, coop, cap] = await Promise.all([
        apiFetch<OperationRow[]>("/operations", token),
        apiFetch<WorkCenterRow[]>("/work-centers", token),
        apiFetch<CoefficientRow[]>("/coefficients", token),
        apiFetch<AuxiliaryOperation[]>("/auxiliary-operations", token),
        apiFetch<DrillingRate[]>("/drilling-rates", token),
        apiFetch<CooperationService[]>("/cooperation-services", token),
        apiFetch<CapacityLoadRow[]>("/capacity", token),
      ]);
      setOperations(ops);
      setCenters(wcs);
      setCoefficients(coefs);
      setAuxiliary(aux);
      setDrilling(drill);
      setCooperation(coop);
      setCapacity(cap);
      setError(null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        logout();
        router.replace("/login?next=/rates");
        return;
      }
      setError(err instanceof Error ? err.message : "Ошибка загрузки");
    }
  }, [token, logout, router]);

  useEffect(() => {
    if (!hydrated) return;
    if (!token) {
      router.replace("/login?next=/rates");
      return;
    }
    void load();
  }, [hydrated, token, router, load]);

  const run = async (action: () => Promise<unknown>) => {
    try {
      await action();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка сохранения");
    }
  };

  return (
    <div className="min-h-screen bg-zinc-50">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <h1 className="text-lg font-semibold">
            Нормативы: операции · станки · коэффициенты · сверление
          </h1>
          <div className="flex items-center gap-3 text-sm text-zinc-600">
            <a href="/tools" className="rounded-md border px-3 py-1.5 hover:bg-zinc-100">
              ← Инструмент
            </a>
            <span>
              {user?.email} · {user?.role}
            </span>
            <button
              type="button"
              className="rounded-md border px-3 py-1.5 hover:bg-zinc-100"
              onClick={() => {
                logout();
                router.replace("/login");
              }}
            >
              Выйти
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl space-y-8 px-6 py-8">
        {error && (
          <p className="rounded-md border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        <Card className="p-4">
          <h2 className="mb-1 font-semibold">Операции и производительность</h2>
          <p className="mb-4 text-sm text-zinc-500">
            Tпз — базовая наладка; Q — съём металла (черновая), S —
            производительность (чистовая). Базовые значения для ISO-группы P
            (Сталь 45); другие материалы масштабируются Kq/Ks.
          </p>
          <OperationsSection
            operations={operations}
            isAdmin={isAdmin}
            onSaveSetup={(id, setup) =>
              run(() =>
                apiFetch<OperationRow>(`/operations/${id}`, token!, {
                  method: "PATCH",
                  body: { setup_time_base_min: setup },
                }),
              )
            }
            onSaveRate={(id, q, s) =>
              run(() =>
                apiFetch(`/operation-rates/${id}`, token!, {
                  method: "PATCH",
                  body: { q_rough_cm3_min: q, s_finish_dm2_min: s },
                }),
              )
            }
          />
        </Card>

        <Card className="p-4">
          <h2 className="mb-1 font-semibold">Рабочие центры (ставка минуты)</h2>
          <p className="mb-4 text-sm text-zinc-500">
            Итоговая ставка минуты R_i (амортизация + энергия + ФОТ + ОПР/ОХР).
            Движок берёт минимальную ставку активного центра группы.
          </p>
          <WorkCentersSection
            centers={centers}
            isAdmin={isAdmin}
            onSaveRate={(id, rate) =>
              run(() =>
                apiFetch<WorkCenterRow>(`/work-centers/${id}`, token!, {
                  method: "PATCH",
                  body: { machine_rate_per_min: rate },
                }),
              )
            }
          />
        </Card>

        <Card className="p-4">
          <h2 className="mb-1 font-semibold">Коэффициенты</h2>
          <p className="mb-4 text-sm text-zinc-500">
            Множители за квалитет (KIT/Ra) и геометрию (тонкостенность,
            прерывистость резания).
          </p>
          <CoefficientsSection
            coefficients={coefficients}
            isAdmin={isAdmin}
            onSave={(id, multiplier) =>
              run(() =>
                apiFetch<CoefficientRow>(`/coefficients/${id}`, token!, {
                  method: "PATCH",
                  body: { multiplier },
                }),
              )
            }
          />
        </Card>

        <Card className="p-4">
          <h2 className="mb-1 font-semibold">Вспомогательные операции</h2>
          <p className="mb-4 text-sm text-zinc-500">
            Фиксированное время × трудовая ставка (слесарка, ОТК, маркировка).
            Неактивные не попадают в расчёт.
          </p>
          <AuxiliarySection
            operations={auxiliary}
            isAdmin={isAdmin}
            onSave={(id, time, rate, isActive) =>
              run(() =>
                apiFetch<AuxiliaryOperation>(
                  `/auxiliary-operations/${id}`,
                  token!,
                  {
                    method: "PATCH",
                    body: {
                      fixed_time_min: time,
                      rate_per_min: rate,
                      is_active: isActive,
                    },
                  },
                ),
              )
            }
          />
        </Card>

        <Card className="p-4">
          <h2 className="mb-1 font-semibold">Подачи сверления по Ø</h2>
          <p className="mb-4 text-sm text-zinc-500">
            Скорость подачи сверла по диапазонам диаметров для тв. сплава и
            HSS (drill_type в HOLE_ARRAY).
          </p>
          <DrillingSection
            rates={drilling}
            isAdmin={isAdmin}
            onSave={(id, carbide, hss) =>
              run(() =>
                apiFetch<DrillingRate>(`/drilling-rates/${id}`, token!, {
                  method: "PATCH",
                  body: {
                    carbide_feed_mm_min: carbide,
                    hss_feed_mm_min: hss,
                  },
                }),
              )
            }
          />
        </Card>

        <Card className="p-4">
          <h2 className="mb-1 font-semibold">Кооперация (подрядчики)</h2>
          <p className="mb-4 text-sm text-zinc-500">
            Цены подрядчиков: термообработка за кг, гальваника за дм², лазер
            за пог. м. MOQ — минимальная партия услуги.
          </p>
          <CooperationSection
            services={cooperation}
            isAdmin={isAdmin}
            onCreate={(form) =>
              run(() =>
                apiFetch<CooperationService>("/cooperation-services", token!, {
                  method: "POST",
                  body: form,
                }),
              )
            }
            onUpdate={(id, price, minLot) =>
              run(() =>
                apiFetch<CooperationService>(
                  `/cooperation-services/${id}`,
                  token!,
                  {
                    method: "PATCH",
                    body: { price_per_unit: price, min_lot_qty: minLot },
                  },
                ),
              )
            }
            onDelete={(id) =>
              run(() =>
                apiFetch<void>(`/cooperation-services/${id}`, token!, {
                  method: "DELETE",
                }),
              )
            }
          />
        </Card>
        <Card className="p-4">
          <h2 className="mb-1 font-semibold">Загрузка станков (APS)</h2>
          <p className="mb-4 text-sm text-zinc-500">
            Загрузка группы на горизонте управляет динамической маржой КП:
            &lt;40% → Kmargin 0.55; 40–80% → 1.0; 80–95% → 1.35; &gt;95% → 2.0
            (surge). Берётся группа главного станка маршрута.
          </p>
          <CapacitySection
            rows={capacity}
            isAdmin={isAdmin}
            onSave={(id, scheduled) =>
              run(() =>
                apiFetch<CapacityLoadRow>(`/capacity/${id}`, token!, {
                  method: "PATCH",
                  body: { scheduled_minutes: scheduled },
                }),
              )
            }
          />
        </Card>
      </main>
    </div>
  );
}
