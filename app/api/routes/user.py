import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.infrastructure.database.connection import get_db
from app.api.schemas.user import UserOut, UserUpdate, UserRoleUpdate
from app.api.schemas.hateoas import Link, with_links
from app.services import user_service
from app.usecases.auth import get_current_active_user, get_current_admin
from app.domain.models.user import User

router = APIRouter(prefix="/users", tags=["Usuarios"])


@router.get("/")
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    """
    Lista los vecinos activos de la plataforma (paginado).
    """
    users, total = user_service.get_all(db, page, page_size)
    items = []
    for u in users:
        items.append(
            with_links(
                UserOut.model_validate(u),
                {"self": Link(href=f"/api/users/{u.id}")},
            )
        )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
        "_links": {
            "self": {"href": f"/api/users?page={page}&page_size={page_size}", "method": "GET"},
            "next": {"href": f"/api/users?page={page + 1}&page_size={page_size}", "method": "GET"} if (page * page_size) < total else None,
            "prev": {"href": f"/api/users?page={page - 1}&page_size={page_size}", "method": "GET"} if page > 1 else None,
        },
    }


@router.get("/{user_id}")
def get_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    """
    Devuelve el perfil público de un vecino.
    """
    user = user_service.get_by_id(db, user_id)
    return with_links(
        UserOut.model_validate(user),
        {
            "self": Link(href=f"/api/users/{user_id}"),
            "services": Link(href=f"/api/services?owner_id={user_id}"),
            "products": Link(href=f"/api/products?owner_id={user_id}"),
            "collection": Link(href="/api/users"),
        },
    )


@router.put("/{user_id}")
def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Actualiza el perfil de un usuario. Solo el propio usuario o un admin pueden hacerlo.
    """
    user = user_service.update(db, user_id, data, current_user)
    return with_links(
        UserOut.model_validate(user),
        {
            "self": Link(href=f"/api/users/{user_id}"),
            "collection": Link(href="/api/users"),
        },
    )


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
def deactivate_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Desactiva (soft delete) la cuenta de un usuario. Solo administradores.
    """
    user = user_service.deactivate(db, user_id, current_user)
    return with_links(
        UserOut.model_validate(user),
        {"collection": Link(href="/api/users")},
    )


@router.patch("/{user_id}/role")
def change_user_role(
    user_id: uuid.UUID,
    role_data: UserRoleUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin),
):
    """
    Cambia el rol de un usuario (administrator, moderator, user). Solo accesible por administradores.
    """
    user = user_service.update_role(db, user_id, role_data.role, admin_user)
    return with_links(
        UserOut.model_validate(user),
        {
            "self": Link(href=f"/api/users/{user_id}"),
            "collection": Link(href="/api/users"),
        },
    )