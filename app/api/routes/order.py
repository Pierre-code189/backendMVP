import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.infrastructure.database.connection import get_db
from app.api.schemas.order import OrderCreate, OrderOut, OrderStatusUpdate
from app.api.schemas.hateoas import Link, with_links
from app.domain.models.order import OrderItemType, OrderStatus
from app.services import order_service
from app.usecases.auth import get_current_active_user
from app.domain.models.user import User

router = APIRouter(prefix="/orders", tags=["Pedidos y Solicitudes"])


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_order(
    data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Solicita un servicio o realiza un pedido de un producto ofrecido por otro vecino.
    """
    order = order_service.create_order(db, data, current_user)
    item_url = f"/api/services/{order.service_id}" if order.service_id else f"/api/products/{order.product_id}"
    return with_links(
        OrderOut.model_validate(order),
        {
            "self": Link(href=f"/api/orders/{order.id}"),
            "buyer": Link(href=f"/api/users/{order.buyer_id}"),
            "seller": Link(href=f"/api/users/{order.seller_id}"),
            "item": Link(href=item_url),
            "status_update": Link(href=f"/api/orders/{order.id}/status", method="PATCH"),
            "my_orders": Link(href="/api/orders/my-orders"),
        },
    )


@router.get("/my-orders")
def get_my_orders(
    role: Optional[str] = Query(None, description="Filtrar por rol: 'client' (lo que pedí) o 'provider' (lo que realicé/vendí)"),
    order_status: Optional[OrderStatus] = Query(None, alias="status"),
    item_type: Optional[OrderItemType] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Historial de servicios y productos del usuario.
    Permite ver tanto los pedidos solicitados como cliente, como los trabajos y ventas realizados como proveedor.
    """
    orders, total = order_service.get_my_orders(db, current_user, role, order_status, item_type, page, page_size)
    items = []
    for o in orders:
        items.append(
            with_links(
                OrderOut.model_validate(o),
                {
                    "self": Link(href=f"/api/orders/{o.id}"),
                    "status_update": Link(href=f"/api/orders/{o.id}/status", method="PATCH"),
                },
            )
        )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
        "_links": {
            "self": {"href": f"/api/orders/my-orders?page={page}&page_size={page_size}", "method": "GET"},
            "next": {"href": f"/api/orders/my-orders?page={page + 1}&page_size={page_size}", "method": "GET"} if (page * page_size) < total else None,
            "prev": {"href": f"/api/orders/my-orders?page={page - 1}&page_size={page_size}", "method": "GET"} if page > 1 else None,
        },
    }


@router.get("/{order_id}")
def get_order(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Consulta el detalle de un pedido. Solo el cliente solicitante, el proveedor o administradores.
    """
    order = order_service.get_by_id(db, order_id, current_user)
    item_url = f"/api/services/{order.service_id}" if order.service_id else f"/api/products/{order.product_id}"
    return with_links(
        OrderOut.model_validate(order),
        {
            "self": Link(href=f"/api/orders/{order.id}"),
            "buyer": Link(href=f"/api/users/{order.buyer_id}"),
            "seller": Link(href=f"/api/users/{order.seller_id}"),
            "item": Link(href=item_url),
            "status_update": Link(href=f"/api/orders/{order.id}/status", method="PATCH"),
            "my_orders": Link(href="/api/orders/my-orders"),
        },
    )


@router.patch("/{order_id}/status")
def update_order_status(
    order_id: uuid.UUID,
    status_data: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Actualiza el estado de la orden (aceptar, rechazar, avanzar, completar o cancelar).
    """
    order = order_service.update_status(db, order_id, status_data.status, current_user)
    return with_links(
        OrderOut.model_validate(order),
        {
            "self": Link(href=f"/api/orders/{order.id}"),
            "my_orders": Link(href="/api/orders/my-orders"),
        },
    )
