from typing import Literal

from pydantic import BaseModel


class GuestSessionResponse(BaseModel):
    session_id: str
    expires_in: int


class StaffLoginResponse(BaseModel):
    user_id: int
    role: Literal["kitchen", "admin"]
    branch_id: int


class MessageResponse(BaseModel):
    message: str


class MenuItemResponse(BaseModel):
    id: str
    name: str
    description: str | None
    price: str
    thumbnail_url: str | None
    image_url: str | None
    available: bool
    sort_order: int


class MenuCategoryResponse(BaseModel):
    id: int
    name: str
    description: str | None
    image_url: str | None
    sort_order: int
    items: list[MenuItemResponse]


class MenuResponse(BaseModel):
    branch_id: int
    categories: list[MenuCategoryResponse]


class OrderCreateResponse(BaseModel):
    order_id: str
    status: str
    total: str


class OrderDetailItemResponse(BaseModel):
    menu_item_id: str
    name: str
    quantity: int
    unit_price: str
    notes: str | None


class OrderHistoryResponse(BaseModel):
    status: str
    changed_by: str
    changed_at: str
    note: str | None


class OrderDetailResponse(BaseModel):
    order_id: str
    status: str
    total: str
    items: list[OrderDetailItemResponse]
    created_at: str
    history: list[OrderHistoryResponse]


class KitchenOrderItemResponse(BaseModel):
    menu_item_id: str
    name: str
    quantity: int
    unit_price: str
    notes: str | None


class KitchenOrderResponse(BaseModel):
    order_id: str
    table_code: str
    status: str
    total: str
    items: list[KitchenOrderItemResponse]
    created_at: str


class KitchenOrdersResponse(BaseModel):
    orders: list[KitchenOrderResponse]


class OrderStatusUpdateResponse(BaseModel):
    order_id: str
    old_status: str
    new_status: str
