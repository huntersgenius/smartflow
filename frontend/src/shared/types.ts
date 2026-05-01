export type StaffRole = "kitchen" | "admin";
export type OrderStatus = "pending" | "accepted" | "preparing" | "ready" | "served" | "cancelled";

export interface GuestSessionResponse {
  session_id: string;
  expires_in: number;
}

export interface StaffLoginResponse {
  user_id: number;
  role: StaffRole;
  branch_id: number;
}

export interface MenuItem {
  id: string;
  name: string;
  description: string | null;
  price: string;
  thumbnail_url: string | null;
  image_url: string | null;
  available: boolean;
  sort_order: number;
}

export interface MenuCategory {
  id: number;
  name: string;
  description: string | null;
  image_url: string | null;
  sort_order: number;
  items: MenuItem[];
}

export interface MenuResponse {
  branch_id: number;
  categories: MenuCategory[];
}

export interface CartItem extends MenuItem {
  quantity: number;
  cookTimeMin: number;
  calories: number;
  categoryName: string;
}

export interface OrderCreateResponse {
  order_id: string;
  status: OrderStatus;
  total: string;
}

export interface OrderDetailItem {
  menu_item_id: string;
  name: string;
  quantity: number;
  unit_price: string;
  notes: string | null;
}

export interface OrderHistoryEntry {
  status: OrderStatus;
  changed_by: string;
  changed_at: string;
  note: string | null;
}

export interface OrderDetail {
  order_id: string;
  status: OrderStatus;
  total: string;
  items: OrderDetailItem[];
  created_at: string;
  history: OrderHistoryEntry[];
}

export interface KitchenOrderItem {
  menu_item_id?: string;
  name: string;
  quantity?: number;
  qty?: number;
  unit_price?: string;
  notes?: string | null;
}

export interface KitchenOrder {
  order_id: string;
  table_code: string;
  table_id?: number;
  status: OrderStatus;
  total: string;
  items: KitchenOrderItem[];
  note?: string | null;
  created_at: string;
}

export interface KitchenOrdersResponse {
  orders: KitchenOrder[];
}

export interface OrderStatusUpdateResponse {
  order_id: string;
  old_status: OrderStatus;
  new_status: OrderStatus;
}

export interface SseEnvelope<TPayload = Record<string, unknown>> {
  event_type: string;
  event_id: string;
  timestamp: string;
  branch_id: number;
  payload: TPayload;
}

export interface AdminCategory {
  id: number;
  branch_id: number;
  name: string;
  description: string | null;
  image_url: string | null;
  sort_order: number;
  active: boolean;
  created_at: string;
}

export interface AdminMenuItem {
  id: string;
  category_id: number;
  branch_id: number;
  category_name: string | null;
  name: string;
  description: string | null;
  price: string;
  image_url: string | null;
  thumbnail_url: string | null;
  available: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface DiningTable {
  id: number;
  branch_id: number;
  table_code: string;
  label: string;
  active: boolean;
  qr_image_url: string | null;
  created_at: string;
}
