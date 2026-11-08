import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.infrastructure.database.connection import get_db
from app.api.schemas.service import ServiceCreate, ServiceOut, ServiceUpdate
from app.api.schemas.hateoas import Link, with_links
from app.domain.models.category import ServiceCategory
from app.services import service_service
from app.usecases.auth import get_current_active_user
from app.domain.models.user import User

router = APIRouter(prefix="/services", tags=["Servicios"])


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_service(
    data: ServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Publica un nuevo servicio vecinal.
    """
    service = service_service.create(db, data, current_user)
    return with_links(
        ServiceOut.model_validate(service),
        {
            "self": Link(href=f"/api/services/{service.id}"),
            "owner": Link(href=f"/api/users/{service.owner_id}"),
            "edit": Link(href=f"/api/services/{service.id}", method="PUT"),
            "delete": Link(href=f"/api/services/{service.id}", method="DELETE"),
            "collection": Link(href="/api/services"),
        },
    )


@router.get("/")
def list_services(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[ServiceCategory] = Query(default=None),
    owner_id: Optional[uuid.UUID] = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Lista los servicios disponibles. Soporta filtro por categoría y propietario.
    """
    services, total = service_service.get_all(db, page, page_size, category, owner_id)
    items = []
    for s in services:
        items.append(
            with_links(
                ServiceOut.model_validate(s),
                {
                    "self": Link(href=f"/api/services/{s.id}"),
                    "owner": Link(href=f"/api/users/{s.owner_id}"),
                },
            )
        )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
        "_links": {
            "self": {"href": f"/api/services?page={page}&page_size={page_size}", "method": "GET"},
            "next": {"href": f"/api/services?page={page + 1}&page_size={page_size}", "method": "GET"} if (page * page_size) < total else None,
            "prev": {"href": f"/api/services?page={page - 1}&page_size={page_size}", "method": "GET"} if page > 1 else None,
        },
    }


@router.get("/{service_id}")
def get_service(
    service_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Devuelve el detalle de un servicio.
    """
    service = service_service.get_by_id(db, service_id)
    return with_links(
        ServiceOut.model_validate(service),
        {
            "self": Link(href=f"/api/services/{service_id}"),
            "owner": Link(href=f"/api/users/{service.owner_id}"),
            "edit": Link(href=f"/api/services/{service_id}", method="PUT"),
            "delete": Link(href=f"/api/services/{service_id}", method="DELETE"),
            "collection": Link(href="/api/services"),
        },
    )


@router.put("/{service_id}")
def update_service(
    service_id: uuid.UUID,
    data: ServiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Edita un servicio. Solo el propietario o moderadores/admins pueden hacerlo.
    """
    service = service_service.update(db, service_id, data, current_user)
    return with_links(
        ServiceOut.model_validate(service),
        {
            "self": Link(href=f"/api/services/{service_id}"),
            "owner": Link(href=f"/api/users/{service.owner_id}"),
            "collection": Link(href="/api/services"),
        },
    )


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(
    service_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Elimina (soft delete) un servicio. Solo el propietario o moderadores/admins.
    """
    service_service.delete(db, service_id, current_user)
