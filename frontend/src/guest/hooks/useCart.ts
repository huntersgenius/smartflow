import { useCartStore } from "../../shared/store";

export function useCart() {
  const items = useCartStore((state) => state.items);
  const addItem = useCartStore((state) => state.addItem);
  const removeItem = useCartStore((state) => state.removeItem);
  const updateQty = useCartStore((state) => state.updateQty);
  const clearCart = useCartStore((state) => state.clearCart);
  const total = useCartStore((state) => state.total());
  const itemCount = useCartStore((state) => state.itemCount());
  const estimatedTime = useCartStore((state) => state.estimatedTime());

  return { items, addItem, removeItem, updateQty, clearCart, total, itemCount, estimatedTime };
}
