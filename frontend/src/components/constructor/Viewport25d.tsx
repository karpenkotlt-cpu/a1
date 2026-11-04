"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { Canvas } from "@react-three/fiber";
import {
  Bounds,
  GizmoHelper,
  GizmoViewport,
  Grid,
  OrbitControls,
} from "@react-three/drei";
import { Brush, Evaluator, SUBTRACTION } from "three-bvh-csg";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";

import { ApiError, apiFetch } from "@/lib/api";
import { buildPreview, type PreviewSpec } from "@/lib/geometry25d";
import {
  extractCentralBore,
  extractScadFeatures,
  type HoleCandidate,
} from "@/lib/scadFeatureExtractor";
import { generateScadFromStore } from "@/lib/scadGenerator";
import {
  extractCustomizerParams,
  updateScadVariable,
} from "@/lib/scadCustomizer";
import type { ConstructorMode, ScadPreviewMeta } from "@/lib/constructor-types";
import { useAuthStore } from "@/stores/auth";
import { useConstructorStore } from "@/stores/constructor";

const MODES: { value: ConstructorMode; label: string; title: string }[] = [
  { value: "TEMPLATE", label: "Шаблон", title: "Ползунки шаблона (как раньше)" },
  {
    value: "SCAD_CUSTOMIZER",
    label: "SCAD-ползунки",
    title: "Код OpenSCAD генерируется из шаблона, правится ползунками",
  },
  {
    value: "SCAD_RAW_CODE",
    label: "SCAD-код",
    title: "Произвольный код OpenSCAD",
  },
];

function PartMesh({ spec }: { spec: PreviewSpec }) {
  const { geometry, edges } = useMemo(() => {
    const model = buildPreview(spec);
    let brush = new Brush(model.part);
    brush.updateMatrixWorld();
    const evaluator = new Evaluator();
    evaluator.useGroups = false;
    for (const cutter of model.cutters) {
      const cutterBrush = new Brush(cutter);
      cutterBrush.updateMatrixWorld();
      brush = evaluator.evaluate(brush, cutterBrush, SUBTRACTION);
      brush.updateMatrixWorld();
    }
    const result = brush.geometry as unknown as THREE.BufferGeometry;
    result.computeVertexNormals();
    return { geometry: result, edges: new THREE.EdgesGeometry(result, 25) };
  }, [spec]);

  return (
    <>
      <mesh geometry={geometry}>
        <meshStandardMaterial color="#a1a1aa" metalness={0.3} roughness={0.45} />
      </mesh>
      <lineSegments geometry={edges}>
        <lineBasicMaterial color="#18181b" transparent opacity={0.55} />
      </lineSegments>
    </>
  );
}

/** Меш из STL серверной компиляции OpenSCAD.
 *
 * Система координат: OpenSCAD — Z вверх, three.js — Y вверх, поэтому
 * базовый разворот rotateX(-90°). Меш всегда ставится НА сетку
 * (min Y = 0) и центрируется по X/Z — при любом повороте.
 */
function ScadPartMesh({
  stlBase64,
  spin,
}: {
  stlBase64: string;
  spin: [number, number, number];
}) {
  // Парсинг — один раз на STL; тяжёлый atob+STLLoader не повторяется
  // при поворотах.
  const base = useMemo(() => {
    const binary = atob(stlBase64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) {
      bytes[i] = binary.charCodeAt(i);
    }
    const parsed = new STLLoader().parse(bytes.buffer);
    parsed.rotateX(-Math.PI / 2); // SCAD Z-up -> three.js Y-up
    parsed.computeVertexNormals();
    return parsed;
  }, [stlBase64]);

  const { geometry, edges } = useMemo(() => {
    const display = base.clone();
    if (spin[0] || spin[1] || spin[2]) {
      display.applyQuaternion(
        new THREE.Quaternion().setFromEuler(
          new THREE.Euler(spin[0], spin[1], spin[2], "XYZ"),
        ),
      );
    }
    // Опора на сетку: min.y = 0, центр по X/Z
    display.computeBoundingBox();
    const box = display.boundingBox ?? new THREE.Box3();
    const center = box.getCenter(new THREE.Vector3());
    display.translate(-center.x, -box.min.y, -center.z);
    return { geometry: display, edges: new THREE.EdgesGeometry(display, 25) };
  }, [base, spin]);

  useEffect(
    () => () => {
      base.dispose();
    },
    [base],
  );

  useEffect(
    () => () => {
      geometry.dispose();
      edges.dispose();
    },
    [geometry, edges],
  );

  return (
    <>
      <mesh geometry={geometry}>
        <meshStandardMaterial color="#a1a1aa" metalness={0.3} roughness={0.45} />
      </mesh>
      <lineSegments geometry={edges}>
        <lineBasicMaterial color="#18181b" transparent opacity={0.55} />
      </lineSegments>
    </>
  );
}

interface ScadPreviewResponse {
  stl_base64: string;
  bbox_mm: number[];
  v_net_cm3: number;
  compile_ms: number;
}

function applyHoleCandidate(candidate: HoleCandidate) {
  useConstructorStore.getState().addFeature({
    type: "HOLE_ARRAY",
    id: crypto.randomUUID(),
    enabled: true,
    count: candidate.count,
    diameter: candidate.diameter,
    depth: candidate.depth,
    is_through: candidate.isThrough,
    tolerance: "IT11",
    thread: null,
    counterbore_diameter: null,
    counterbore_depth: null,
    drill_type: candidate.drillType,
  });
}

function snapshotForGenerator() {
  const s = useConstructorStore.getState();
  return {
    templateType: s.templateType,
    t1: s.t1,
    t2: s.t2,
    t3: s.t3,
    t4: s.t4,
    t5: s.t5,
    features: s.features,
  };
}

export default function Viewport25d() {
  const templateType = useConstructorStore((s) => s.templateType);
  const t1 = useConstructorStore((s) => s.t1);
  const t2 = useConstructorStore((s) => s.t2);
  const t3 = useConstructorStore((s) => s.t3);
  const t4 = useConstructorStore((s) => s.t4);
  const t5 = useConstructorStore((s) => s.t5);
  const features = useConstructorStore((s) => s.features);

  const mode = useConstructorStore((s) => s.mode);
  const setMode = useConstructorStore((s) => s.setMode);
  const scadCode = useConstructorStore((s) => s.scadCode);
  const setScadCode = useConstructorStore((s) => s.setScadCode);
  const scadStl = useConstructorStore((s) => s.scadStl);
  const scadMeta = useConstructorStore((s) => s.scadMeta);
  const scadError = useConstructorStore((s) => s.scadError);
  const setScadPreview = useConstructorStore((s) => s.setScadPreview);
  const setScadError = useConstructorStore((s) => s.setScadError);
  const token = useAuthStore((s) => s.token);

  const [capability, setCapability] = useState<boolean | null>(null);
  const [dismissedCandidates, setDismissedCandidates] = useState<
    string | null
  >(null);
  // Ориентация модели во вьюпорте (Euler XYZ, рад): шаги по 90°;
  // поворот косметический — bbox для расчёта остаётся из OpenSCAD-осей
  const [scadSpin, setScadSpin] = useState<[number, number, number]>([
    0,
    0,
    0,
  ]);
  const previewSeq = useRef(0);

  useEffect(() => {
    // Публичный capability: нет бинарника/kill-switch → прячем SCAD-режимы
    apiFetch<{ scad_available: boolean }>("/scad/capability", null)
      .then((res) => setCapability(res.scad_available))
      .catch(() => setCapability(false));
  }, []);

  const spec = useMemo<PreviewSpec>(
    () => ({ templateType, t1, t2, t3, t4, t5, features }),
    [templateType, t1, t2, t3, t4, t5, features],
  );

  // Вход в SCAD_CUSTOMIZER с пустым кодом: генерируем из текущего шаблона
  useEffect(() => {
    if (mode !== "SCAD_CUSTOMIZER") return;
    const state = useConstructorStore.getState();
    if (!state.scadCode.trim()) {
      state.setScadCode(generateScadFromStore(snapshotForGenerator()));
    }
  }, [mode]);

  // Debounce-превью SCAD: перетаскивание ползунка не штормит сервер
  useEffect(() => {
    if (mode === "TEMPLATE" || !scadCode.trim()) return;
    const current = ++previewSeq.current;
    const timer = setTimeout(() => {
      apiFetch<ScadPreviewResponse>("/scad/preview", token, {
        method: "POST",
        body: { scad_code: scadCode },
      })
        .then((res) => {
          if (previewSeq.current !== current) return;
          const meta: ScadPreviewMeta = {
            bbox_mm: res.bbox_mm,
            v_net_cm3: res.v_net_cm3,
            compile_ms: res.compile_ms,
          };
          setScadPreview(res.stl_base64, meta);
        })
        .catch((err: unknown) => {
          if (previewSeq.current !== current) return;
          setScadError(
            err instanceof ApiError ? err.message : "Ошибка компиляции SCAD",
          );
        });
    }, 400);
    return () => clearTimeout(timer);
  }, [mode, scadCode, token, setScadPreview, setScadError]);

  const isTemplate = mode === "TEMPLATE";
  const params = useMemo(
    () => (mode === "SCAD_CUSTOMIZER" ? extractCustomizerParams(scadCode) : []),
    [mode, scadCode],
  );

  const extraction = useMemo(
    () => (isTemplate ? null : extractScadFeatures(scadCode)),
    [isTemplate, scadCode],
  );
  const bore = useMemo(
    () => (isTemplate ? null : extractCentralBore(scadCode)),
    [isTemplate, scadCode],
  );

  // Явные @feature-теги применяются сразу — без дублирования существующих
  useEffect(() => {
    if (!extraction || extraction.tagged.length === 0) return;
    const existing = useConstructorStore
      .getState()
      .features.filter((f) => f.type === "HOLE_ARRAY");
    for (const tag of extraction.tagged) {
      const duplicate = existing.some(
        (f) =>
          f.type === "HOLE_ARRAY" &&
          f.count === tag.count &&
          Math.abs(f.diameter - tag.diameter) < 0.01 &&
          Math.abs(f.depth - tag.depth) < 0.01,
      );
      if (!duplicate) applyHoleCandidate(tag);
    }
  }, [extraction]);

  // Эвристические кандидаты — только через баннер, никогда молча
  const heuristic =
    mode === "SCAD_RAW_CODE" ? (extraction?.heuristic ?? []) : [];
  const heuristicKey = heuristic
    .map((h) => `${h.count}x${h.diameter}x${h.depth}`)
    .join("|");
  const showCandidateBanner =
    heuristic.length > 0 && dismissedCandidates !== heuristicKey;

  return (
    <div className="relative h-full">
      <div className="absolute top-2 left-2 z-10 flex gap-1 rounded-md border bg-white/90 p-1 shadow-sm backdrop-blur">
        {MODES.map((item) => {
          const disabled =
            item.value !== "TEMPLATE" && capability === false;
          return (
            <button
              key={item.value}
              type="button"
              title={disabled ? "OpenSCAD недоступен на сервере" : item.title}
              disabled={disabled}
              onClick={() => setMode(item.value)}
              className={`rounded px-2 py-1 text-xs transition-colors ${
                mode === item.value
                  ? "bg-zinc-900 text-white"
                  : "text-zinc-600 hover:bg-zinc-100"
              } ${disabled ? "cursor-not-allowed opacity-40" : ""}`}
            >
              {item.label}
            </button>
          );
        })}
      </div>

      {capability === false && (
        <div className="absolute top-2 left-1/2 z-10 -translate-x-1/2 rounded border border-amber-200 bg-amber-50 px-3 py-1 text-xs text-amber-700">
          OpenSCAD недоступен на сервере — работает только режим «Шаблон»
        </div>
      )}

      <Canvas camera={{ position: [260, 200, 260], near: 1, far: 20000 }}>
        <ambientLight intensity={0.7} />
        <directionalLight position={[300, 500, 200]} intensity={1.4} />
        <directionalLight position={[-300, 200, -200]} intensity={0.4} />
        <Bounds fit clip observe margin={1.4}>
          {isTemplate ? (
            <PartMesh spec={spec} />
          ) : scadStl ? (
            <ScadPartMesh stlBase64={scadStl} spin={scadSpin} />
          ) : null}
        </Bounds>
        <Grid
          infiniteGrid
          cellSize={10}
          sectionSize={50}
          fadeDistance={4000}
          cellColor="#d4d4d8"
          sectionColor="#a1a1aa"
        />
        <OrbitControls makeDefault />
        <GizmoHelper alignment="bottom-right" margin={[56, 56]}>
          <GizmoViewport
            axisColors={["#c2410c", "#15803d", "#1d4ed8"]}
            labelColor="white"
          />
        </GizmoHelper>
      </Canvas>

      {!isTemplate && (
        <div className="absolute inset-x-2 bottom-2 z-10 rounded-md border bg-white/95 p-2 shadow-sm backdrop-blur">
          {showCandidateBanner && (
            <div className="mb-2 flex items-center justify-between gap-2 rounded border border-blue-200 bg-blue-50 px-2 py-1 text-xs text-blue-800">
              <span>
                Найдено переходов:{" "}
                {heuristic
                  .map((h) => `${h.count}×Ø${h.diameter}×${h.depth} мм`)
                  .join(", ")}{" "}
                — применить к расчёту?
              </span>
              <span className="flex shrink-0 gap-1">
                <button
                  type="button"
                  className="rounded border border-blue-300 bg-white px-2 py-0.5 hover:bg-blue-100"
                  onClick={() => {
                    heuristic.forEach(applyHoleCandidate);
                    setDismissedCandidates(heuristicKey);
                  }}
                >
                  Применить
                </button>
                <button
                  type="button"
                  className="rounded border px-2 py-0.5 hover:bg-zinc-100"
                  onClick={() => setDismissedCandidates(heuristicKey)}
                >
                  Игнорировать
                </button>
              </span>
            </div>
          )}
          {scadError && (
            <p className="mb-2 rounded bg-red-50 px-2 py-1 font-mono text-[11px] text-red-600">
              {scadError}
            </p>
          )}
          {mode === "SCAD_CUSTOMIZER" && (
            <div className="max-h-32 space-y-1 overflow-y-auto">
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-zinc-400">
                  Код синхронизирован с шаблоном при генерации; правки
                  ползунками не перезаписывают его
                </span>
                <button
                  type="button"
                  title="Перестроить код из текущих параметров шаблона и фич (заменит правки)"
                  onClick={() =>
                    useConstructorStore
                      .getState()
                      .setScadCode(generateScadFromStore(snapshotForGenerator()))
                  }
                  className="ml-2 shrink-0 rounded border px-2 py-0.5 text-[11px] text-zinc-600 hover:bg-zinc-100"
                >
                  ↻ Регенерировать
                </button>
              </div>
              {params.length === 0 && (
                <p className="text-xs text-zinc-400">
                  В коде нет переменных с комментариями вида{" "}
                  <code>{"// [min:шаг:max] Лейбл"}</code>
                </p>
              )}
              {params.map((param) => (
                <label
                  key={param.name}
                  className="flex items-center gap-2 text-xs text-zinc-600"
                >
                  <span className="w-40 shrink-0 truncate" title={param.name}>
                    {param.label}
                  </span>
                  <input
                    type="range"
                    min={param.min ?? 0}
                    max={param.max ?? Math.max(param.value * 2, 100)}
                    step={param.step ?? 1}
                    value={param.value}
                    onChange={(event) =>
                      setScadCode(
                        updateScadVariable(
                          scadCode,
                          param.name,
                          Number(event.target.value),
                        ),
                      )
                    }
                    className="flex-1"
                  />
                  <span className="w-14 shrink-0 text-right font-mono">
                    {param.value}
                  </span>
                </label>
              ))}
            </div>
          )}
          {mode === "SCAD_RAW_CODE" && (
            <textarea
              value={scadCode}
              onChange={(event) => setScadCode(event.target.value)}
              spellCheck={false}
              placeholder="// Код OpenSCAD, например:&#10;cylinder(h=10, d=20, $fn=96);"
              className="h-28 w-full resize-none rounded border bg-zinc-50 p-2 font-mono text-[11px] text-zinc-800 outline-none focus:border-zinc-400"
            />
          )}
          {scadMeta && (
            <p className="mt-1 text-[11px] text-zinc-400">
              v_net {scadMeta.v_net_cm3.toFixed(2)} см³ · bbox{" "}
              {scadMeta.bbox_mm.map((v) => v.toFixed(0)).join("×")} мм ·{" "}
              {scadMeta.compile_ms} мс
            </p>
          )}
          {scadStl && (
            <div className="mt-1 flex items-center gap-1 text-[11px] text-zinc-500">
              <span className="text-zinc-400">Ориентация:</span>
              {(["X", "Y", "Z"] as const).map((axis, idx) => (
                <button
                  key={axis}
                  type="button"
                  title={`Повернуть на 90° вокруг ${axis} (деталь всегда ставится на сетку)`}
                  onClick={() =>
                    setScadSpin((s) => {
                      const next: [number, number, number] = [...s];
                      next[idx] += Math.PI / 2;
                      return next;
                    })
                  }
                  className="rounded border px-2 py-0.5 hover:bg-zinc-100"
                >
                  ↻{axis}
                </button>
              ))}
              <button
                type="button"
                onClick={() => setScadSpin([0, 0, 0])}
                className="rounded border px-2 py-0.5 hover:bg-zinc-100"
              >
                Сброс
              </button>
            </div>
          )}
          {extraction && (
            <p className="mt-1 text-[11px] text-zinc-500">
              Авто-маршрут:{" "}
              {extraction.family === "TURNING"
                ? "токарная"
                : extraction.family === "PRISMATIC"
                  ? "фрезерная"
                  : "не определён — шаблон из формы"}
              {bore
                ? ` · расточка Ø${Math.round(bore.diameter)}×${Math.round(bore.length)} → T2`
                : extraction.hasCentralBore
                  ? " · расточка → T2 (размеры из формы)"
                  : ""}
              {" · заготовка (v_gross) подбирается из bbox автоматически"}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
