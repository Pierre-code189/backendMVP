import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models.order import OrderItemType, OrderStatus


class OrderCreate(BaseModel):
    """Schema for requesting a service or purchasing a product."""
    item_type: OrderItemType = Field(..., description="Tipo de elemento: 'service' o 'product'")
    item_id: uuid.UUID = Field(..., description="ID del servicio o producto solicitado")
    quantity: int = Field(default=1, gt=0, description="Cantidad (unidades en productos o factor en servicios)")
    notes: Optional[str] = Field(default=None, description="Instrucciones, detalles o preferencia horaria")


class OrderStatusUpdate(BaseModel):
    """Schema for updating the status of an order."""
    status: OrderStatus = Field(..., description="Nuevo estado del pedido")


class OrderOut(BaseModel):
    """Public representation of an order."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    buyer_id: uuid.UUID
    seller_id: uuid.UUID
    item_type: OrderItemType
    service_id: Optional[uuid.UUID] = None
    product_id: Optional[uuid.UUID] = None
    quantity: int
    unit_price: float
    total_price: float
    status: OrderStatus
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
