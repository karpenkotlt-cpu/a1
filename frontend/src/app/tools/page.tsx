"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ApiError, apiFetch } from "@/lib/api";
import type { ToolBasket } from "@/lib/types";
import { useAuthStore } from "@/stores/auth";

const GROUP_TITLES: Record<string, string> = {
  TURN_CNC_EXT: "Токарная ЧПУ: наружное точение",
  TURN_CNC_INT: "Токарная ЧПУ: расточка",
  TURN_MANUAL: "Токарная универсальная",
  MILL_CNC_FACE: "Фрезерная: торцевание (D50-63)",
  MILL_CNC_D16: "Фрезерная: карманы (D16-20)",
  MILL_CNC_D10: "Фрезерная: карманы (D8-12)",
  MILL_CNC_D5: "Фрезерная: пазы (D4-6)",
  MILL_CNC_D3: "Фрезерная: микро (D2-3)",
  MILL_5AXIS_3D: "5-осевая: 3D-поверхности",
  GRIND_CYL: "Шлифовка",
  DRILL_CARBIDE: "Сверление: тв. сплав",
  DRILL_HSS: "Сверление: быстрорез (HSS)",
};

function basketTitle(basket: ToolBasket): string {
  const base = GROUP_TITLES[basket.operation_group] ?? basket.operation_group;
  if (basket.diameter_from_mm && basket.diameter_to_mm) {
    return `${base} Ø${basket.diameter_from_mm}–${basket.diameter_to_mm}`;
  }
  return base;
}

export default function ToolBasketsPage() {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  const hydrated = useAuthStore((s) => s.hydrated);
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const [baskets, setBaskets] = useState<ToolBasket[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState({ cost: "", life: "", regrindable: false });
  const isAdmin = user?.role === "ADMIN";

  const load = useCallback(async () => {
    if (!token) return;
    try {
      setBaskets(await apiFetch<ToolBasket[]>("/tool-baskets", token));
      setError(null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        logout();
        router.replace("/login?next=/tools");
        return;
      }
      setError(err instanceof Error ? err.message : "Ошибка загрузки");
    }
  }, [token, logout, router]);

  useEffect(() => {
    if (!hydrated) return;
    if (!token) {
      router.replace("/login?next=/tools");
      return;
    }
    void load();
  }, [hydrated, token, router, load]);

  function startEdit(basket: ToolBasket) {
    setEditingId(basket.id);
    setDraft({
      cost: basket.tool_set_cost,
      life: basket.tool_life_min,
      regrindable: basket.regrindable,
    });
  }

  async function handleSave(id: number) {
    if (!token) return;
    try {
      await apiFetch<ToolBasket>(`/tool-baskets/${id}`, token, {
        method: "PATCH",
        body: {
          tool_set_cost: draft.cost,
          tool_life_min: draft.life,
          regrindable: draft.regrindable,
        },
      });
      setEditingId(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка сохранения");
    }
  }

  return (
    <div className="min-h-screen bg-zinc-50">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <h1 className="text-lg font-semibold">Инструментальные корзины</h1>
          <div className="flex items-center gap-3 text-sm text-zinc-600">
            <a href="/materials" className="rounded-md border px-3 py-1.5 hover:bg-zinc-100">
              ← Материалы
            </a>
            <a href="/rates" className="rounded-md border px-3 py-1.5 hover:bg-zinc-100">
              Нормативы →
            </a>
            <span>
              {user?.email} · {user?.role}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                logout();
                router.replace("/login");
              }}
            >
              Выйти
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl space-y-4 px-6 py-8">
        <p className="text-sm text-zinc-500">
          Нормативы для P-группы (Сталь 45): влияние материала масштабируется
          коэффициентом Kwear. Стоимость минуты = Ctool / Tlife (для
          перетачиваемого монолита ×0.733).
        </p>
        {error && (
          <p className="rounded-md border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
            {error}
          </p>
        )}
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Корзина</TableHead>
              <TableHead className="text-right">Ctool, ₽</TableHead>
              <TableHead className="text-right">Tlife, мин</TableHead>
              <TableHead>Переточка</TableHead>
              {isAdmin && <TableHead />}
            </TableRow>
          </TableHeader>
          <TableBody>
            {baskets.map((basket) =>
              editingId === basket.id ? (
                <TableRow key={basket.id}>
                  <TableCell>{basketTitle(basket)}</TableCell>
                  <TableCell>
                    <input
                      type="number"
                      step="0.01"
                      min="0.01"
                      value={draft.cost}
                      onChange={(e) =>
                        setDraft({ ...draft, cost: e.target.value })
                      }
                      className="h-8 w-24 rounded-md border border-input px-2 text-sm"
                    />
                  </TableCell>
                  <TableCell>
                    <input
                      type="number"
                      step="1"
                      min="1"
                      value={draft.life}
                      onChange={(e) =>
                        setDraft({ ...draft, life: e.target.value })
                      }
                      className="h-8 w-20 rounded-md border border-input px-2 text-sm"
                    />
                  </TableCell>
                  <TableCell>
                    <input
                      type="checkbox"
                      checked={draft.regrindable}
                      onChange={(e) =>
                        setDraft({ ...draft, regrindable: e.target.checked })
                      }
                    />
                  </TableCell>
                  <TableCell className="space-x-2 text-right whitespace-nowrap">
                    <Button size="sm" onClick={() => void handleSave(basket.id)}>
                      Сохранить
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setEditingId(null)}
                    >
                      Отмена
                    </Button>
                  </TableCell>
                </TableRow>
              ) : (
                <TableRow key={basket.id}>
                  <TableCell className="font-medium">
                    {basketTitle(basket)}
                  </TableCell>
                  <TableCell className="text-right">
                    {basket.tool_set_cost}
                  </TableCell>
                  <TableCell className="text-right">
                    {basket.tool_life_min}
                  </TableCell>
                  <TableCell>{basket.regrindable ? "да (×0.733)" : "нет"}</TableCell>
                  {isAdmin && (
                    <TableCell className="text-right">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => startEdit(basket)}
                      >
                        Изменить
                      </Button>
                    </TableCell>
                  )}
                </TableRow>
              ),
            )}
          </TableBody>
        </Table>
      </main>
    </div>
  );
}
