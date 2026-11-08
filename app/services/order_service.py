import uuid
from typing import Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.domain.models.order import Order, OrderItemType, OrderStatus
from app.domain.models.user import User
from app.domain.models.service import Service
from app.domain.models.product import Product
from app.api.schemas.order import OrderCreate


def get_by_id(db: Session, order_id: uuid.UUID, current_user: User) -> Order:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")
    # Only buyer, seller, or staff can access
    if (
        order.buyer_id != current_user.id
        and order.seller_id != current_user.id
        and current_user.role.value not in ("moderator", "administrator")
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin permisos para ver este pedido")
    return order


def get_my_orders(
    db: Session,
    current_user: User,
    role: Optional[str] = None,
    order_status: Optional[OrderStatus] = None,
    item_type: Optional[OrderItemType] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Order], int]:
    query = db.query(Order)

    # Filter by user role (client vs provider)
    if role in ("client", "buyer"):
        query = query.filter(Order.buyer_id == current_user.id)
    elif role in ("provider", "seller"):
        query = query.filter(Order.seller_id == current_user.id)
    else:
        query = query.filter(
            (Order.buyer_id == current_user.id) | (Order.seller_id == current_user.id)
        )

    if order_status:
        query = query.filter(Order.status == order_status)
    if item_type:
        query = query.filter(Order.item_type == item_type)

    total = query.count()
    orders = query.order_by(Order.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return orders, total


def create_order(db: Session, data: OrderCreate, buyer: User) -> Order:
    if data.item_type == OrderItemType.SERVICE:
        service = db.query(Service).filter(Service.id == data.item_id, Service.is_active == True).first()
        if not service:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Servicio no disponible o inexistente")
        if service.owner_id == buyer.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No puedes solicitar tu propio servicio")

        seller_id = service.owner_id
        service_id = service.id
        product_id = None
        unit_price = service.price_per_hour
        total_price = round(unit_price * data.quantity, 2)

    elif data.item_type == OrderItemType.PRODUCT:
        product = db.query(Product).filter(Product.id == data.item_id, Product.is_active == True).first()
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no disponible o inexistente")
        if product.owner_id == buyer.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No puedes comprar tu propio producto")
        if product.stock < data.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stock insuficiente. Disponible: {product.stock}",
            )

        seller_id = product.owner_id
        service_id = None
        product_id = product.id
        unit_price = product.price
        total_price = round(unit_price * data.quantity, 2)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de elemento no válido")

    order = Order(
        buyer_id=buyer.id,
        seller_id=seller_id,
        item_type=data.item_type,
        service_id=service_id,
        product_id=product_id,
        quantity=data.quantity,
        unit_price=unit_price,
        total_price=total_price,
        status=OrderStatus.PENDING,
        notes=data.notes,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def update_status(db: Session, order_id: uuid.UUID, new_status: OrderStatus, current_user: User) -> Order:
    order = get_by_id(db, order_id, current_user)
    is_buyer = order.buyer_id == current_user.id
    is_seller = order.seller_id == current_user.id
    is_staff = current_user.role.value in ("moderator", "administrator")

    # Business rules for transitions
    if is_buyer and not is_seller and not is_staff:
        # Buyer can only cancel if it's still pending
        if new_status != OrderStatus.CANCELLED or order.status != OrderStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El cliente solo puede cancelar solicitudes que aún estén en estado pendiente",
            )
    elif is_seller or is_staff:
        # Provider or staff cannot change already completed or cancelled orders
        if order.status in (OrderStatus.COMPLETED, OrderStatus.CANCELLED, OrderStatus.REJECTED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se puede modificar una orden en estado {order.status.value}",
            )

    # If transitioning to COMPLETED, decrement product stock
    if new_status == OrderStatus.COMPLETED and order.status != OrderStatus.COMPLETED:
        if order.item_type == OrderItemType.PRODUCT and order.product_id:
            product = db.query(Product).filter(Product.id == order.product_id).first()
            if product:
                if product.stock < order.quantity:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Stock insuficiente para completar la entrega. Disponible: {product.stock}",
                    )
                product.stock -= order.quantity

    order.status = new_status
    db.commit()
    db.refresh(order)
    return order
