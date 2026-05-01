import { useCallback } from "react";

const KEY = "smartflow-recent-order";

export function useRecentOrder() {
  const saveRecentOrder = useCallback((orderId: string, tableCode: string) => {
    localStorage.setItem(KEY, JSON.stringify({ orderId, tableCode, savedAt: Date.now() }));
  }, []);

  const getRecentOrder = useCallback((): { orderId: string; tableCode: string } | null => {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }, []);

  return { saveRecentOrder, getRecentOrder };
}
