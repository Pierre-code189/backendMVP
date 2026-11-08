import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.infrastructure.database.connection import get_db
from app.api.schemas.alert import AlertCreate, AlertOut, AlertUpdate
from app.api.schemas.hateoas import Link, with_links
from app.domain.models.category import AlertCategory, UrgencyLevel
from app.services import alert_service
from app.usecases.auth import get_current_active_user
from app.domain.models.user import User

router = APIRouter(prefix="/alerts", tags=["Alertas de Emergencia"])


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_alert(
    data: AlertCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Publica una alerta vecinal de emergencia o peligro (ej. buzon abierto, rio desbordado, zona insegura).
    Requiere inicio de sesión.
    """
    alert = alert_service.create(db, data, current_user)
    return with_links(
        AlertOut.model_validate(alert),
        {
            "self": Link(href=f"/api/alerts/{alert.id}"),
            "owner": Link(href=f"/api/users/{alert.owner_id}"),
            "edit": Link(href=f"/api/alerts/{alert.id}", method="PUT"),
            "delete": Link(href=f"/api/alerts/{alert.id}", method="DELETE"),
            "collection": Link(href="/api/alerts"),
        },
    )


@router.get("/")
def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[AlertCategory] = Query(default=None),
    urgency: Optional[UrgencyLevel] = Query(default=None),
    owner_id: Optional[uuid.UUID] = Query(default=None),
    is_resolved: Optional[bool] = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Lista las alertas de emergencia del vecindario. Consulta pública sin login.
    """
    alerts, total = alert_service.get_all(db, page, page_size, category, urgency, owner_id, is_resolved)
    items = []
    for a in alerts:
        items.append(
            with_links(
                AlertOut.model_validate(a),
                {
                    "self": Link(href=f"/api/alerts/{a.id}"),
                    "owner": Link(href=f"/api/users/{a.owner_id}"),
                },
            )
        )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
        "_links": {
            "self": {"href": f"/api/alerts?page={page}&page_size={page_size}", "method": "GET"},
            "next": {"href": f"/api/alerts?page={page + 1}&page_size={page_size}", "method": "GET"} if (page * page_size) < total else None,
            "prev": {"href": f"/api/alerts?page={page - 1}&page_size={page_size}", "method": "GET"} if page > 1 else None,
        },
    }


@router.get("/{alert_id}")
def get_alert(
    alert_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Consulta el detalle de una alerta de emergencia. Acceso público.
    """
    alert = alert_service.get_by_id(db, alert_id)
    return with_links(
        AlertOut.model_validate(alert),
        {
            "self": Link(href=f"/api/alerts/{alert_id}"),
            "owner": Link(href=f"/api/users/{alert.owner_id}"),
            "edit": Link(href=f"/api/alerts/{alert_id}", method="PUT"),
            "delete": Link(href=f"/api/alerts/{alert_id}", method="DELETE"),
            "collection": Link(href="/api/alerts"),
        },
    )


@router.put("/{alert_id}")
def update_alert(
    alert_id: uuid.UUID,
    data: AlertUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Edita una alerta (por ejemplo para actualizar detalles o marcarla como resuelta).
    Solo el vecino creador o moderadores/administradores pueden modificarla.
    """
    alert = alert_service.update(db, alert_id, data, current_user)
    return with_links(
        AlertOut.model_validate(alert),
        {
            "self": Link(href=f"/api/alerts/{alert_id}"),
            "owner": Link(href=f"/api/users/{alert.owner_id}"),
            "collection": Link(href="/api/alerts"),
        },
    )


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert(
    alert_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Elimina (soft delete) una alerta.
    Solo el vecino creador o moderadores/administradores pueden eliminarla.
    """
    alert_service.delete(db, alert_id, current_user)
