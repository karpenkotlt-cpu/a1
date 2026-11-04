"use client";

import { useEffect } from "react";

import { UNAUTHORIZED_EVENT } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";
import { useConstructorStore } from "@/stores/constructor";

export function StoreHydrator() {
  useEffect(() => {
    // rehydrate() завершается микрозадачей ПОСЛЕ синхронного флеша эффектов
    // страниц — гварды обязаны ждать флаг hydrated, иначе видят token=null
    // и выкидывают на /login при каждом обновлении страницы.
    Promise.resolve(useAuthStore.persist.rehydrate()).then(() => {
      useAuthStore.getState().setHydrated();
    });
    void useConstructorStore.persist.rehydrate();
  }, []);
  useEffect(() => {
    // Истёкший/невалидный JWT: любой apiFetch с 401 → logout + /login.
    // Полная перезагрузка через location.assign чистит состояние памяти;
    // logout() обнуляет persist в localStorage → login не редиректит обратно.
    const onUnauthorized = () => {
      useAuthStore.getState().logout();
      window.location.assign("/login");
    };
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, []);
  return null;
}
