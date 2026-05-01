import { Clock } from "lucide-react";

import { money } from "../shared/format";
import type { KitchenOrder, OrderStatus } from "../shared/types";

const nextStatus: Partial<Record<OrderStatus, OrderStatus>> = {
  pending: "accepted",
  accepted: "preparing",
  preparing: "ready",
  ready: "served",
};

export default function KanbanCard({
  order,
  disabled = false,
  onMove,
}: {
  order: KitchenOrder;
  disabled?: boolean;
  onMove: (orderId: string, status: OrderStatus) => void;
}) {
  const next = nextStatus[order.status];
  const minutes = Math.max(0, Math.floor((Date.now() - new Date(order.created_at).getTime()) / 60000));

  return (
    <article className="print-ticket rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-500">{order.table_code}</p>
          <h3 className="text-lg font-bold text-sf-dark">#{order.order_id.slice(0, 8)}</h3>
        </div>
        <span className="flex items-center gap-1 rounded-full bg-sf-mint px-2 py-1 text-xs font-semibold text-sf-green">
          <Clock size={13} />
          {minutes}m
        </span>
      </div>
      <div className="mt-3 space-y-2">
        {order.items.map((item, index) => (
          <div key={`${order.order_id}-${item.name}-${index}`} className="text-sm">
            <span className="font-semibold">{item.quantity ?? item.qty ?? 1}x</span> {item.name}
            {item.notes ? <p className="text-xs text-slate-500">{item.notes}</p> : null}
          </div>
        ))}
      </div>
      <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3">
        <strong>{money(order.total)}</strong>
        {next ? (
          <button
            className="rounded-md bg-sf-green px-3 py-2 text-sm font-bold text-white disabled:bg-slate-300"
            onClick={() => onMove(order.order_id, next)}
            disabled={disabled}
          >
            Keyingi
          </button>
        ) : null}
      </div>
    </article>
  );
}
