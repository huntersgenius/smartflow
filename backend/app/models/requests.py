from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GuestSessionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    table_code: str = Field(min_length=1, max_length=50)


class StaffLoginRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=255)


class OrderItemRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    menu_item_id: UUID
    quantity: int = Field(gt=0, le=32767)
    notes: str | None = None


class OrderCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    items: list[OrderItemRequest]
    note: str | None = None


class OrderStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    status: Literal["accepted", "preparing", "ready", "served", "cancelled"]
    note: str | None = None
