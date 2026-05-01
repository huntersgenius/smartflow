import { ArrowLeft, Wifi, WifiOff } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";

import { money } from "../shared/format";
import OrderTracker from "./components/OrderTracker";
import { useOrderStream } from "./hooks/useOrderStream";

export default function OrderStatusPage() {
  const navigate = useNavigate();
  const { tableCode, orderId } = useParams();
  const { status, connected, error, detail } = useOrderStream(orderId ?? null);
  const terminal = status === "ready" || status === "served" || status === "cancelled";

  return (
    <main className="phone-shell min-h-screen px-4 pb-8 pt-5">
      <button className="mb-4 flex items-center gap-2 text-sm font-semibold text-sf-dark" onClick={() => navigate(`/t/${tableCode}/menu`)}>
        <ArrowLeft size={18} />
        Menyu
      </button>
      <div className="rounded-lg border border-sf-line bg-white p-5 shadow-sm">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-sf-green">Buyurtma</p>
            <h1 className="mt-1 text-xl font-bold text-sf-dark">#{orderId?.slice(0, 8)}</h1>
          </div>
          <div className={`flex items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold ${connected ? "bg-sf-mint text-sf-green" : "bg-slate-100 text-slate-500"}`}>
            {connected ? <Wifi size={14} /> : <WifiOff size={14} />}
            {connected ? "Live" : terminal ? "Yakunlandi" : "Kutilmoqda"}
          </div>
        </div>
        {error ? <p className="mt-4 text-sm text-red-600">{error}</p> : null}
        {!connected && !terminal && !error ? (
          <p className="mt-4 text-sm text-slate-500">Holat yuklandi. Jonli aloqa qayta ulanishi mumkin.</p>
        ) : null}
        <div className="mt-6">
          <OrderTracker status={status} />
        </div>
      </div>

      {detail ? (
        <section className="mt-5 rounded-lg border border-sf-line bg-white p-4">
          <h2 className="font-bold text-sf-dark">Tarkibi</h2>
          <div className="mt-3 space-y-2">
            {detail.items.map((item) => (
              <div key={item.menu_item_id} className="flex justify-between text-sm">
                <span>{item.quantity} x {item.name}</span>
                <strong>{money(Number(item.unit_price) * item.quantity)}</strong>
              </div>
            ))}
          </div>
          <div className="mt-4 border-t border-sf-line pt-3">
            <div className="flex justify-between font-bold">
              <span>Jami</span>
              <span>{money(detail.total)}</span>
            </div>
          </div>
        </section>
      ) : null}
    </main>
  );
}
