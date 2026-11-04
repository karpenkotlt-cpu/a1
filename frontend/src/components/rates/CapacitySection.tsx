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
import type { CapacityLoadRow } from "@/lib/types";

function kmarginHint(utilization: number | null): string {
  if (utilization === null) return "Kmargin 1.0";
  if (utilization < 40) return "Kmargin 0.55 (простой → скидка)";
  if (utilization <= 80) return "Kmargin 1.0";
  if (utilization <= 95) return "Kmargin 1.35 (высокая загрузка)";
  return "Kmargin 2.0 (surge)";
}

interface CapacitySectionProps {
  rows: CapacityLoadRow[];
  isAdmin: boolean;
  onSave: (rowId: number, scheduled: string) => Promise<void>;
}

export function CapacitySection({
  rows,
  isAdmin,
  onSave,
}: CapacitySectionProps) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState("");

  function startEdit(row: CapacityLoadRow) {
    setEditingId(row.id);
    setDraft(row.scheduled_minutes);
  }

  async function handleSave(rowId: number) {
    await onSave(rowId, draft);
    setEditingId(null);
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Группа станков</TableHead>
          <TableHead className="text-right">Фонд, мин</TableHead>
          <TableHead className="text-right">Запланировано, мин</TableHead>
          <TableHead className="text-right">Загрузка</TableHead>
          <TableHead>Kmargin</TableHead>
          {isAdmin && <TableHead />}
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) =>
          editingId === row.id ? (
            <TableRow key={row.id}>
              <TableCell className="font-medium">{row.work_center_group}</TableCell>
              <TableCell className="text-right">{row.total_fund_minutes}</TableCell>
              <TableCell className="text-right">
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  className="h-8 w-32 rounded-md border border-input px-2 text-sm"
                />
              </TableCell>
              <TableCell colSpan={2} />
              <TableCell className="space-x-2 text-right whitespace-nowrap">
                <Button size="sm" onClick={() => void handleSave(row.id)}>
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
            <TableRow key={row.id}>
              <TableCell className="font-medium">{row.work_center_group}</TableCell>
              <TableCell className="text-right">{row.total_fund_minutes}</TableCell>
              <TableCell className="text-right">{row.scheduled_minutes}</TableCell>
              <TableCell className="text-right">
                {row.utilization_percent !== null
                  ? `${row.utilization_percent.toFixed(1)}%`
                  : "—"}
              </TableCell>
              <TableCell className="text-xs text-zinc-500">
                {kmarginHint(row.utilization_percent)}
              </TableCell>
              {isAdmin && (
                <TableCell className="text-right">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => startEdit(row)}
                  >
                    Изменить
                  </Button>
                </TableCell>
              )}
            </TableRow>
          ),
        )}
        {rows.length === 0 && (
          <TableRow>
            <TableCell colSpan={6} className="text-center text-zinc-500">
              Нет данных APS — все группы считаются с Kmargin 1.0
            </TableCell>
          </TableRow>
        )}
      </TableBody>
    </Table>
  );
}
