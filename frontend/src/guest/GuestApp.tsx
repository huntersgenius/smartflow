import { useEffect, useState } from "react";
import { Navigate, Route, Routes, useParams } from "react-router-dom";

import { api } from "../shared/api";
import { useCartStore, useSessionStore } from "../shared/store";
import type { GuestSessionResponse, MenuResponse } from "../shared/types";
import CartPage from "./CartPage";
import MenuPage from "./MenuPage";
import OrderStatusPage from "./OrderStatusPage";

function GuestBootstrap({ tableCode }: { tableCode: string }) {
  const setGuest = useSessionStore((state) => state.setGuest);
  const setCartContext = useCartStore((state) => state.setContext);
  const [sessionReady, setSessionReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function boot() {
      setSessionReady(false);
      setError(null);

      try {
        await api.post<GuestSessionResponse>("/sessions/guest", { table_code: tableCode });
        const menu = await api.get<MenuResponse>("/menu?branch_id=1");
        if (cancelled) return;

        setGuest(tableCode, menu.branch_id);
        setCartContext(menu.branch_id, tableCode);
        setSessionReady(true);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Table not found. Please scan the QR code again.");
      }
    }

    void boot();
    return () => {
      cancelled = true;
    };
  }, [setCartContext, setGuest, tableCode]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-ember-900 p-6 font-outfit">
        <div className="animate-scale-in text-center">
          <div className="mb-6 text-6xl">:(</div>
          <h2 className="mb-3 font-fraunces text-2xl font-light text-ember-100">Table not found</h2>
          <p className="max-w-xs text-sm text-ember-400">{error}</p>
          <p className="mt-4 text-xs text-ember-500">Please scan the QR code on your table</p>
        </div>
      </div>
    );
  }

  if (!sessionReady) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-ember-900 font-outfit">
        <div className="animate-fade-in text-center">
          <div className="relative mb-8">
            <div className="animate-float text-5xl">🍽️</div>
          </div>
          <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-4 border-ember-500/25 border-t-ember-500" />
          <p className="text-sm text-ember-400">Preparing your experience...</p>
        </div>
      </div>
    );
  }

  return (
    <Routes>
      <Route path="menu" element={<MenuPage />} />
      <Route path="cart" element={<CartPage />} />
      <Route path="order/:orderId" element={<OrderStatusPage />} />
      <Route index element={<Navigate to="menu" replace />} />
      <Route path="*" element={<Navigate to="menu" replace />} />
    </Routes>
  );
}

export default function GuestApp() {
  const { tableCode } = useParams<{ tableCode: string }>();
  if (!tableCode) return <Navigate to="/" replace />;
  return <GuestBootstrap tableCode={tableCode} />;
}
