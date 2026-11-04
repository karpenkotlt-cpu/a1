/**
 * Экстрактор технологических признаков из SCAD-кода.
 *
 * Два уровня доверия (регексп по чужому коду ошибается — молчаливая
 * перезапись user-фич ломает доверие и расчёт):
 *
 * 1. Явные теги — применяются сразу:
 *    `// @feature HOLE_ARRAY count=6 d=11 depth=20 through=true drill=CARBIDE`
 *
 * 2. Best-effort эвристика — только через баннер подтверждения:
 *    вычитаемые cylinder(...) внутри difference() с for(i=[0:n-1]) —
 *    кандидаты на сверловку; осевой цилиндр — маркер расточки (T2).
 */

export type OperationFamily = "TURNING" | "PRISMATIC" | "UNKNOWN";

export interface HoleCandidate {
  count: number;
  diameter: number;
  depth: number;
  isThrough: boolean;
  drillType: "CARBIDE" | "HSS";
}

export interface ScadExtraction {
  /** Из @feature-тегов: применяются без подтверждения. */
  tagged: HoleCandidate[];
  /** Эвристические кандидаты: только по явному «Применить». */
  heuristic: HoleCandidate[];
  /** Осевой вычитаемый цилиндр → шаблон T2 (INNER_OPERATION). */
  hasCentralBore: boolean;
  family: OperationFamily;
}

const TAG_PATTERN = /@feature\s+HOLE_ARRAY\b([^\n]*)/g;
const FOR_COUNT_MINUS_ONE = /\[\s*0\s*:\s*(\d+)\s*-\s*1\s*\]/;
const FOR_COUNT_INCLUSIVE = /\[\s*0\s*:\s*(\d+)\s*\]/;
const CYLINDER_ARGS = /cylinder\s*\(\s*([^)]*)\)/g;

function parseArgs(raw: string): Record<string, string> {
  const args: Record<string, string> = {};
  for (const match of raw.matchAll(/([A-Za-z_]\w*)\s*=\s*([^\s,)]+)/g)) {
    args[match[1]] = match[2];
  }
  return args;
}

function numberArg(
  args: Record<string, string>,
  key: string,
  fallback: number,
): number {
  const value = Number.parseFloat(args[key] ?? "");
  return Number.isFinite(value) && value > 0 ? value : fallback;
}

function sameHole(a: HoleCandidate, b: HoleCandidate): boolean {
  return (
    a.count === b.count &&
    Math.abs(a.diameter - b.diameter) < 0.01 &&
    Math.abs(a.depth - b.depth) < 0.01
  );
}

function parseTagLine(rest: string): HoleCandidate | null {
  const args = parseArgs(rest);
  const diameter = numberArg(args, "d", Number.NaN);
  if (!Number.isFinite(diameter)) return null;
  const depth = numberArg(args, "depth", Number.NaN);
  if (!Number.isFinite(depth)) return null;
  return {
    count: Math.max(1, Math.round(numberArg(args, "count", 1))),
    diameter,
    depth,
    isThrough: args.through === "true",
    drillType: args.drill === "HSS" ? "HSS" : "CARBIDE",
  };
}

/** Осевой вычитаемый цилиндр: без смещения XY у корня difference(). */
export function detectCentralBore(code: string): boolean {
  const root = /difference\s*\(\s*\)\s*\{/.exec(code);
  if (!root) return false;
  const tail = code.slice(root.index, root.index + 600);
  return /(?:^|\n)\s*(?:translate\(\[\s*0\s*,\s*0\s*[^\]]*\]\s*)?cylinder\s*\(/.test(
    tail,
  );
}

/**
 * Размеры центральной расточки из кода (только литералы:
 * `cylinder(h=80, d=60)` у корня difference). Выражения вида
 * `h = il1 + 2` не парсятся — нужен детект по наличию (см.
 * detectCentralBore) и размеры из формы шаблона.
 */
export function extractCentralBore(
  code: string,
): { diameter: number; length: number } | null {
  const root = /difference\s*\(\s*\)\s*\{/.exec(code);
  if (!root) return null;
  const tail = code.slice(root.index, root.index + 600);
  const match =
    /(?:^|\n)\s*(?:translate\(\[\s*0\s*,\s*0\s*(?:,[^\]]*)?\]\s*)?cylinder\s*\(([^)]*)\)/.exec(
      tail,
    );
  if (!match) return null;
  const args = parseArgs(match[1] ?? "");
  const diameter = args.d
    ? Number.parseFloat(args.d)
    : args.r
      ? Number.parseFloat(args.r) * 2
      : Number.NaN;
  const length = args.h ? Number.parseFloat(args.h) : Number.NaN;
  if (
    !Number.isFinite(diameter) ||
    diameter <= 0 ||
    !Number.isFinite(length) ||
    length <= 0
  ) {
    return null;
  }
  return { diameter, length };
}

/** Группа операций: тела вращения → токарная, кубы/выдавливание → фрезерная. */
export function detectOperationFamily(code: string): OperationFamily {
  const turning = /\b(rotate_extrude|cylinder)\s*\(/.test(code);
  const prismatic = /\b(cube|linear_extrude|square|polygon)\s*\(/.test(code);
  if (turning && !prismatic) return "TURNING";
  if (prismatic && !turning) return "PRISMATIC";
  if (turning && prismatic) return "PRISMATIC";
  return "UNKNOWN";
}

export function extractScadFeatures(code: string): ScadExtraction {
  const tagged: HoleCandidate[] = [];
  for (const match of code.matchAll(TAG_PATTERN)) {
    const hole = parseTagLine(match[1] ?? "");
    if (hole) tagged.push(hole);
  }

  // Эвристика: difference()-блок + цикл for + вычитаемый cylinder
  const heuristic: HoleCandidate[] = [];
  const differenceRoot = /difference\s*\(\s*\)\s*\{/.exec(code);
  if (differenceRoot) {
    const block = code.slice(
      differenceRoot.index,
      differenceRoot.index + 2000,
    );
    const loops = [
      ...block.matchAll(/for\s*\(\s*\w+\s*=\s*(\[[^\]]*\])\s*\)/g),
    ].map((m) => m[1] ?? "");
    for (const range of loops) {
      let count = 0;
      const minusOne = FOR_COUNT_MINUS_ONE.exec(range);
      const inclusive = FOR_COUNT_INCLUSIVE.exec(range);
      if (minusOne) {
        count = Number.parseInt(minusOne[1], 10);
      } else if (inclusive) {
        count = Number.parseInt(inclusive[1], 10) + 1;
      }
      if (!count) continue;
      const cylinder = CYLINDER_ARGS.exec(block);
      if (!cylinder) continue;
      const args = parseArgs(cylinder[1] ?? "");
      const diameter = numberArg(args, "d", args.r ? Number.parseFloat(args.r) * 2 : Number.NaN);
      if (!Number.isFinite(diameter) || diameter <= 0) continue;
      const depth = numberArg(args, "h", Number.NaN);
      if (!Number.isFinite(depth)) continue;
      const candidate: HoleCandidate = {
        count,
        diameter,
        depth,
        isThrough: false,
        drillType: "CARBIDE",
      };
      const covered =
        tagged.some((tag) => sameHole(tag, candidate)) ||
        heuristic.some((existing) => sameHole(existing, candidate));
      if (!covered) heuristic.push(candidate);
    }
  }

  return {
    tagged,
    heuristic,
    hasCentralBore: detectCentralBore(code),
    family: detectOperationFamily(code),
  };
}
