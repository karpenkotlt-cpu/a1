/**
 * Разбор и правка переменных кастомайзера OpenSCAD.
 *
 * Формат строки: `name = value; // [min:step:max] Русский лейбл`
 * (диапазон опционален). Регэксп исправлен относительно исходного
 * материала: корректный символьный класс скобки и поддержка
 * отрицательных/дробных значений.
 */

export interface CustomizerParam {
  name: string;
  value: number;
  label: string;
  min: number | null;
  max: number | null;
  step: number | null;
}

const PARAM_LINE =
  /^[ \t]*([A-Za-z_][A-Za-z0-9_]*)[ \t]*=[ \t]*(-?\d+(?:\.\d+)?)[ \t]*;[ \t]*\/\/[ \t]*(?:\[([^\]]*)\][ \t]*)?(.*)$/;

export function extractCustomizerParams(code: string): CustomizerParam[] {
  const params: CustomizerParam[] = [];
  const seen = new Set<string>();
  for (const line of code.split(/\r?\n/)) {
    const match = PARAM_LINE.exec(line);
    if (!match) continue;
    const [, name, rawValue, rawRange, rawLabel] = match;
    if (seen.has(name)) continue;
    seen.add(name);
    let min: number | null = null;
    let max: number | null = null;
    let step: number | null = null;
    if (rawRange) {
      const parts = rawRange.split(":").map((p) => Number.parseFloat(p.trim()));
      if (parts.length === 2 && parts.every((p) => Number.isFinite(p))) {
        [min, max] = parts;
      } else if (parts.length === 3 && parts.every((p) => Number.isFinite(p))) {
        [min, step, max] = parts;
      }
    }
    params.push({
      name,
      value: Number.parseFloat(rawValue),
      label: (rawLabel ?? "").trim() || name,
      min,
      max,
      step,
    });
  }
  return params;
}

/** Заменяет присваивание переменной, сохраняя кастомайзер-комментарий. */
export function updateScadVariable(
  code: string,
  name: string,
  value: number,
): string {
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const pattern = new RegExp(
    `^([ \\t]*${escaped}[ \\t]*=[ \\t]*)(-?\\d+(?:\\.\\d+)?)([ \\t]*;.*)$`,
    "m",
  );
  const formatted = Number.isInteger(value) ? String(value) : value.toFixed(2);
  return code.replace(pattern, `$1${formatted}$3`);
}
