"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  TOLERANCE_OPTIONS,
  type ConstructorFeature,
  type HoleArrayFeature,
  type RectPocketFeature,
} from "@/lib/constructor-types";
import { useConstructorStore } from "@/stores/constructor";

function featureSummary(feature: ConstructorFeature): string {
  if (feature.type === "HOLE_ARRAY") {
    const through = feature.is_through ? "сквозные" : `гл. ${feature.depth}`;
    const thread = feature.thread ? `, ${feature.thread}` : "";
    const cb =
      feature.counterbore_diameter && feature.counterbore_depth
        ? `, цек. Ø${feature.counterbore_diameter}×${feature.counterbore_depth}`
        : "";
    return `${feature.count}×Ø${feature.diameter} ${through} · ${feature.tolerance}${thread}${cb}`;
  }
  return `${feature.count}× карман ${feature.length}×${feature.width}×${feature.depth} · ${feature.tolerance}`;
}

function HoleEditor({ feature }: { feature: HoleArrayFeature }) {
  const updateFeature = useConstructorStore((s) => s.updateFeature);
  return (
    <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
      <div className="space-y-1">
        <Label className="text-xs text-zinc-500">Кол-во</Label>
        <Input
          type="number"
          min={1}
          value={feature.count}
          onChange={(e) =>
            updateFeature(feature.id, { count: Number(e.target.value) || 1 })
          }
        />
      </div>
      <div className="space-y-1">
        <Label className="text-xs text-zinc-500">Ø, мм</Label>
        <Input
          type="number"
          step={0.1}
          min={0.5}
          value={feature.diameter}
          onChange={(e) =>
            updateFeature(feature.id, { diameter: Number(e.target.value) })
          }
        />
      </div>
      <div className="space-y-1">
        <Label className="text-xs text-zinc-500">Глубина, мм</Label>
        <Input
          type="number"
          step={0.1}
          min={0.1}
          disabled={feature.is_through}
          value={feature.depth}
          onChange={(e) =>
            updateFeature(feature.id, { depth: Number(e.target.value) })
          }
        />
      </div>
      <div className="space-y-1">
        <Label className="text-xs text-zinc-500">Квалитет</Label>
        <select
          value={feature.tolerance}
          onChange={(e) => updateFeature(feature.id, { tolerance: e.target.value })}
          className="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm"
        >
          {TOLERANCE_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </div>
      <div className="space-y-1">
        <Label className="text-xs text-zinc-500">Резьба</Label>
        <Input
          placeholder="M6"
          value={feature.thread ?? ""}
          onChange={(e) =>
            updateFeature(feature.id, {
              thread: e.target.value === "" ? null : e.target.value,
            })
          }
        />
      </div>
      <div className="space-y-1">
        <Label className="text-xs text-zinc-500">Ø цековки</Label>
        <Input
          type="number"
          step={0.1}
          placeholder="—"
          value={feature.counterbore_diameter ?? ""}
          onChange={(e) =>
            updateFeature(feature.id, {
              counterbore_diameter:
                e.target.value === "" ? null : Number(e.target.value),
            })
          }
        />
      </div>
      <div className="space-y-1">
        <Label className="text-xs text-zinc-500">Глуб. цековки</Label>
        <Input
          type="number"
          step={0.1}
          placeholder="—"
          value={feature.counterbore_depth ?? ""}
          onChange={(e) =>
            updateFeature(feature.id, {
              counterbore_depth:
                e.target.value === "" ? null : Number(e.target.value),
            })
          }
        />
      </div>
      <div className="space-y-1">
        <Label className="text-xs text-zinc-500">Тип сверла</Label>
        <select
          value={feature.drill_type ?? "CARBIDE"}
          onChange={(e) =>
            updateFeature(feature.id, {
              drill_type: e.target.value as "CARBIDE" | "HSS",
            })
          }
          className="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm"
        >
          <option value="CARBIDE">Тв. сплав (монолит)</option>
          <option value="HSS">Быстрорез (HSS)</option>
        </select>
      </div>
      <label className="flex items-end gap-2 pb-2 text-sm">
        <input
          type="checkbox"
          checked={feature.is_through}
          onChange={(e) =>
            updateFeature(feature.id, { is_through: e.target.checked })
          }
        />
        Сквозные
      </label>
    </div>
  );
}

function PocketEditor({ feature }: { feature: RectPocketFeature }) {
  const updateFeature = useConstructorStore((s) => s.updateFeature);
  return (
    <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
      <div className="space-y-1">
        <Label className="text-xs text-zinc-500">Кол-во</Label>
        <Input
          type="number"
          min={1}
          value={feature.count}
          onChange={(e) =>
            updateFeature(feature.id, { count: Number(e.target.value) || 1 })
          }
        />
      </div>
      <div className="space-y-1">
        <Label className="text-xs text-zinc-500">Длина, мм</Label>
        <Input
          type="number"
          step={0.1}
          value={feature.length}
          onChange={(e) =>
            updateFeature(feature.id, { length: Number(e.target.value) })
          }
        />
      </div>
      <div className="space-y-1">
        <Label className="text-xs text-zinc-500">Ширина, мм</Label>
        <Input
          type="number"
          step={0.1}
          value={feature.width}
          onChange={(e) =>
            updateFeature(feature.id, { width: Number(e.target.value) })
          }
        />
      </div>
      <div className="space-y-1">
        <Label className="text-xs text-zinc-500">Глубина, мм</Label>
        <Input
          type="number"
          step={0.1}
          value={feature.depth}
          onChange={(e) =>
            updateFeature(feature.id, { depth: Number(e.target.value) })
          }
        />
      </div>
      <div className="space-y-1">
        <Label className="text-xs text-zinc-500">Квалитет</Label>
        <select
          value={feature.tolerance}
          onChange={(e) => updateFeature(feature.id, { tolerance: e.target.value })}
          className="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm"
        >
          {TOLERANCE_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

export function FeatureTree() {
  const features = useConstructorStore((s) => s.features);
  const addFeature = useConstructorStore((s) => s.addFeature);
  const updateFeature = useConstructorStore((s) => s.updateFeature);
  const removeFeature = useConstructorStore((s) => s.removeFeature);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  return (
    <section className="space-y-3 rounded-xl border bg-white p-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">Фичи-модификаторы</h2>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => {
              const id = crypto.randomUUID();
              addFeature({
                type: "HOLE_ARRAY",
                id,
                enabled: true,
                count: 4,
                diameter: 11,
                depth: 20,
                is_through: false,
                tolerance: "IT11",
                thread: null,
                counterbore_diameter: null,
                counterbore_depth: null,
                drill_type: "CARBIDE",
              });
              setExpandedId(id);
            }}
          >
            + Отверстия
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => {
              const id = crypto.randomUUID();
              addFeature({
                type: "RECT_POCKET",
                id,
                enabled: true,
                count: 1,
                length: 40,
                width: 25,
                depth: 10,
                tool_diameter: 10,
                tolerance: "IT11",
              });
              setExpandedId(id);
            }}
          >
            + Карман
          </Button>
        </div>
      </div>

      {features.length === 0 && (
        <p className="text-sm text-zinc-500">
          Добавьте отверстия или карманы — каждая фича уменьшает объём и добавляет
          операции.
        </p>
      )}

      <div className="space-y-2">
        {features.map((feature) => (
          <div key={feature.id} className="rounded-lg border p-2">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={feature.enabled}
                onChange={(e) =>
                  updateFeature(feature.id, { enabled: e.target.checked })
                }
                title="Учитывать в расчёте"
              />
              <button
                type="button"
                className="flex-1 text-left text-sm"
                onClick={() =>
                  setExpandedId(expandedId === feature.id ? null : feature.id)
                }
              >
                {featureSummary(feature)}
              </button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="text-red-600"
                onClick={() => removeFeature(feature.id)}
              >
                Удалить
              </Button>
            </div>
            {expandedId === feature.id &&
              (feature.type === "HOLE_ARRAY" ? (
                <HoleEditor feature={feature} />
              ) : (
                <PocketEditor feature={feature} />
              ))}
          </div>
        ))}
      </div>
    </section>
  );
}
