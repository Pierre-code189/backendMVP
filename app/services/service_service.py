import uuid
from typing import Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.domain.models.service import Service
from app.domain.models.user import User
from app.domain.models.category import ServiceCategory
from app.api.schemas.service import ServiceCreate, ServiceUpdate


def get_by_id(db: Session, service_id: uuid.UUID) -> Service:
    service = db.query(Service).filter(Service.id == service_id, Service.is_active == True).first()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Servicio no encontrado")
    return service


def get_all(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    category: Optional[ServiceCategory] = None,
    owner_id: Optional[uuid.UUID] = None,
) -> tuple[list[Service], int]:
    query = db.query(Service).filter(Service.is_active == True)
    if category:
        query = query.filter(Service.category == category)
    if owner_id:
        query = query.filter(Service.owner_id == owner_id)
    total = query.count()
    services = query.offset((page - 1) * page_size).limit(page_size).all()
    return services, total


def create(db: Session, data: ServiceCreate, owner: User) -> Service:
    service = Service(
        title=data.title,
        description=data.description,
        price_per_hour=data.price_per_hour,
        category=data.category,
        owner_id=owner.id,
    )
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


def update(db: Session, service_id: uuid.UUID, data: ServiceUpdate, current_user: User) -> Service:
    service = get_by_id(db, service_id)
    if service.owner_id != current_user.id and current_user.role.value not in ("moderator", "administrator"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin permisos para modificar este servicio")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(service, field, value)

    db.commit()
    db.refresh(service)
    return service


def delete(db: Session, service_id: uuid.UUID, current_user: User) -> None:
    """Soft delete."""
    service = get_by_id(db, service_id)
    if service.owner_id != current_user.id and current_user.role.value not in ("moderator", "administrator"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin permisos para eliminar este servicio")
    service.is_active = False
    db.commit()
