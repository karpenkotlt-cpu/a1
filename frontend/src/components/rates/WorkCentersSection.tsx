"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { WorkCenterRow } from "@/lib/types";

const MACHINE_TYPE_TITLES: Record<string, string> = {
  TURNING_CNC: "Токарный ЧПУ",
  TURNING_CONVENTIONAL: "Токарный универсальный",
  MILLING_3AXIS: "Фрезерный 3-ос.",
  MILLING_5AXIS: "Фрезерный 5-ос.",
  DRILLING: "Сверлильный",
  GRINDING: "Шлифовальный",
  WEDM: "Эрозионный",
  BANDSAW: "Ленточнопильный",
  LASER: "Лазерный",
  PRESS_BRAKE: "Листогиб",
};

interface WorkCentersSectionProps {
  centers: WorkCenterRow[];
  isAdmin: boolean;
  onSaveRate: (centerId: number, rate: string) => Promise<void>;
}

export function WorkCentersSection({
  centers,
  isAdmin,
  onSaveRate,
}: WorkCentersSectionProps) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState("");

  function startEdit(center: WorkCenterRow) {
    setEditingId(center.id);
    setDraft(center.machine_rate_per_min ?? "");
  }

  async function handleSave(centerId: number) {
    await onSaveRate(centerId, draft);
    setEditingId(null);
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Рабочий центр</TableHead>
          <TableHead>Тип</TableHead>
          <TableHead>Группа</TableHead>
          <TableHead className="text-right">Ставка, ₽/мин</TableHead>
          {isAdmin && <TableHead />}
        </TableRow>
      </TableHeader>
      <TableBody>
        {centers.map((center) =>
          editingId === center.id ? (
            <TableRow key={center.id}>
              <TableCell className="font-medium">{center.name}</TableCell>
              <TableCell>
                {MACHINE_TYPE_TITLES[center.machine_type] ??
                  center.machine_type}
              </TableCell>
              <TableCell className="text-zinc-500">
                {center.group_code}
              </TableCell>
              <TableCell className="text-right">
                <input
                  type="number"
                  step="0.0001"
                  min="0.0001"
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  className="h-8 w-28 rounded-md border border-input px-2 text-sm"
                />
              </TableCell>
              <TableCell className="space-x-2 text-right whitespace-nowrap">
                <Button size="sm" onClick={() => void handleSave(center.id)}>
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
            <TableRow key={center.id}>
              <TableCell className="font-medium">
                {center.name}
                <span className="ml-2 text-xs text-zinc-400">
                  {center.code}
                </span>
              </TableCell>
              <TableCell>
                {MACHINE_TYPE_TITLES[center.machine_type] ??
                  center.machine_type}
              </TableCell>
              <TableCell className="text-zinc-500">
                {center.group_code}
              </TableCell>
              <TableCell className="text-right">
                {center.machine_rate_per_min ?? "—"}
              </TableCell>
              {isAdmin && (
                <TableCell className="text-right">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => startEdit(center)}
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
  );
}
