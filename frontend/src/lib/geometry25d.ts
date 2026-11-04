import * as THREE from "three";

import type {
  ConstructorFeature,
  HoleArrayFeature,
  T1Dimensions,
  T2Dimensions,
  T3Dimensions,
  T4Dimensions,
  T5Dimensions,
  TemplateType,
} from "@/lib/constructor-types";

export interface PreviewSpec {
  templateType: TemplateType;
  t1: T1Dimensions;
  t2: T2Dimensions;
  t3: T3Dimensions;
  t4: T4Dimensions;
  t5: T5Dimensions;
  features: ConstructorFeature[];
}

export interface PreviewModel {
  part: THREE.BufferGeometry;
  cutters: THREE.BufferGeometry[];
}

function outerProfile(steps: { diameter: number; length: number }[]): {
  points: THREE.Vector2[];
  top: number;
  maxRadius: number;
} {
  const points: THREE.Vector2[] = [];
  let z = 0;
  let maxRadius = 0;
  for (const step of steps) {
    const r = step.diameter / 2;
    maxRadius = Math.max(maxRadius, r);
    points.push(new THREE.Vector2(r, z));
    z += step.length;
    points.push(new THREE.Vector2(r, z));
  }
  return { points, top: z, maxRadius };
}

function rotationProfile(
  outer: { diameter: number; length: number }[],
  inner: { diameter: number; length: number }[],
): THREE.Vector2[] {
  const outerUp = outerProfile(outer);
  const profile: THREE.Vector2[] = [];
  const outerTop = outerUp.top;

  if (inner.length > 0) {
    let zi = 0;
    const innerPts: THREE.Vector2[] = [];
    for (const step of inner) {
      const r = step.diameter / 2;
      innerPts.push(new THREE.Vector2(r, zi));
      zi += step.length;
      innerPts.push(new THREE.Vector2(r, zi));
    }
    const innerTop = zi;
    profile.push(...innerPts);
    if (Math.abs(innerTop - outerTop) < 0.01) {
      profile.push(new THREE.Vector2(outerUp.points.at(-1)!.x, outerTop));
    } else {
      profile.push(new THREE.Vector2(0, innerTop));
      profile.push(new THREE.Vector2(0, outerTop));
      profile.push(new THREE.Vector2(outerUp.points.at(-1)!.x, outerTop));
    }
  } else {
    profile.push(new THREE.Vector2(0, 0));
    profile.push(...outerUp.points);
  }
  if (inner.length === 0) {
    profile.push(new THREE.Vector2(0, outerTop));
    return profile;
  }
  for (let i = outerUp.points.length - 1; i >= 0; i -= 1) {
    const p = outerUp.points[i];
    profile.push(new THREE.Vector2(p.x, Math.min(p.y, outerTop)));
  }
  profile.push(profile[0].clone());
  return profile;
}

function boltCircle(count: number, radius: number): [number, number][] {  const positions: [number, number][] = [];
  for (let i = 0; i < count; i += 1) {
    const angle = (2 * Math.PI * i) / count;
    positions.push([radius * Math.cos(angle), radius * Math.sin(angle)]);
  }
  return positions;
}

function grid(count: number, spanX: number, spanZ: number): [number, number][] {
  const cols = Math.ceil(Math.sqrt(count));
  const rows = Math.ceil(count / cols);
  const positions: [number, number][] = [];
  for (let i = 0; i < count; i += 1) {
    const col = i % cols;
    const row = Math.floor(i / cols);
    const x = cols === 1 ? 0 : (col - (cols - 1) / 2) * (spanX / cols);
    const z = rows === 1 ? 0 : (row - (rows - 1) / 2) * (spanZ / rows);
    positions.push([x, z]);
  }
  return positions;
}

function holeCutter(
  diameter: number,
  depth: number,
  x: number,
  z: number,
  faceY: number,
  direction: 1 | -1,
): THREE.BufferGeometry {
  const height = depth + 2;
  const geometry = new THREE.CylinderGeometry(diameter / 2, diameter / 2, height, 24);
  const center = faceY + direction * (height / 2 - 1);
  geometry.translate(x, center, z);
  return geometry;
}

function pocketCutter(
  length: number,
  width: number,
  depth: number,
  x: number,
  z: number,
  faceY: number,
  direction: 1 | -1,
): THREE.BufferGeometry {
  const height = depth + 2;
  const geometry = new THREE.BoxGeometry(length, height, width);
  const center = faceY + direction * (height / 2 - 1);
  geometry.translate(x, center, z);
  return geometry;
}

function holeCutters(
  feature: HoleArrayFeature,
  positions: [number, number][],
  throughDepth: number,
  faceY: number,
  direction: 1 | -1,
): THREE.BufferGeometry[] {
  const depth = feature.is_through ? throughDepth : feature.depth;
  const cutters = positions.map(([x, z]) =>
    holeCutter(feature.diameter, depth, x, z, faceY, direction),
  );
  if (feature.counterbore_diameter && feature.counterbore_depth) {
    for (const [x, z] of positions) {
      cutters.push(
        holeCutter(
          feature.counterbore_diameter,
          feature.counterbore_depth,
          x,
          z,
          faceY,
          direction,
        ),
      );
    }
  }
  return cutters;
}

/**
 * Ориентация контура для LatheGeometry: нормали считаются как (dy, -dx),
 * поэтому наружная поверхность должна обходиться снизу вверх (CCW).
 * Замкнутые контуры T2/T3 строились по часовой (вверх по расточке →
 * вниз по наружке) — все нормали инвертировались, деталь рендерилась
 * «наизнанку», а CSG давал артефакты.
 */
function ensureCcw(points: THREE.Vector2[]): THREE.Vector2[] {
  let area = 0;
  for (let i = 0; i < points.length; i += 1) {
    const a = points[i];
    const b = points[(i + 1) % points.length];
    area += a.x * b.y - b.x * a.y;
  }
  return area < 0 ? [...points].reverse() : points;
}

export function buildPreview(spec: PreviewSpec): PreviewModel {
  const { templateType } = spec;
  const features = spec.features.filter((feature) => feature.enabled);

  if (templateType === "T4_PLATE" || templateType === "T5_HOUSING") {
    const isHousing = templateType === "T5_HOUSING";
    const dims = isHousing ? spec.t5 : spec.t4;
    const { length, width, height } = dims;
    const part = new THREE.BoxGeometry(length, height, width);
    part.translate(length / 2, height / 2, width / 2);
    const cutters: THREE.BufferGeometry[] = [];
    if (isHousing) {
      const ratio = spec.t5.removal_ratio;
      const windows = ratio < 0.35 ? 1 : ratio < 0.7 ? 2 : 3;
      const wl = length * 0.35;
      const ww = width * 0.35;
      for (let i = 0; i < windows; i += 1) {
        const x =
          length / 2 + (i - (windows - 1) / 2) * (length * 0.45);
        cutters.push(pocketCutter(wl, ww, height + 4, x, width / 2, height, -1));
      }
    }
    for (const feature of features) {
      if (feature.type === "HOLE_ARRAY") {
        const positions = grid(feature.count, length * 0.7, width * 0.7).map(
          ([x, z]) => [x + length / 2, z + width / 2] as [number, number],
        );
        cutters.push(...holeCutters(feature, positions, height, height, -1));
      } else {
        for (const [x] of grid(feature.count, length * 0.7, width * 0.7)) {
          cutters.push(
            pocketCutter(
              feature.length,
              feature.width,
              feature.depth,
              x + length / 2,
              width / 2,
              height,
              -1,
            ),
          );
        }
      }
    }
    return centerAll(part, cutters);
  }

  let profile: THREE.Vector2[];
  let totalLength: number;
  let maxOuterRadius: number;
  let firstInnerRadius = 0;

  if (templateType === "T1_STEPPED_SHAFT") {
    const outer = outerProfile(spec.t1.steps);
    profile = rotationProfile(spec.t1.steps, []);
    totalLength = outer.top;
    maxOuterRadius = outer.maxRadius;
  } else if (templateType === "T2_BUSHING") {
    profile = rotationProfile(spec.t2.outer_steps, spec.t2.inner_steps);
    const outer = outerProfile(spec.t2.outer_steps);
    totalLength = outer.top;
    maxOuterRadius = outer.maxRadius;
    firstInnerRadius = spec.t2.inner_steps.length
      ? spec.t2.inner_steps[0].diameter / 2
      : 0;
  } else {
    const { outer_diameter, thickness, center_hole_diameter } = spec.t3;
    totalLength = thickness;
    maxOuterRadius = outer_diameter / 2;
    firstInnerRadius = center_hole_diameter / 2;
    profile =
      center_hole_diameter > 0
        ? [
            new THREE.Vector2(firstInnerRadius, 0),
            new THREE.Vector2(firstInnerRadius, thickness),
            new THREE.Vector2(maxOuterRadius, thickness),
            new THREE.Vector2(maxOuterRadius, 0),
            new THREE.Vector2(firstInnerRadius, 0),
          ]
        : [
            new THREE.Vector2(0, 0),
            new THREE.Vector2(maxOuterRadius, 0),
            new THREE.Vector2(maxOuterRadius, thickness),
            new THREE.Vector2(0, thickness),
          ];
  }

  const part = new THREE.LatheGeometry(ensureCcw(profile), 64);
  const cutters: THREE.BufferGeometry[] = [];
  const boltRadius =
    firstInnerRadius > 0
      ? (maxOuterRadius + firstInnerRadius) / 2
      : maxOuterRadius * 0.65;

  for (const feature of features) {
    if (feature.type === "HOLE_ARRAY") {
      const positions = boltCircle(feature.count, boltRadius);
      // Вход отверстий/цековок — с верхнего торца (как у T4/T5),
      // иначе глухие отверстия «сверлились» с нижней плоскости.
      cutters.push(
        ...holeCutters(feature, positions, totalLength, totalLength, -1),
      );
    } else {
      const step = feature.length * 1.6;
      for (let i = 0; i < feature.count; i += 1) {
        const x = (i - (feature.count - 1) / 2) * step;
        cutters.push(
          pocketCutter(feature.length, feature.width, feature.depth, x, 0, 0, 1),
        );
      }
    }
  }

  return centerAll(part, cutters);
}

function centerAll(
  part: THREE.BufferGeometry,
  cutters: THREE.BufferGeometry[],
): PreviewModel {
  part.computeBoundingBox();
  const box = part.boundingBox ?? new THREE.Box3();
  const center = box.getCenter(new THREE.Vector3());
  part.translate(-center.x, -center.y, -center.z);
  for (const cutter of cutters) {
    cutter.translate(-center.x, -center.y, -center.z);
  }
  return { part, cutters };
}
