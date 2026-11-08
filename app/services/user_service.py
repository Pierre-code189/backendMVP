import uuid
from typing import Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.domain.models.user import User
from app.api.schemas.user import UserCreate, UserUpdate
from app.usecases.auth import hash_password


def get_by_id(db: Session, user_id: uuid.UUID) -> User:
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return user


def get_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def get_all(db: Session, page: int = 1, page_size: int = 20) -> tuple[list[User], int]:
    query = db.query(User).filter(User.is_active == True)
    total = query.count()
    users = query.offset((page - 1) * page_size).limit(page_size).all()
    return users, total


def create(db: Session, data: UserCreate) -> User:
    # Check uniqueness
    if get_by_email(db, data.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El email ya está registrado")
    if get_by_username(db, data.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El nombre de usuario ya está en uso")
    if not data.dni:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El DNI es obligatorio")
    existing_dni = db.query(User).filter(User.dni == data.dni).first()
    if existing_dni:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El DNI ya está registrado")

    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        dni=data.dni,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update(db: Session, user_id: uuid.UUID, data: UserUpdate, current_user: User) -> User:
    user = get_by_id(db, user_id)
    # Only the user themselves or an admin can update
    if user.id != current_user.id and current_user.role.value not in ("moderator", "administrator"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin permisos para modificar este usuario")

    # Uniqueness checks if updating email or dni
    if data.email and data.email != user.email:
        if get_by_email(db, data.email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El email ya está registrado")

    if data.dni and data.dni != user.dni:
        if db.query(User).filter(User.dni == data.dni).first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El DNI ya está registrado")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


def deactivate(db: Session, user_id: uuid.UUID, current_user: User) -> User:
    """Soft delete — sets is_active=False."""
    user = get_by_id(db, user_id)
    if current_user.role.value != "administrator":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo administradores pueden desactivar cuentas")
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user
