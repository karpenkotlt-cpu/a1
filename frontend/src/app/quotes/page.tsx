"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ApiError, apiDownload, apiFetch } from "@/lib/api";
import type { Quote, QuoteDetail } from "@/lib/types";
import { useAuthStore } from "@/stores/auth";
import { useConstructorStore } from "@/stores/constructor";

export default function QuotesPage() {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  const hydrated = useAuthStore((s) => s.hydrated);
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const hydrateFromRequest = useConstructorStore(
    (s) => s.hydrateFromRequest,
  );
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [openingId, setOpeningId] = useState<number | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    try {
      setQuotes(await apiFetch<Quote[]>("/quotes", token));
      setError(null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        logout();
        router.replace("/login?next=/quotes");
        return;
      }
      setError(err instanceof Error ? err.message : "Ошибка загрузки");
    }
  }, [token, logout, router]);

  useEffect(() => {
    if (!hydrated) return;
    if (!token) {
      router.replace("/login?next=/quotes");
      return;
    }
    void load();
  }, [hydrated, token, router, load]);

  async function handleOpen(id: number) {
    if (!token) return;
    setOpeningId(id);
    try {
      const detail = await apiFetch<QuoteDetail>(`/quotes/${id}`, token);
      hydrateFromRequest(detail.request, detail.material_id);
      router.push("/constructor");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка открытия");
    } finally {
      setOpeningId(null);
    }
  }

  async function handleExport(id: number) {
    if (!token) return;
    try {
      await apiDownload(`/quotes/${id}/export.xlsx`, token, `quote_${id}.xlsx`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка экспорта");
    }
  }

  async function handleDelete(id: number) {
    if (!token) return;
    try {
      await apiFetch<void>(`/quotes/${id}`, token, { method: "DELETE" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка удаления");
    }
  }

const canDelete = (quote: Quote) =>
  user?.role === "ADMIN" || quote.author_email === user?.email;

function formatDate(iso: string): string {
  const date = new Date(iso);
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${pad(date.getDate())}.${pad(date.getMonth() + 1)}.${date.getFullYear()} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

  return (
    <div className="min-h-screen bg-zinc-50">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <h1 className="text-lg font-semibold">Сохранённые расчёты</h1>
          <div className="flex items-center gap-3 text-sm text-zinc-600">
            <a href="/constructor" className="rounded-md border px-3 py-1.5 hover:bg-zinc-100">
              ← Конструктор
            </a>
            <span>
              {user?.email} · {user?.role}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                logout();
                router.replace("/login");
              }}
            >
              Выйти
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl space-y-4 px-6 py-8">
        {error && (
          <p className="rounded-md border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
            {error}
          </p>
        )}
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Дата</TableHead>
              <TableHead>Название</TableHead>
              <TableHead className="text-right">Партия</TableHead>
              <TableHead className="text-right">Цена/дет, ₽</TableHead>
              <TableHead className="text-right">Итого, ₽</TableHead>
              <TableHead>Автор</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {quotes.map((quote) => (
              <TableRow key={quote.id}>
                <TableCell>{formatDate(quote.created_at)}</TableCell>
                <TableCell className="font-medium">{quote.name}</TableCell>
                <TableCell className="text-right">{quote.batch_size}</TableCell>
                <TableCell className="text-right">{quote.price_per_part}</TableCell>
                <TableCell className="text-right">
                  {quote.batch_total_price}
                </TableCell>
                <TableCell>{quote.author_email}</TableCell>
                <TableCell className="space-x-2 text-right whitespace-nowrap">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={openingId === quote.id}
                    onClick={() => void handleOpen(quote.id)}
                  >
                    {openingId === quote.id ? "Открытие…" : "Открыть"}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => void handleExport(quote.id)}
                  >
                    Excel
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      window.open(`/quotes/${quote.id}/print`, "_blank")
                    }
                  >
                    PDF
                  </Button>
                  {canDelete(quote) && (
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => void handleDelete(quote.id)}
                    >
                      Удалить
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
            {quotes.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-zinc-500">
                  Нет сохранённых расчётов — создайте их в конструкторе
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </main>
    </div>
  );
}
