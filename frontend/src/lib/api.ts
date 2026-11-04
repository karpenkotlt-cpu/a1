const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
}

export const UNAUTHORIZED_EVENT = "qcs:unauthorized";

/**
 * 401 от API (кроме /auth/*): протухший/невалидный JWT. Сообщаем приложению
 * событием — слушатель в StoreHydrator делает logout() и ведёт на /login.
 * Без этого просроченный токен в localStorage «застревает»: гварды проверяют
 * только наличие токена, страницы показывают "Invalid token".
 */
function notifyUnauthorized(path: string): void {
  if (typeof window === "undefined") return;
  // Логин при неверном пароле тоже даёт 401 — редирект зациклился бы.
  if (path.startsWith("/auth/")) return;
  window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
}

export async function apiDownload(
  path: string,
  token: string,
  filename: string,
): Promise<void> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    if (response.status === 401) notifyUnauthorized(path);
    throw new ApiError(response.status, `HTTP ${response.status}`);
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export async function apiFetch<T>(
  path: string,
  token: string | null,
  options: RequestOptions = {},
): Promise<T> {
  const headers: Record<string, string> = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });
  if (!response.ok) {
    if (response.status === 401) notifyUnauthorized(path);
    const payload: unknown = await response.json().catch(() => null);
    const detail =
      payload &&
      typeof payload === "object" &&
      "detail" in payload &&
      typeof payload.detail === "string"
        ? payload.detail
        : `HTTP ${response.status}`;
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
