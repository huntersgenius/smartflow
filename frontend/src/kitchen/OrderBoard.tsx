import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Navigate } from "react-router-dom";

import { api, isAuthError } from "../shared/api";
import { useKitchenStore, useSessionStore } from "../shared/store";
import type { KitchenOrdersResponse, OrderStatus } from "../shared/types";
import { useKitchenStream } from "./hooks/useKitchenStream";
import { useOrderActions } from "./hooks/useOrderActions";
import KanbanCard from "./KanbanCard";

const columns: Array<{ status: OrderStatus; title: string; className: string }> = [
  { status: "pending", title: "Yangi", className: "border-amber-200 bg-amber-50" },
  { status: "accepted", title: "Qabul", className: "border-blue-200 bg-blue-50" },
  { status: "preparing", title: "Tayyorlanmoqda", className: "border-purple-200 bg-purple-50" },
  { status: "ready", title: "Tayyor", className: "border-green-200 bg-green-50" },
];

export default function OrderBoard() {
  const role = useSessionStore((state) => state.role);
  const clearSession = useSessionStore((state) => state.clearSession);
  const orders = useKitchenStore((state) => state.orders);
  const setOrders = useKitchenStore((state) => state.setOrders);
  const action = useOrderActions();
  const stream = useKitchenStream(role === "kitchen" || role === "admin");

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["kitchen-orders"],
    queryFn: () => api.get<KitchenOrdersResponse>("/kitchen/orders"),
    enabled: role === "kitchen" || role === "admin",
    refetchInterval: 30_000,
  });

  useEffect(() => {
    if (data?.orders) setOrders(data.orders);
  }, [data, setOrders]);

  useEffect(() => {
    if (isAuthError(error)) clearSession();
  }, [clearSession, error]);

  if (role !== "kitchen" && role !== "admin") return <Navigate to="/kitchen/login" replace />;

  return (
    <section className="mx-auto max-w-7xl px-4 py-6">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-sf-dark">Buyurtmalar</h1>
          <p className="text-sm text-slate-500">
            {isLoading
              ? "Yuklanmoqda..."
              : stream.connected
                ? "Jonli panel ulangan"
                : stream.reconnecting
                  ? "Jonli aloqa qayta ulanmoqda..."
                  : "Jonli aloqa kutilmoqda"}
          </p>
        </div>
        {error ? (
          <button
            className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-sf-dark disabled:opacity-60"
            onClick={() => void refetch()}
            disabled={isFetching}
          >
            Qayta yuklash
          </button>
        ) : null}
      </div>
      {error ? (
        <div className="mb-4 rounded-lg border border-red-100 bg-red-50 p-3 text-sm text-red-700">
          {error instanceof Error ? error.message : "Buyurtmalar yuklanmadi."}
        </div>
      ) : null}
      <div className="grid gap-4 lg:grid-cols-4">
        {columns.map((column) => (
          <section key={column.status} className={`min-h-96 rounded-lg border p-3 ${column.className}`}>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-bold text-sf-dark">{column.title}</h2>
              <span className="rounded-full bg-white px-2 py-1 text-xs font-bold">{orders[column.status].length}</span>
            </div>
            <div className="space-y-3">
              {orders[column.status].map((order) => (
                <KanbanCard
                  key={order.order_id}
                  order={order}
                  disabled={action.isPending}
                  onMove={(orderId, status) => action.mutate({ orderId, status })}
                />
              ))}
              {orders[column.status].length === 0 ? (
                <p className="rounded-md bg-white/70 p-3 text-center text-sm text-slate-500">Buyurtma yo'q</p>
              ) : null}
            </div>
          </section>
        ))}
      </div>
    </section>
  );
}
