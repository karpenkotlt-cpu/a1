"use client";

import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiFetch } from "@/lib/api";
import type { CalculateRequest } from "@/lib/constructor-types";
import { useAuthStore } from "@/stores/auth";

export function SaveQuote({
  request,
  materialId,
}: {
  request: CalculateRequest | null;
  materialId: number | null;
}) {
  const token = useAuthStore((s) => s.token);
  const [name, setName] = useState("");
  const [status, setStatus] = useState<"idle" | "saving" | "saved">("idle");
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    if (!token || !request || name.trim() === "") return;
    setStatus("saving");
    setError(null);
    try {
      await apiFetch("/quotes", token, {
        method: "POST",
        body: { name: name.trim(), material_id: materialId, request },
      });
      setStatus("saved");
    } catch (err) {
      setStatus("idle");
      setError(err instanceof Error ? err.message : "Ошибка сохранения");
    }
  }

  return (
    <section className="space-y-3 rounded-xl border bg-white p-4">
      <h2 className="font-semibold">Сохранить расчёт</h2>
      <div className="space-y-1">
        <Label className="text-xs text-zinc-500">Название</Label>
        <Input
          placeholder="Корпус подшипника, заказ №123"
          value={name}
          onChange={(event) => {
            setName(event.target.value);
            setStatus("idle");
          }}
        />
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
      {status === "saved" ? (
        <p className="text-sm text-green-700">
          Сохранено. <Link href="/quotes" className="underline">Все расчёты →</Link>
        </p>
      ) : (
        <Button
          type="button"
          className="w-full"
          disabled={!request || name.trim() === "" || status === "saving"}
          onClick={() => void handleSave()}
        >
          {status === "saving" ? "Сохранение…" : "Сохранить"}
        </Button>
      )}
    </section>
  );
}
