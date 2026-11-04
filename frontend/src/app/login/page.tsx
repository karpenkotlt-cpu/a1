"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiFetch } from "@/lib/api";
import type { User } from "@/lib/types";
import { useAuthStore } from "@/stores/auth";

interface LoginResponse {
  access_token: string;
  token_type: string;
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const setAuth = useAuthStore((state) => state.setAuth);
  const token = useAuthStore((state) => state.token);
  const hydrated = useAuthStore((state) => state.hydrated);
  const [email, setEmail] = useState("admin@qcs.dev");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function resolveRedirect(): string {
    const next = searchParams.get("next");
    if (next && next.startsWith("/") && !next.startsWith("//")) {
      return next;
    }
    return "/constructor";
  }

  // Уже вошедший (сессия в localStorage) не должен видеть форму входа:
  // отправляем на целевую страницу после гидратации стора.
  useEffect(() => {
    if (hydrated && token) {
      router.replace(resolveRedirect());
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hydrated, token]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const token = await apiFetch<LoginResponse>("/auth/login", null, {
        method: "POST",
        body: { email, password },
      });
      const user = await apiFetch<User>("/auth/me", token.access_token);
      setAuth(token.access_token, user);
      router.push(resolveRedirect());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка входа");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm space-y-4 rounded-xl border bg-white p-8 shadow-sm"
      >
        <div>
          <h1 className="text-xl font-semibold">Smart Quote &amp; CAM-Costing</h1>
          <p className="text-sm text-zinc-500">Вход в систему расчёта ТКП</p>
        </div>
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="password">Пароль</Label>
          <Input
            id="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            minLength={8}
          />
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? "Вход..." : "Войти"}
        </Button>
      </form>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
