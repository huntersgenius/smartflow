import { useEffect, useMemo, useState } from "react";

import { useKitchenStore } from "../../shared/store";
import type { KitchenOrder, OrderStatus, SseEnvelope } from "../../shared/types";
import { useAudioAlert } from "./useAudioAlert";

export function useKitchenStream(enabled: boolean) {
  const addOrder = useKitchenStore((state) => state.addOrder);
  const updateStatus = useKitchenStore((state) => state.updateStatus);
  const alert = useAudioAlert();
  const [connected, setConnected] = useState(false);
  const [reconnecting, setReconnecting] = useState(false);

  const backoff = useMemo(() => [1000, 2000, 4000, 8000, 15000], []);

  useEffect(() => {
    if (!enabled) return;
    let es: EventSource | null = null;
    let retryCount = 0;
    let closed = false;
    let timer: number | undefined;

    function connect() {
      if (closed) return;
      es = new EventSource("/api/v1/kitchen/stream");

      es.addEventListener("connected", () => {
        retryCount = 0;
        setConnected(true);
        setReconnecting(false);
      });

      es.addEventListener("new_order", (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data) as SseEnvelope<KitchenOrder>;
          addOrder({ ...data.payload, status: "pending" });
          alert.newOrder();
          retryCount = 0;
        } catch {
          setConnected(false);
        }
      });

      const handleStatus = (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data) as SseEnvelope<{ order_id: string; new_status: OrderStatus }>;
          updateStatus(data.payload.order_id, data.payload.new_status);
        } catch {
          setConnected(false);
        }
      };

      es.addEventListener("order_status_changed", handleStatus);
      es.addEventListener("order_ready", handleStatus);
      es.addEventListener("order_cancelled", handleStatus);
      es.onerror = () => {
        if (closed) return;
        setConnected(false);
        setReconnecting(true);
        es?.close();
        const delay = backoff[Math.min(retryCount++, backoff.length - 1)];
        timer = window.setTimeout(connect, delay);
      };
    }

    connect();
    return () => {
      closed = true;
      if (timer) window.clearTimeout(timer);
      es?.close();
    };
  }, [addOrder, alert, backoff, enabled, updateStatus]);

  return { connected, reconnecting };
}
