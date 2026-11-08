import uuid
from typing import Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.domain.models.alert import Alert
from app.domain.models.user import User
from app.domain.models.category import AlertCategory, UrgencyLevel
from app.api.schemas.alert import AlertCreate, AlertUpdate


def get_by_id(db: Session, alert_id: uuid.UUID) -> Alert:
    alert = db.query(Alert).filter(Alert.id == alert_id, Alert.is_active == True).first()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerta no encontrada")
    return alert


def get_all(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    category: Optional[AlertCategory] = None,
    urgency: Optional[UrgencyLevel] = None,
    owner_id: Optional[uuid.UUID] = None,
    is_resolved: Optional[bool] = None,
) -> tuple[list[Alert], int]:
    query = db.query(Alert).filter(Alert.is_active == True)
    if category:
        query = query.filter(Alert.category == category)
    if urgency:
        query = query.filter(Alert.urgency == urgency)
    if owner_id:
        query = query.filter(Alert.owner_id == owner_id)
    if is_resolved is not None:
        query = query.filter(Alert.is_resolved == is_resolved)
    total = query.count()
    alerts = query.order_by(Alert.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return alerts, total


def create(db: Session, data: AlertCreate, owner: User) -> Alert:
    alert = Alert(
        title=data.title,
        description=data.description,
        category=data.category,
        urgency=data.urgency,
        location=data.location,
        owner_id=owner.id,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def update(db: Session, alert_id: uuid.UUID, data: AlertUpdate, current_user: User) -> Alert:
    alert = get_by_id(db, alert_id)
    if alert.owner_id != current_user.id and current_user.role.value not in ("moderator", "administrator"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin permisos para modificar esta alerta")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(alert, field, value)

    db.commit()
    db.refresh(alert)
    return alert


def delete(db: Session, alert_id: uuid.UUID, current_user: User) -> None:
    """Soft delete."""
    alert = get_by_id(db, alert_id)
    if alert.owner_id != current_user.id and current_user.role.value not in ("moderator", "administrator"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin permisos para eliminar esta alerta")
    alert.is_active = False
    db.commit()
