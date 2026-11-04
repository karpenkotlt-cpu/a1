"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { Step, TemplateType } from "@/lib/constructor-types";
import { useConstructorStore } from "@/stores/constructor";

const TEMPLATES: { type: TemplateType; title: string; hint: string }[] = [
  { type: "T1_STEPPED_SHAFT", title: "T1 Вал", hint: "ступенчатый вал / ось" },
  { type: "T2_BUSHING", title: "T2 Втулка", hint: "втулка / стакан / кольцо" },
  { type: "T3_FLANGE", title: "T3 Фланец", hint: "фланец / диск / крышка" },
  { type: "T4_PLATE", title: "T4 Плита", hint: "плита / планка / блок" },
  { type: "T5_HOUSING", title: "T5 Корпус", hint: "корпус / кронштейн (Kвыб)" },
];

function NumInput({
  label,
  value,
  onChange,
  step = 0.1,
  min = 0.1,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  step?: number;
  min?: number;
}) {
  return (
    <div className="space-y-1">
      <Label className="text-xs text-zinc-500">{label}</Label>
      <Input
        type="number"
        value={Number.isFinite(value) ? value : ""}
        step={step}
        min={min}
        onChange={(event) => {
          const parsed = Number(event.target.value);
          if (Number.isFinite(parsed)) onChange(parsed);
        }}
      />
    </div>
  );
}

function StepsEditor({
  title,
  steps,
  onChange,
  allowEmpty,
}: {
  title: string;
  steps: Step[];
  onChange: (steps: Step[]) => void;
  allowEmpty?: boolean;
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{title}</span>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => onChange([...steps, { diameter: 40, length: 20 }])}
        >
          + Ступень
        </Button>
      </div>
      {steps.length === 0 && (
        <p className="text-xs text-zinc-500">Нет ступеней</p>
      )}
      {steps.map((step, index) => (
        <div key={index} className="flex items-end gap-2">
          <div className="flex-1">
            <NumInput
              label="Ø, мм"
              value={step.diameter}
              onChange={(diameter) =>
                onChange(steps.map((s, i) => (i === index ? { ...s, diameter } : s)))
              }
            />
          </div>
          <div className="flex-1">
            <NumInput
              label="Длина, мм"
              value={step.length}
              onChange={(length) =>
                onChange(steps.map((s, i) => (i === index ? { ...s, length } : s)))
              }
            />
          </div>
          {(allowEmpty || steps.length > 1) && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="mb-1 text-red-600"
              onClick={() => onChange(steps.filter((_, i) => i !== index))}
            >
              ✕
            </Button>
          )}
        </div>
      ))}
    </div>
  );
}

export function TemplateForm() {
  const templateType = useConstructorStore((s) => s.templateType);
  const setTemplateType = useConstructorStore((s) => s.setTemplateType);
  const t1 = useConstructorStore((s) => s.t1);
  const setT1 = useConstructorStore((s) => s.setT1);
  const t2 = useConstructorStore((s) => s.t2);
  const setT2 = useConstructorStore((s) => s.setT2);
  const t3 = useConstructorStore((s) => s.t3);
  const setT3 = useConstructorStore((s) => s.setT3);
  const t4 = useConstructorStore((s) => s.t4);
  const setT4 = useConstructorStore((s) => s.setT4);
  const t5 = useConstructorStore((s) => s.t5);
  const setT5 = useConstructorStore((s) => s.setT5);

  return (
    <section className="space-y-4 rounded-xl border bg-white p-4">
      <h2 className="font-semibold">Шаблон детали</h2>
      <div className="grid grid-cols-2 gap-2">
        {TEMPLATES.map((template) => (
          <button
            key={template.type}
            type="button"
            onClick={() => setTemplateType(template.type)}
            className={`rounded-lg border p-2 text-left transition-colors ${
              templateType === template.type
                ? "border-zinc-900 bg-zinc-900 text-white"
                : "hover:bg-zinc-50"
            }`}
          >
            <div className="text-sm font-medium">{template.title}</div>
            <div
              className={`text-xs ${templateType === template.type ? "text-zinc-300" : "text-zinc-500"}`}
            >
              {template.hint}
            </div>
          </button>
        ))}
      </div>

      {templateType === "T1_STEPPED_SHAFT" && (
        <StepsEditor
          title="Ступени (слева направо)"
          steps={t1.steps}
          onChange={(steps) => setT1({ steps })}
        />
      )}
      {templateType === "T2_BUSHING" && (
        <div className="space-y-4">
          <StepsEditor
            title="Наружные ступени"
            steps={t2.outer_steps}
            onChange={(outer_steps) => setT2({ ...t2, outer_steps })}
          />
          <StepsEditor
            title="Расточка (от левого торца)"
            steps={t2.inner_steps}
            onChange={(inner_steps) => setT2({ ...t2, inner_steps })}
            allowEmpty
          />
        </div>
      )}
      {templateType === "T3_FLANGE" && (
        <div className="grid grid-cols-3 gap-2">
          <NumInput
            label="Ø внешний"
            value={t3.outer_diameter}
            onChange={(outer_diameter) => setT3({ ...t3, outer_diameter })}
          />
          <NumInput
            label="Толщина"
            value={t3.thickness}
            onChange={(thickness) => setT3({ ...t3, thickness })}
          />
          <NumInput
            label="Ø центральный"
            value={t3.center_hole_diameter}
            min={0}
            onChange={(center_hole_diameter) => setT3({ ...t3, center_hole_diameter })}
          />
        </div>
      )}
      {templateType === "T4_PLATE" && (
        <div className="grid grid-cols-3 gap-2">
          <NumInput
            label="Длина"
            value={t4.length}
            onChange={(length) => setT4({ ...t4, length })}
          />
          <NumInput
            label="Ширина"
            value={t4.width}
            onChange={(width) => setT4({ ...t4, width })}
          />
          <NumInput
            label="Высота"
            value={t4.height}
            onChange={(height) => setT4({ ...t4, height })}
          />
        </div>
      )}
      {templateType === "T5_HOUSING" && (
        <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
          <NumInput
            label="Длина"
            value={t5.length}
            onChange={(length) => setT5({ ...t5, length })}
          />
          <NumInput
            label="Ширина"
            value={t5.width}
            onChange={(width) => setT5({ ...t5, width })}
          />
          <NumInput
            label="Высота"
            value={t5.height}
            onChange={(height) => setT5({ ...t5, height })}
          />
          <NumInput
            label="Kвыб, %"
            value={Math.round(t5.removal_ratio * 100)}
            min={5}
            onChange={(percent) =>
              setT5({
                ...t5,
                removal_ratio: Math.min(0.95, Math.max(0.05, percent / 100)),
              })
            }
          />
        </div>
      )}
    </section>
  );
}
