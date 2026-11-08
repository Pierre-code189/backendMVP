import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import String, Integer, Float, Enum as SAEnum, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.infrastructure.database.base import Base


class OrderItemType(str, Enum):
    SERVICE = "service"
    PRODUCT = "product"


class OrderStatus(str, Enum):
    PENDING = "pendiente"
    ACCEPTED = "aceptado"
    REJECTED = "rechazado"
    IN_PROGRESS = "en_progreso"
    COMPLETED = "completado"
    CANCELLED = "cancelado"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    buyer_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    item_type: Mapped[OrderItemType] = mapped_column(
        SAEnum(OrderItemType, name="order_item_type_enum"), nullable=False
    )
    service_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("services.id", ondelete="SET NULL"), nullable=True
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    total_price: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus, name="order_status_enum"), default=OrderStatus.PENDING, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    # Relationships
    buyer: Mapped["User"] = relationship("User", foreign_keys=[buyer_id], back_populates="orders_bought")
    seller: Mapped["User"] = relationship("User", foreign_keys=[seller_id], back_populates="orders_sold")
    service: Mapped["Service"] = relationship("Service", foreign_keys=[service_id])
    product: Mapped["Product"] = relationship("Product", foreign_keys=[product_id])
