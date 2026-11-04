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
import type { CoefficientRow } from "@/lib/types";

const COEF_TYPE_TITLES: Record<string, string> = {
  TOLERANCE: "Квалитет",
  GEOMETRY: "Геометрия",
  MATERIAL: "Материал",
  BATCH: "Партия",
};

interface CoefficientsSectionProps {
  coefficients: CoefficientRow[];
  isAdmin: boolean;
  onSave: (coefficientId: number, multiplier: string) => Promise<void>;
}

export function CoefficientsSection({
  coefficients,
  isAdmin,
  onSave,
}: CoefficientsSectionProps) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState("");

  function startEdit(coefficient: CoefficientRow) {
    setEditingId(coefficient.id);
    setDraft(coefficient.multiplier);
  }

  async function handleSave(coefficientId: number) {
    await onSave(coefficientId, draft);
    setEditingId(null);
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Тип</TableHead>
          <TableHead>Код</TableHead>
          <TableHead className="text-right">Множитель</TableHead>
          <TableHead>Описание</TableHead>
          {isAdmin && <TableHead />}
        </TableRow>
      </TableHeader>
      <TableBody>
        {coefficients.map((coefficient) =>
          editingId === coefficient.id ? (
            <TableRow key={coefficient.id}>
              <TableCell>
                {COEF_TYPE_TITLES[coefficient.coef_type] ??
                  coefficient.coef_type}
              </TableCell>
              <TableCell className="font-medium">{coefficient.code}</TableCell>
              <TableCell className="text-right">
                <input
                  type="number"
                  step="0.001"
                  min="0.001"
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  className="h-8 w-24 rounded-md border border-input px-2 text-sm"
                />
              </TableCell>
              <TableCell>{coefficient.description ?? "—"}</TableCell>
              <TableCell className="space-x-2 text-right whitespace-nowrap">
                <Button size="sm" onClick={() => void handleSave(coefficient.id)}>
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
            <TableRow key={coefficient.id}>
              <TableCell>
                {COEF_TYPE_TITLES[coefficient.coef_type] ??
                  coefficient.coef_type}
              </TableCell>
              <TableCell className="font-medium">{coefficient.code}</TableCell>
              <TableCell className="text-right">
                {coefficient.multiplier}
              </TableCell>
              <TableCell>{coefficient.description ?? "—"}</TableCell>
              {isAdmin && (
                <TableCell className="text-right">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => startEdit(coefficient)}
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
