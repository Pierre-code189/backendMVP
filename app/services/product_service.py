import uuid
from typing import Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.domain.models.product import Product
from app.domain.models.user import User
from app.domain.models.category import ProductCategory
from app.api.schemas.product import ProductCreate, ProductUpdate


def get_by_id(db: Session, product_id: uuid.UUID) -> Product:
    product = db.query(Product).filter(Product.id == product_id, Product.is_active == True).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    return product


def get_all(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    category: Optional[ProductCategory] = None,
    owner_id: Optional[uuid.UUID] = None,
) -> tuple[list[Product], int]:
    query = db.query(Product).filter(Product.is_active == True)
    if category:
        query = query.filter(Product.category == category)
    if owner_id:
        query = query.filter(Product.owner_id == owner_id)
    total = query.count()
    products = query.offset((page - 1) * page_size).limit(page_size).all()
    return products, total


def create(db: Session, data: ProductCreate, owner: User) -> Product:
    product = Product(
        title=data.title,
        description=data.description,
        price=data.price,
        stock=data.stock,
        category=data.category,
        owner_id=owner.id,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update(db: Session, product_id: uuid.UUID, data: ProductUpdate, current_user: User) -> Product:
    product = get_by_id(db, product_id)
    if product.owner_id != current_user.id and current_user.role.value not in ("moderator", "administrator"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin permisos para modificar este producto")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


def delete(db: Session, product_id: uuid.UUID, current_user: User) -> None:
    """Soft delete."""
    product = get_by_id(db, product_id)
    if product.owner_id != current_user.id and current_user.role.value not in ("moderator", "administrator"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin permisos para eliminar este producto")
    product.is_active = False
    db.commit()
