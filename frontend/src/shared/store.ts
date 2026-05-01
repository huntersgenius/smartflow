import { create } from "zustand";
import { persist } from "zustand/middleware";

import { estimateCartTime, priceNumber } from "./format";
import type { CartItem, KitchenOrder, OrderStatus, StaffRole } from "./types";

interface CartState {
  items: CartItem[];
  branchId: number;
  tableCode: string | null;
  addItem: (item: CartItem) => void;
  removeItem: (itemId: string) => void;
  updateQty: (itemId: string, qty: number) => void;
  clearCart: () => void;
  setContext: (branchId: number, tableCode: string) => void;
  total: () => number;
  itemCount: () => number;
  estimatedTime: () => ReturnType<typeof estimateCartTime>;
}

interface SessionState {
  role: "guest" | StaffRole | null;
  branchId: number | null;
  tableCode: string | null;
  userId: number | null;
  setGuest: (tableCode: string, branchId: number) => void;
  setStaff: (role: StaffRole, branchId: number, userId: number) => void;
  clearSession: () => void;
}

interface KitchenState {
  orders: Record<OrderStatus, KitchenOrder[]>;
  setOrders: (orders: KitchenOrder[]) => void;
  addOrder: (order: KitchenOrder) => void;
  updateStatus: (orderId: string, status: OrderStatus) => void;
  removeOrder: (orderId: string) => void;
}

const emptyKitchenOrders: Record<OrderStatus, KitchenOrder[]> = {
  pending: [],
  accepted: [],
  preparing: [],
  ready: [],
  served: [],
  cancelled: [],
};

function groupKitchenOrders(orders: KitchenOrder[]): Record<OrderStatus, KitchenOrder[]> {
  const grouped: Record<OrderStatus, KitchenOrder[]> = {
    pending: [],
    accepted: [],
    preparing: [],
    ready: [],
    served: [],
    cancelled: [],
  };
  orders.forEach((order) => {
    if (order.status !== "served" && order.status !== "cancelled") {
      grouped[order.status].push(order);
    }
  });
  return grouped;
}

export const useCartStore = create<CartState>()(
  persist(
    (set, get) => ({
      items: [],
      branchId: 1,
      tableCode: null,
      setContext: (branchId, tableCode) =>
        set((state) => ({
          branchId,
          tableCode,
          items: state.tableCode && state.tableCode !== tableCode ? [] : state.items,
        })),
      addItem: (item) =>
        set((state) => {
          const existing = state.items.find((cartItem) => cartItem.id === item.id);
          if (existing) {
            return {
              items: state.items.map((cartItem) =>
                cartItem.id === item.id ? { ...cartItem, quantity: cartItem.quantity + 1 } : cartItem,
              ),
            };
          }
          return { items: [...state.items, { ...item, quantity: 1 }] };
        }),
      removeItem: (itemId) =>
        set((state) => ({ items: state.items.filter((item) => item.id !== itemId) })),
      updateQty: (itemId, qty) =>
        set((state) => ({
          items: qty <= 0
            ? state.items.filter((item) => item.id !== itemId)
            : state.items.map((item) => (item.id === itemId ? { ...item, quantity: qty } : item)),
        })),
      clearCart: () => set({ items: [] }),
      total: () => get().items.reduce((sum, item) => sum + priceNumber(item.price) * item.quantity, 0),
      itemCount: () => get().items.reduce((sum, item) => sum + item.quantity, 0),
      estimatedTime: () => estimateCartTime(get().items),
    }),
    { name: "smartflow-cart" },
  ),
);

export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      role: null,
      branchId: null,
      tableCode: null,
      userId: null,
      setGuest: (tableCode, branchId) => set({ role: "guest", tableCode, branchId, userId: null }),
      setStaff: (role, branchId, userId) => set({ role, branchId, userId, tableCode: null }),
      clearSession: () => set({ role: null, branchId: null, tableCode: null, userId: null }),
    }),
    { name: "smartflow-session" },
  ),
);

export const useKitchenStore = create<KitchenState>((set) => ({
  orders: emptyKitchenOrders,
  setOrders: (orders) => set({ orders: groupKitchenOrders(orders) }),
  addOrder: (order) =>
    set((state) => {
      const all = Object.values(state.orders).flat().filter((existing) => existing.order_id !== order.order_id);
      all.push({ ...order, status: order.status || "pending" });
      return { orders: groupKitchenOrders(all) };
    }),
  updateStatus: (orderId, status) =>
    set((state) => {
      const all = Object.values(state.orders).flat();
      const next = all.map((order) => (order.order_id === orderId ? { ...order, status } : order));
      return { orders: groupKitchenOrders(next) };
    }),
  removeOrder: (orderId) =>
    set((state) => {
      const grouped = { ...state.orders };
      (Object.keys(grouped) as OrderStatus[]).forEach((status) => {
        grouped[status] = grouped[status].filter((order) => order.order_id !== orderId);
      });
      return { orders: grouped };
    }),
}));
