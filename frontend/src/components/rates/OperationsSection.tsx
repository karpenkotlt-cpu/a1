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
import type { OperationRate, OperationRow } from "@/lib/types";

const inputClass =
  "h-8 w-24 rounded-md border border-input px-2 text-sm";

interface OperationsSectionProps {
  operations: OperationRow[];
  isAdmin: boolean;
  onSaveSetup: (operationId: number, setupTime: string) => Promise<void>;
  onSaveRate: (rateId: number, q: string, s: string) => Promise<void>;
}

interface Draft {
  setup: string;
  q: string;
  s: string;
}

function baseRate(operation: OperationRow): OperationRate | null {
  return (
    operation.rates.find((r) => r.material_iso_group === "P") ??
    operation.rates[0] ??
    null
  );
}

export function OperationsSection({
  operations,
  isAdmin,
  onSaveSetup,
  onSaveRate,
}: OperationsSectionProps) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState<Draft>({ setup: "", q: "", s: "" });

  function startEdit(operation: OperationRow) {
    const rate = baseRate(operation);
    setEditingId(operation.id);
    setDraft({
      setup: operation.setup_time_base_min,
      q: rate?.q_rough_cm3_min ?? "",
      s: rate?.s_finish_dm2_min ?? "",
    });
  }

  async function handleSave(operation: OperationRow) {
    await onSaveSetup(operation.id, draft.setup);
    const rate = baseRate(operation);
    if (rate) {
      await onSaveRate(rate.id, draft.q, draft.s);
    }
    setEditingId(null);
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Операция</TableHead>
          <TableHead>Группа станков</TableHead>
          <TableHead className="text-right">Tпз, мин</TableHead>
          <TableHead className="text-right">Q (P), см³/мин</TableHead>
          <TableHead className="text-right">S (P), дм²/мин</TableHead>
          {isAdmin && <TableHead />}
        </TableRow>
      </TableHeader>
      <TableBody>
        {operations.map((operation) => {
          const rate = baseRate(operation);
          return editingId === operation.id ? (
            <TableRow key={operation.id}>
              <TableCell className="font-medium">{operation.name}</TableCell>
              <TableCell className="text-zinc-500">
                {operation.work_center_group}
              </TableCell>
              <TableCell className="text-right">
                <input
                  type="number"
                  step="0.5"
                  min="0"
                  value={draft.setup}
                  onChange={(e) =>
                    setDraft({ ...draft, setup: e.target.value })
                  }
                  className={inputClass}
                />
              </TableCell>
              <TableCell className="text-right">
                <input
                  type="number"
                  step="0.001"
                  min="0.001"
                  value={draft.q}
                  onChange={(e) => setDraft({ ...draft, q: e.target.value })}
                  className={inputClass}
                  disabled={!rate}
                />
              </TableCell>
              <TableCell className="text-right">
                <input
                  type="number"
                  step="0.001"
                  min="0.001"
                  value={draft.s}
                  onChange={(e) => setDraft({ ...draft, s: e.target.value })}
                  className={inputClass}
                  disabled={!rate}
                />
              </TableCell>
              <TableCell className="space-x-2 text-right whitespace-nowrap">
                <Button size="sm" onClick={() => void handleSave(operation)}>
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
            <TableRow key={operation.id}>
              <TableCell className="font-medium">
                {operation.name}
                <span className="ml-2 text-xs text-zinc-400">
                  {operation.code}
                </span>
              </TableCell>
              <TableCell className="text-zinc-500">
                {operation.work_center_group}
              </TableCell>
              <TableCell className="text-right">
                {operation.setup_time_base_min}
              </TableCell>
              <TableCell className="text-right">
                {rate ? rate.q_rough_cm3_min : "—"}
              </TableCell>
              <TableCell className="text-right">
                {rate ? rate.s_finish_dm2_min : "—"}
              </TableCell>
              {isAdmin && (
                <TableCell className="text-right">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => startEdit(operation)}
                  >
                    Изменить
                  </Button>
                </TableCell>
              )}
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
