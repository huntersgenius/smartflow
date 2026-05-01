import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, Minus, Plus, Trash2 } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { useNavigate, useParams } from "react-router-dom";

import { api } from "../shared/api";
import { money } from "../shared/format";
import type { OrderCreateResponse } from "../shared/types";
import { useCart } from "./hooks/useCart";
import { useRecentOrder } from "./hooks/useRecentOrder";

export default function CartPage() {
  const navigate = useNavigate();
  const { tableCode } = useParams();
  const { items, updateQty, removeItem, clearCart, total, itemCount, estimatedTime } = useCart();
  const { saveRecentOrder } = useRecentOrder();
  const [note, setNote] = useState("");
  const idempotencyRef = useRef<string | null>(null);
  const submittingRef = useRef(false);
  const cartSignature = useMemo(
    () => JSON.stringify(items.map((item) => [item.id, item.quantity, item.price])),
    [items],
  );

  const createOrder = useMutation({
    mutationFn: async (idempotencyKey: string) => {
      return api.post<OrderCreateResponse>(
        "/orders",
        {
          items: items.map((item) => ({
            menu_item_id: item.id,
            quantity: item.quantity,
            notes: null,
          })),
          note: note || null,
        },
        { "Idempotency-Key": idempotencyKey },
      );
    },
    onSuccess: (data) => {
      toast.success("Buyurtma yuborildi");
      if (tableCode) saveRecentOrder(data.order_id, tableCode);
      idempotencyRef.current = null;
      clearCart();
      navigate(`/t/${tableCode}/order/${data.order_id}`);
    },
    onSettled: () => {
      submittingRef.current = false;
    },
  });

  useEffect(() => {
    if (!createOrder.isPending) {
      idempotencyRef.current = null;
      submittingRef.current = false;
    }
  }, [cartSignature, note]);

  function submitOrder() {
    if (submittingRef.current || createOrder.isPending || items.length === 0) return;
    submittingRef.current = true;
    idempotencyRef.current ||= createIdempotencyKey();
    createOrder.mutate(idempotencyRef.current);
  }

  return (
    <main className="phone-shell min-h-screen bg-white px-4 pb-8 pt-5">
      <button className="mb-4 flex items-center gap-2 text-sm font-semibold text-sf-dark" onClick={() => navigate(`/t/${tableCode}/menu`)}>
        <ArrowLeft size={18} />
        Menyuga qaytish
      </button>
      <h1 className="text-2xl font-bold text-sf-dark">Savat</h1>
      <p className="mt-1 text-sm text-slate-500">Buyurtmani tekshiring va yuboring.</p>

      {items.length === 0 ? (
        <div className="mt-10 rounded-lg border border-sf-line bg-sf-mint p-5 text-center">
          <p className="font-semibold text-sf-dark">Savat bo'sh</p>
          <button className="mt-4 rounded-lg bg-sf-green px-5 py-3 font-bold text-white" onClick={() => navigate(`/t/${tableCode}/menu`)}>
            Menyuga o'tish
          </button>
        </div>
      ) : (
        <>
          <div className="mt-5 space-y-3">
            {items.map((item) => (
              <div key={item.id} className="rounded-lg border border-sf-line p-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="font-semibold text-sf-dark">{item.name}</h2>
                    <p className="text-sm text-slate-500">{item.cookTimeMin} daq · {item.calories} kcal</p>
                    <p className="mt-1 font-bold text-sf-green">{money(Number(item.price) * item.quantity)}</p>
                  </div>
                  <button className="text-slate-400" onClick={() => removeItem(item.id)}>
                    <Trash2 size={18} />
                  </button>
                </div>
                <div className="mt-3 flex w-32 items-center justify-between rounded-lg bg-sf-mint p-1">
                  <button className="grid h-8 w-8 place-items-center rounded-md bg-white disabled:opacity-50" onClick={() => updateQty(item.id, item.quantity - 1)} disabled={createOrder.isPending}>
                    <Minus size={15} />
                  </button>
                  <span className="font-bold">{item.quantity}</span>
                  <button className="grid h-8 w-8 place-items-center rounded-md bg-sf-green text-white disabled:bg-slate-300" onClick={() => updateQty(item.id, item.quantity + 1)} disabled={createOrder.isPending}>
                    <Plus size={15} />
                  </button>
                </div>
              </div>
            ))}
          </div>

          <label className="mt-5 block">
            <span className="text-sm font-semibold text-sf-dark">Izoh</span>
            <textarea
              value={note}
              onChange={(event) => setNote(event.target.value)}
              className="mt-2 min-h-24 w-full rounded-lg border border-sf-line p-3 outline-none focus:border-sf-green"
              placeholder="Masalan: sous alohida bo'lsin"
            />
          </label>

          <div className="mt-5 rounded-lg border border-sf-line bg-sf-mint p-4">
            <div className="flex justify-between text-sm">
              <span>{itemCount} ta mahsulot</span>
              <strong>{money(total)}</strong>
            </div>
            <p className="mt-2 font-semibold text-sf-dark">{estimatedTime.label}</p>
            <p className="text-xs text-slate-500">Navbatga qarab o'zgaradi</p>
          </div>

          <button
            className="mt-5 w-full rounded-lg bg-sf-green py-4 font-bold text-white disabled:bg-slate-300"
            onClick={submitOrder}
            disabled={createOrder.isPending || items.length === 0}
            aria-busy={createOrder.isPending}
          >
            {createOrder.isPending ? "Yuborilmoqda..." : "Buyurtma berish"}
          </button>
        </>
      )}
    </main>
  );
}

function createIdempotencyKey(): string {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID();
  }

  const bytes = new Uint8Array(16);
  if (globalThis.crypto?.getRandomValues) {
    globalThis.crypto.getRandomValues(bytes);
  } else {
    bytes.forEach((_, index) => {
      bytes[index] = Math.floor(Math.random() * 256);
    });
  }
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = [...bytes].map((byte) => byte.toString(16).padStart(2, "0"));
  return `${hex.slice(0, 4).join("")}-${hex.slice(4, 6).join("")}-${hex.slice(6, 8).join("")}-${hex.slice(8, 10).join("")}-${hex.slice(10).join("")}`;
}
