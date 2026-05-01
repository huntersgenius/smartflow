import { useEffect, useRef, useState } from "react";
import confetti from "canvas-confetti";

import { api } from "../../shared/api";
import type { OrderDetail, OrderStatus, SseEnvelope } from "../../shared/types";

export function useOrderStream(orderId: string | null) {
  const [status, setStatus] = useState<OrderStatus | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<OrderDetail | null>(null);
  const esRef = useRef<EventSource | null>(null);
  const lastEventId = useRef<string>("0");
  const readyBurst = useRef(false);

  useEffect(() => {
    if (!orderId) return;
    let closed = false;

    function closeStream(updateState = true) {
      esRef.current?.close();
      esRef.current = null;
      if (updateState) setConnected(false);
    }

    function handleStatus(e: MessageEvent) {
      try {
        const data = JSON.parse(e.data) as SseEnvelope<{ new_status: OrderStatus }>;
        lastEventId.current = e.lastEventId;
        setStatus(data.payload.new_status);
        if (["ready", "served", "cancelled"].includes(data.payload.new_status)) {
          closeStream();
        }
      } catch {
        setConnected(false);
      }
    }

    function connect() {
      if (closed) return;
      const es = new EventSource(`/api/v1/guest/orders/${orderId}/stream`);
      esRef.current = es;

      es.addEventListener("connected", () => {
        setConnected(true);
        setError(null);
      });
      es.addEventListener("order_status_changed", handleStatus);
      es.addEventListener("order_ready", (e: MessageEvent) => {
        handleStatus(e);
        if (!readyBurst.current) {
          readyBurst.current = true;
          confetti({ particleCount: 80, spread: 60, origin: { y: 0.75 } });
        }
      });
      es.addEventListener("order_cancelled", (e: MessageEvent) => {
        handleStatus(e);
      });
      es.onerror = () => setConnected(false);
    }

    api
      .get<OrderDetail>(`/orders/${orderId}`)
      .then((data) => {
        if (closed) return;
        setDetail(data);
        setStatus(data.status);
        connect();
      })
      .catch((err) => {
        if (closed) return;
        const message = err instanceof Error ? err.message : "Buyurtma yuklanmadi";
        setError(message);
        setConnected(false);
      });

    return () => {
      closed = true;
      closeStream(false);
    };
  }, [orderId]);

  return { status, connected, error, detail, lastEventId: lastEventId.current };
}
