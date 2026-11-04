"use client";

import { useRouter } from "next/navigation";
import {
  Fragment,
  useCallback,
  useEffect,
  useState,
  type FormEvent,
} from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ApiError, apiFetch } from "@/lib/api";
import type { Material } from "@/lib/types";
import { useAuthStore } from "@/stores/auth";

const ISO_GROUPS = ["P", "M", "K", "N", "S", "H"] as const;

const EMPTY_FORM = {
  grade: "",
  gost: "",
  iso_group: "P",
  density_g_cm3: "7.85",
  machinability_factor: "1.00",
  cost_per_kg: "0.00",
  scrap_price_per_kg: "0.00",
};

export default function MaterialsPage() {
  const router = useRouter();
  const token = useAuthStore((state) => state.token);
  const user = useAuthStore((state) => state.user);
  const hydrated = useAuthStore((state) => state.hydrated);
  const logout = useAuthStore((state) => state.logout);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editDraft, setEditDraft] = useState(EMPTY_FORM);
  const isAdmin = user?.role === "ADMIN";

  const load = useCallback(async () => {
    if (!token) return;
    try {
      setMaterials(await apiFetch<Material[]>("/materials", token));
      setError(null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        logout();
        router.replace("/login?next=/materials");
        return;
      }
      setError(err instanceof Error ? err.message : "Ошибка загрузки");
    }
  }, [token, logout, router]);

  useEffect(() => {
    if (!hydrated) return;
    if (!token) {
      router.replace("/login?next=/materials");
      return;
    }
    void load();
  }, [hydrated, token, router, load]);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    try {
      await apiFetch<Material>("/materials", token, {
        method: "POST",
        body: { ...form, gost: form.gost === "" ? null : form.gost },
      });
      setForm(EMPTY_FORM);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка создания");
    }
  }

  async function handleDelete(id: number) {
    if (!token) return;
    try {
      await apiFetch<void>(`/materials/${id}`, token, { method: "DELETE" });
      setEditingId(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка удаления");
    }
  }

  function startEdit(material: Material) {
    setEditingId(material.id);
    setEditDraft({
      grade: material.grade,
      gost: material.gost ?? "",
      iso_group: material.iso_group,
      density_g_cm3: material.density_g_cm3,
      machinability_factor: material.machinability_factor,
      cost_per_kg: material.cost_per_kg,
      scrap_price_per_kg: material.scrap_price_per_kg,
    });
  }

  async function handleUpdate(id: number) {
    if (!token) return;
    try {
      await apiFetch<Material>(`/materials/${id}`, token, {
        method: "PATCH",
        body: { ...editDraft, gost: editDraft.gost === "" ? null : editDraft.gost },
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
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <h1 className="text-lg font-semibold">Справочник: Материалы</h1>
          <div className="flex items-center gap-3 text-sm text-zinc-600">
            <a href="/tools" className="rounded-md border px-3 py-1.5 hover:bg-zinc-100">
              Корзины инструмента
            </a>
            <span>
              {user?.email} · {user?.role}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                logout();
                router.replace("/login?next=/materials");
              }}
            >
              Выйти
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl space-y-6 px-6 py-8">
        {error && (
          <p className="rounded-md border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
            {error}
          </p>
        )}
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Марка</TableHead>
              <TableHead>ГОСТ</TableHead>
              <TableHead>ISO</TableHead>
              <TableHead className="text-right">ρ, г/см³</TableHead>
              <TableHead className="text-right">Kmach</TableHead>
              <TableHead className="text-right">Цена, ₽/кг</TableHead>
              <TableHead className="text-right">Стружка, ₽/кг</TableHead>
              {isAdmin && <TableHead />}
            </TableRow>
          </TableHeader>
          <TableBody>
            {materials.map((material) => (
              // key обязателен на корневом элементе итерации: шорткат <>
              // не принимает пропсы, поэтому Fragment с ключом.
              <Fragment key={material.id}>
                <TableRow>
                  <TableCell className="font-medium">{material.grade}</TableCell>
                  <TableCell>{material.gost ?? "—"}</TableCell>
                  <TableCell>{material.iso_group}</TableCell>
                  <TableCell className="text-right">
                    {material.density_g_cm3}
                  </TableCell>
                  <TableCell className="text-right">
                    {material.machinability_factor}
                  </TableCell>
                  <TableCell className="text-right">{material.cost_per_kg}</TableCell>
                  <TableCell className="text-right">
                    {material.scrap_price_per_kg}
                  </TableCell>
                  {isAdmin && (
                    <TableCell className="space-x-2 text-right whitespace-nowrap">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => startEdit(material)}
                      >
                        Изменить
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => void handleDelete(material.id)}
                      >
                        Удалить
                      </Button>
                    </TableCell>
                  )}
                </TableRow>
                {editingId === material.id && (
                  <TableRow key={`${material.id}-edit`}>
                    <TableCell colSpan={8}>
                      <div className="grid grid-cols-2 gap-3 py-2 md:grid-cols-4">
                        <div className="space-y-1">
                          <Label className="text-xs text-zinc-500">Марка</Label>
                          <Input
                            value={editDraft.grade}
                            onChange={(e) =>
                              setEditDraft({ ...editDraft, grade: e.target.value })
                            }
                          />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs text-zinc-500">ГОСТ</Label>
                          <Input
                            value={editDraft.gost}
                            onChange={(e) =>
                              setEditDraft({ ...editDraft, gost: e.target.value })
                            }
                          />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs text-zinc-500">ISO</Label>
                          <select
                            value={editDraft.iso_group}
                            onChange={(e) =>
                              setEditDraft({
                                ...editDraft,
                                iso_group: e.target.value,
                              })
                            }
                            className="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm"
                          >
                            {ISO_GROUPS.map((group) => (
                              <option key={group} value={group}>
                                {group}
                              </option>
                            ))}
                          </select>
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs text-zinc-500">ρ, г/см³</Label>
                          <Input
                            type="number"
                            step="0.0001"
                            value={editDraft.density_g_cm3}
                            onChange={(e) =>
                              setEditDraft({
                                ...editDraft,
                                density_g_cm3: e.target.value,
                              })
                            }
                          />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs text-zinc-500">Kmach (Kq)</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={editDraft.machinability_factor}
                            onChange={(e) =>
                              setEditDraft({
                                ...editDraft,
                                machinability_factor: e.target.value,
                              })
                            }
                          />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs text-zinc-500">Цена, ₽/кг</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={editDraft.cost_per_kg}
                            onChange={(e) =>
                              setEditDraft({
                                ...editDraft,
                                cost_per_kg: e.target.value,
                              })
                            }
                          />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs text-zinc-500">
                            Стружка, ₽/кг
                          </Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={editDraft.scrap_price_per_kg}
                            onChange={(e) =>
                              setEditDraft({
                                ...editDraft,
                                scrap_price_per_kg: e.target.value,
                              })
                            }
                          />
                        </div>
                        <div className="flex items-end gap-2">
                          <Button
                            size="sm"
                            onClick={() => void handleUpdate(material.id)}
                          >
                            Сохранить
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setEditingId(null)}
                          >
                            Отмена
                          </Button>
                        </div>
                      </div>
                    </TableCell>
                   </TableRow>
                 )}
              </Fragment>
             ))}
            {materials.length === 0 && (
              <TableRow>
                <TableCell colSpan={8} className="text-center text-zinc-500">
                  Нет материалов
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
        {isAdmin && (
          <form
            onSubmit={handleCreate}
            className="grid grid-cols-2 gap-4 rounded-xl border bg-white p-6 md:grid-cols-4"
          >
            <div className="space-y-2">
              <Label htmlFor="grade">Марка</Label>
              <Input
                id="grade"
                value={form.grade}
                onChange={(event) =>
                  setForm({ ...form, grade: event.target.value })
                }
                required
                minLength={2}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="gost">ГОСТ</Label>
              <Input
                id="gost"
                value={form.gost}
                onChange={(event) =>
                  setForm({ ...form, gost: event.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="iso_group">ISO-группа</Label>
              <select
                id="iso_group"
                value={form.iso_group}
                onChange={(event) =>
                  setForm({ ...form, iso_group: event.target.value })
                }
                className="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm"
              >
                {ISO_GROUPS.map((group) => (
                  <option key={group} value={group}>
                    {group}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="density">Плотность, г/см³</Label>
              <Input
                id="density"
                type="number"
                step="0.0001"
                value={form.density_g_cm3}
                onChange={(event) =>
                  setForm({ ...form, density_g_cm3: event.target.value })
                }
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="machinability">Kmach</Label>
              <Input
                id="machinability"
                type="number"
                step="0.01"
                value={form.machinability_factor}
                onChange={(event) =>
                  setForm({ ...form, machinability_factor: event.target.value })
                }
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="cost">Цена, ₽/кг</Label>
              <Input
                id="cost"
                type="number"
                step="0.01"
                value={form.cost_per_kg}
                onChange={(event) =>
                  setForm({ ...form, cost_per_kg: event.target.value })
                }
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="scrap">Стружка, ₽/кг</Label>
              <Input
                id="scrap"
                type="number"
                step="0.01"
                value={form.scrap_price_per_kg}
                onChange={(event) =>
                  setForm({ ...form, scrap_price_per_kg: event.target.value })
                }
                required
              />
            </div>
            <div className="flex items-end">
              <Button type="submit" className="w-full">
                Добавить
              </Button>
            </div>
          </form>
        )}
      </main>
    </div>
  );
}
