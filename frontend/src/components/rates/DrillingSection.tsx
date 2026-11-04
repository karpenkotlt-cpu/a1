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
import type { DrillingRate } from "@/lib/types";

interface DrillingSectionProps {
  rates: DrillingRate[];
  isAdmin: boolean;
  onSave: (rateId: number, carbide: string, hss: string) => Promise<void>;
}

export function DrillingSection({
  rates,
  isAdmin,
  onSave,
}: DrillingSectionProps) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState({ carbide: "", hss: "" });

  function startEdit(rate: DrillingRate) {
    setEditingId(rate.id);
    setDraft({
      carbide: rate.carbide_feed_mm_min,
      hss: rate.hss_feed_mm_min,
    });
  }

  async function handleSave(rateId: number) {
    await onSave(rateId, draft.carbide, draft.hss);
    setEditingId(null);
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Диапазон Ø, мм</TableHead>
          <TableHead className="text-right">Тв. сплав, мм/мин</TableHead>
          <TableHead className="text-right">HSS, мм/мин</TableHead>
          {isAdmin && <TableHead />}
        </TableRow>
      </TableHeader>
      <TableBody>
        {rates.map((rate) =>
          editingId === rate.id ? (
            <TableRow key={rate.id}>
              <TableCell className="font-medium">
                Ø{rate.diameter_from_mm}–{rate.diameter_to_mm}
              </TableCell>
              <TableCell className="text-right">
                <input
                  type="number"
                  step="0.1"
                  min="0.1"
                  value={draft.carbide}
                  onChange={(e) =>
                    setDraft({ ...draft, carbide: e.target.value })
                  }
                  className="h-8 w-24 rounded-md border border-input px-2 text-sm"
                />
              </TableCell>
              <TableCell className="text-right">
                <input
                  type="number"
                  step="0.1"
                  min="0.1"
                  value={draft.hss}
                  onChange={(e) => setDraft({ ...draft, hss: e.target.value })}
                  className="h-8 w-24 rounded-md border border-input px-2 text-sm"
                />
              </TableCell>
              <TableCell className="space-x-2 text-right whitespace-nowrap">
                <Button size="sm" onClick={() => void handleSave(rate.id)}>
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
            <TableRow key={rate.id}>
              <TableCell className="font-medium">
                Ø{rate.diameter_from_mm}–{rate.diameter_to_mm}
              </TableCell>
              <TableCell className="text-right">
                {rate.carbide_feed_mm_min}
              </TableCell>
              <TableCell className="text-right">
                {rate.hss_feed_mm_min}
              </TableCell>
              {isAdmin && (
                <TableCell className="text-right">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => startEdit(rate)}
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
