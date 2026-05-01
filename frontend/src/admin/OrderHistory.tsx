import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api, isAuthError } from "../shared/api";
import { money } from "../shared/format";
import { useSessionStore } from "../shared/store";
import type { KitchenOrder } from "../shared/types";

export default function OrderHistory() {
  const clearSession = useSessionStore((state) => state.clearSession);
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const orders = useQuery({
    queryKey: ["admin-orders", date],
    queryFn: () => api.get<{ orders: KitchenOrder[] }>(`/admin/orders?date=${date}`),
  });

  useEffect(() => {
    if (isAuthError(orders.error)) clearSession();
  }, [clearSession, orders.error]);

  function exportCsv() {
    const rows = [["order_id", "table", "status", "total", "created_at"], ...(orders.data?.orders ?? []).map((order) => [
      order.order_id,
      order.table_code,
      order.status,
      order.total,
      order.created_at,
    ])];
    const blob = new Blob([rows.map((row) => row.map(csvCell).join(",")).join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `orders-${date}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="mx-auto max-w-7xl px-4 py-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-sf-dark">Order History</h1>
          <p className="text-sm text-slate-500">Branch order archive</p>
        </div>
        <div className="flex gap-2">
          <input className="h-10 rounded-md border border-slate-200 px-3" type="date" value={date} onChange={(event) => setDate(event.target.value)} />
          <button className="rounded-md bg-sf-green px-4 text-sm font-bold text-white disabled:bg-slate-300" onClick={exportCsv} disabled={!orders.data?.orders.length}>CSV</button>
        </div>
      </div>
      {orders.error ? (
        <div className="mt-4 rounded-lg border border-red-100 bg-red-50 p-3 text-sm text-red-700">
          {orders.error instanceof Error ? orders.error.message : "Orders did not load."}
        </div>
      ) : null}
      <div className="mt-5 overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="min-w-[720px] w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500">
            <tr>
              <th className="p-3">Order</th>
              <th className="p-3">Table</th>
              <th className="p-3">Status</th>
              <th className="p-3">Total</th>
              <th className="p-3">Created</th>
            </tr>
          </thead>
          <tbody>
            {orders.isLoading ? (
              <tr>
                <td className="p-4 text-center text-slate-500" colSpan={5}>Loading orders...</td>
              </tr>
            ) : null}
            {!orders.isLoading && orders.data?.orders.length === 0 ? (
              <tr>
                <td className="p-4 text-center text-slate-500" colSpan={5}>No orders for this date.</td>
              </tr>
            ) : null}
            {orders.data?.orders.map((order) => (
              <tr key={order.order_id} className="border-t border-slate-100">
                <td className="p-3 font-semibold">#{order.order_id.slice(0, 8)}</td>
                <td className="p-3">{order.table_code}</td>
                <td className="p-3">{order.status}</td>
                <td className="p-3">{money(order.total)}</td>
                <td className="p-3">{new Date(order.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function csvCell(value: string): string {
  return `"${value.replace(/"/g, '""')}"`;
}
