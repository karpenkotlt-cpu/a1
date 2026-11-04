"use client";

import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  SERVICE_TYPE_TITLES,
  UNIT_TITLES,
  type CooperationService,
} from "@/lib/types";

const EMPTY_FORM = {
  service_type: "HEAT_TREATMENT",
  unit: "KG",
  price_per_unit: "",
  contractor: "",
  min_lot_qty: "0",
};

interface CooperationSectionProps {
  services: CooperationService[];
  isAdmin: boolean;
  onCreate: (form: typeof EMPTY_FORM) => Promise<void>;
  onUpdate: (
    serviceId: number,
    price: string,
    minLot: string,
  ) => Promise<void>;
  onDelete: (serviceId: number) => Promise<void>;
}

export function CooperationSection({
  services,
  isAdmin,
  onCreate,
  onUpdate,
  onDelete,
}: CooperationSectionProps) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState({ price: "", minLot: "" });

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onCreate(form);
    setForm(EMPTY_FORM);
  }

  function startEdit(service: CooperationService) {
    setEditingId(service.id);
    setDraft({
      price: service.price_per_unit,
      minLot: service.min_lot_qty,
    });
  }

  return (
    <div className="space-y-4">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Услуга</TableHead>
            <TableHead>Подрядчик</TableHead>
            <TableHead className="text-right">Цена, ₽</TableHead>
            <TableHead>Единица</TableHead>
            <TableHead className="text-right">MOQ</TableHead>
            {isAdmin && <TableHead />}
          </TableRow>
        </TableHeader>
        <TableBody>
          {services.map((service) =>
            editingId === service.id ? (
              <TableRow key={service.id}>
                <TableCell className="font-medium">
                  {SERVICE_TYPE_TITLES[service.service_type] ??
                    service.service_type}
                </TableCell>
                <TableCell>{service.contractor ?? "—"}</TableCell>
                <TableCell className="text-right">
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    value={draft.price}
                    onChange={(e) =>
                      setDraft({ ...draft, price: e.target.value })
                    }
                    className="h-8 w-24 rounded-md border border-input px-2 text-sm"
                  />
                </TableCell>
                <TableCell>
                  {UNIT_TITLES[service.unit] ?? service.unit}
                </TableCell>
                <TableCell className="text-right">
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={draft.minLot}
                    onChange={(e) =>
                      setDraft({ ...draft, minLot: e.target.value })
                    }
                    className="h-8 w-24 rounded-md border border-input px-2 text-sm"
                  />
                </TableCell>
                <TableCell className="space-x-2 text-right whitespace-nowrap">
                  <Button
                    size="sm"
                    onClick={() => void onUpdate(service.id, draft.price, draft.minLot)}
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
                </TableCell>
              </TableRow>
            ) : (
              <TableRow key={service.id}>
                <TableCell className="font-medium">
                  {SERVICE_TYPE_TITLES[service.service_type] ??
                    service.service_type}
                </TableCell>
                <TableCell>{service.contractor ?? "—"}</TableCell>
                <TableCell className="text-right">
                  {service.price_per_unit}
                </TableCell>
                <TableCell>
                  {UNIT_TITLES[service.unit] ?? service.unit}
                </TableCell>
                <TableCell className="text-right">
                  {service.min_lot_qty}
                </TableCell>
                {isAdmin && (
                  <TableCell className="space-x-2 text-right whitespace-nowrap">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => startEdit(service)}
                    >
                      Изменить
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => void onDelete(service.id)}
                    >
                      Удалить
                    </Button>
                  </TableCell>
                )}
              </TableRow>
            ),
          )}
          {services.length === 0 && (
            <TableRow>
              <TableCell colSpan={6} className="text-center text-zinc-500">
                Нет услуг кооперации
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
      {isAdmin && (
        <form
          onSubmit={handleCreate}
          className="flex flex-wrap items-end gap-3 rounded-lg border bg-zinc-50 p-4"
        >
          <div className="space-y-1">
            <span className="text-xs text-zinc-500">Услуга</span>
            <select
              value={form.service_type}
              onChange={(e) =>
                setForm({ ...form, service_type: e.target.value })
              }
              className="h-9 rounded-md border border-input bg-transparent px-3 text-sm"
            >
              {Object.entries(SERVICE_TYPE_TITLES).map(([value, title]) => (
                <option key={value} value={value}>
                  {title}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <span className="text-xs text-zinc-500">Единица</span>
            <select
              value={form.unit}
              onChange={(e) => setForm({ ...form, unit: e.target.value })}
              className="h-9 rounded-md border border-input bg-transparent px-3 text-sm"
            >
              {Object.entries(UNIT_TITLES).map(([value, title]) => (
                <option key={value} value={value}>
                  {title}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <span className="text-xs text-zinc-500">Цена, ₽</span>
            <Input
              type="number"
              step="0.01"
              min="0.01"
              required
              value={form.price_per_unit}
              onChange={(e) =>
                setForm({ ...form, price_per_unit: e.target.value })
              }
              className="w-28"
            />
          </div>
          <div className="space-y-1">
            <span className="text-xs text-zinc-500">Подрядчик</span>
            <Input
              value={form.contractor}
              onChange={(e) =>
                setForm({ ...form, contractor: e.target.value })
              }
              className="w-40"
            />
          </div>
          <div className="space-y-1">
            <span className="text-xs text-zinc-500">MOQ</span>
            <Input
              type="number"
              step="0.01"
              min="0"
              value={form.min_lot_qty}
              onChange={(e) =>
                setForm({ ...form, min_lot_qty: e.target.value })
              }
              className="w-24"
            />
          </div>
          <Button type="submit" size="sm">
            Добавить
          </Button>
        </form>
      )}
    </div>
  );
}
