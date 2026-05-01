import { useEffect, useState } from "react";
import { api } from "../../shared/api";
import { useCartStore, useSessionStore } from "../../shared/store";
import type { GuestSessionResponse } from "../../shared/types";

export function useGuestSession(tableCode: string | undefined) {
  const setGuest = useSessionStore((state) => state.setGuest);
  const setCartContext = useCartStore((state) => state.setContext);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!tableCode) {
      setLoading(false);
      setError("Stol kodi topilmadi");
      return;
    }
    let cancelled = false;
    const currentTableCode = tableCode;

    async function start() {
      setLoading(true);
      setError(null);
      try {
        await api.post<GuestSessionResponse>("/sessions/guest", { table_code: currentTableCode });
        if (cancelled) return;
        setGuest(currentTableCode, 1);
        setCartContext(1, currentTableCode);
      } catch (err) {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : "Sessiya ochilmadi";
        setError(message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    start();
    return () => {
      cancelled = true;
    };
  }, [setCartContext, setGuest, tableCode]);

  return { loading, error };
}
