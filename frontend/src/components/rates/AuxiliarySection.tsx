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
import type { AuxiliaryOperation } from "@/lib/types";

interface AuxiliarySectionProps {
  operations: AuxiliaryOperation[];
  isAdmin: boolean;
  onSave: (
    operationId: number,
    fixedTime: string,
    rate: string,
    isActive: boolean,
  ) => Promise<void>;
}

export function AuxiliarySection({
  operations,
  isAdmin,
  onSave,
}: AuxiliarySectionProps) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState({
    time: "",
    rate: "",
    active: false,
  });

  function startEdit(operation: AuxiliaryOperation) {
    setEditingId(operation.id);
    setDraft({
      time: operation.fixed_time_min,
      rate: operation.rate_per_min,
      active: operation.is_active,
    });
  }

  async function handleSave(operationId: number) {
    await onSave(operationId, draft.time, draft.rate, draft.active);
    setEditingId(null);
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Операция</TableHead>
          <TableHead className="text-right">Tфикс, мин</TableHead>
          <TableHead className="text-right">Ставка, ₽/мин</TableHead>
          <TableHead>Активна</TableHead>
          {isAdmin && <TableHead />}
        </TableRow>
      </TableHeader>
      <TableBody>
        {operations.map((operation) =>
          editingId === operation.id ? (
            <TableRow key={operation.id}>
              <TableCell className="font-medium">{operation.name}</TableCell>
              <TableCell className="text-right">
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={draft.time}
                  onChange={(e) =>
                    setDraft({ ...draft, time: e.target.value })
                  }
                  className="h-8 w-20 rounded-md border border-input px-2 text-sm"
                />
              </TableCell>
              <TableCell className="text-right">
                <input
                  type="number"
                  step="0.0001"
                  min="0"
                  value={draft.rate}
                  onChange={(e) =>
                    setDraft({ ...draft, rate: e.target.value })
                  }
                  className="h-8 w-24 rounded-md border border-input px-2 text-sm"
                />
              </TableCell>
              <TableCell>
                <input
                  type="checkbox"
                  checked={draft.active}
                  onChange={(e) =>
                    setDraft({ ...draft, active: e.target.checked })
                  }
                />
              </TableCell>
              <TableCell className="space-x-2 text-right whitespace-nowrap">
                <Button size="sm" onClick={() => void handleSave(operation.id)}>
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
              <TableCell className="text-right">
                {operation.fixed_time_min}
              </TableCell>
              <TableCell className="text-right">
                {operation.rate_per_min}
              </TableCell>
              <TableCell>{operation.is_active ? "да" : "нет"}</TableCell>
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
          ),
        )}
      </TableBody>
    </Table>
  );
}
