"use client";

import {
  SERVICE_TYPE_TITLES,
  type CooperationService,
} from "@/lib/types";
import { useConstructorStore } from "@/stores/constructor";

const UNIT_HINTS: Record<string, string> = {
  KG: "кол-во, кг (авто: масса)",
  DM2: "кол-во, дм² (авто: площадь)",
  METER: "кол-во, пог. м — укажите",
  PIECE: "кол-во, шт (авто: 1)",
};

const UNIT_SHORT: Record<string, string> = {
  KG: "кг",
  DM2: "дм²",
  METER: "м",
  PIECE: "шт",
};

export function CooperationPicker({
  services,
}: {
  services: CooperationService[];
}) {
  const selections = useConstructorStore((s) => s.cooperationSelections);
  const toggle = useConstructorStore((s) => s.toggleCooperation);
  const setQty = useConstructorStore((s) => s.setCooperationQty);

  if (services.length === 0) {
    return (
      <p className="text-xs text-zinc-400">
        Услуги кооперации не заведены — добавьте их в справочнике «Нормативы».
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {services.map((service) => {
        const selected = service.id in selections;
        return (
          <div key={service.id} className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={selected}
              onChange={() => toggle(service.id)}
            />
            <span className={selected ? "font-medium" : "text-zinc-600"}>
              {SERVICE_TYPE_TITLES[service.service_type] ??
                service.service_type}
              {service.contractor ? ` · ${service.contractor}` : ""}
            </span>
            <span className="text-xs text-zinc-400">
              {service.price_per_unit} ₽/
              {UNIT_SHORT[service.unit] ?? service.unit}
              {Number(service.min_lot_qty) > 0 && ` · MOQ ${service.min_lot_qty}`}
            </span>
            {selected && (
              <input
                type="number"
                step="0.001"
                min="0"
                placeholder={UNIT_HINTS[service.unit] ?? "кол-во"}
                value={selections[service.id] ?? ""}
                onChange={(e) => setQty(service.id, e.target.value)}
                className="ml-auto h-8 w-36 rounded-md border border-input px-2 text-sm"
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
