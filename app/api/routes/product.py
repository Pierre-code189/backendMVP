import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.infrastructure.database.connection import get_db
from app.api.schemas.product import ProductCreate, ProductOut, ProductUpdate
from app.api.schemas.hateoas import Link, with_links
from app.domain.models.category import ProductCategory
from app.services import product_service
from app.usecases.auth import get_current_active_user
from app.domain.models.user import User

router = APIRouter(prefix="/products", tags=["Productos"])


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_product(
    data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Publica un nuevo producto para la venta vecinal.
    """
    product = product_service.create(db, data, current_user)
    return with_links(
        ProductOut.model_validate(product),
        {
            "self": Link(href=f"/api/products/{product.id}"),
            "owner": Link(href=f"/api/users/{product.owner_id}"),
            "edit": Link(href=f"/api/products/{product.id}", method="PUT"),
            "delete": Link(href=f"/api/products/{product.id}", method="DELETE"),
            "collection": Link(href="/api/products"),
        },
    )


@router.get("/")
def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[ProductCategory] = Query(default=None),
    owner_id: Optional[uuid.UUID] = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Lista los productos disponibles. Soporta filtro por categoría y propietario.
    """
    products, total = product_service.get_all(db, page, page_size, category, owner_id)
    items = []
    for p in products:
        items.append(
            with_links(
                ProductOut.model_validate(p),
                {
                    "self": Link(href=f"/api/products/{p.id}"),
                    "owner": Link(href=f"/api/users/{p.owner_id}"),
                },
            )
        )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
        "_links": {
            "self": {"href": f"/api/products?page={page}&page_size={page_size}", "method": "GET"},
            "next": {"href": f"/api/products?page={page + 1}&page_size={page_size}", "method": "GET"} if (page * page_size) < total else None,
            "prev": {"href": f"/api/products?page={page - 1}&page_size={page_size}", "method": "GET"} if page > 1 else None,
        },
    }


@router.get("/{product_id}")
def get_product(
    product_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Devuelve el detalle de un producto.
    """
    product = product_service.get_by_id(db, product_id)
    return with_links(
        ProductOut.model_validate(product),
        {
            "self": Link(href=f"/api/products/{product_id}"),
            "owner": Link(href=f"/api/users/{product.owner_id}"),
            "edit": Link(href=f"/api/products/{product_id}", method="PUT"),
            "delete": Link(href=f"/api/products/{product_id}", method="DELETE"),
            "collection": Link(href="/api/products"),
        },
    )


@router.put("/{product_id}")
def update_product(
    product_id: uuid.UUID,
    data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Edita un producto. Solo el propietario o moderadores/admins.
    """
    product = product_service.update(db, product_id, data, current_user)
    return with_links(
        ProductOut.model_validate(product),
        {
            "self": Link(href=f"/api/products/{product_id}"),
            "owner": Link(href=f"/api/users/{product.owner_id}"),
            "collection": Link(href="/api/products"),
        },
    )


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Elimina (soft delete) un producto. Solo el propietario o moderadores/admins.
    """
    product_service.delete(db, product_id, current_user)
