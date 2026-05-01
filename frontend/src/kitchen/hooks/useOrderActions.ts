import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "../../shared/api";
import { useKitchenStore } from "../../shared/store";
import type { OrderStatus, OrderStatusUpdateResponse } from "../../shared/types";

export function useOrderActions() {
  const queryClient = useQueryClient();
  const updateStatus = useKitchenStore((state) => state.updateStatus);

  return useMutation({
    mutationFn: ({ orderId, status }: { orderId: string; status: OrderStatus }) =>
      api.patch<OrderStatusUpdateResponse>(`/kitchen/orders/${orderId}/status`, { status }),
    onSuccess: (data) => {
      updateStatus(data.order_id, data.new_status);
      queryClient.invalidateQueries({ queryKey: ["kitchen-orders"] });
    },
  });
}
