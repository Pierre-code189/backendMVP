from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.infrastructure.database.connection import get_db
from app.api.schemas.token import Token
from app.api.schemas.user import UserCreate, UserOut
from app.api.schemas.hateoas import Link, with_links
from app.services import user_service
from app.usecases.auth import verify_password, create_access_token, get_current_active_user
from app.domain.models.user import User

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: Session = Depends(get_db)):
    """
    Registra un nuevo vecino en la plataforma.
    """
    user = user_service.create(db, data)
    return with_links(
        UserOut.model_validate(user),
        {
            "self": Link(href=f"/api/users/{user.id}"),
            "login": Link(href="/api/auth/login", method="POST"),
            "collection": Link(href="/api/users"),
        },
    )


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Autentica con username o email + password. Devuelve un JWT Bearer token.
    """
    # Allow login with email OR username
    user = user_service.get_by_email(db, form_data.username)
    if not user:
        user = user_service.get_by_username(db, form_data.username)

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cuenta inactiva")

    access_token = create_access_token(data={"sub": str(user.id), "username": user.username})
    return Token(access_token=access_token)


@router.get("/me")
def me(current_user: User = Depends(get_current_active_user)):
    """
    Devuelve el perfil del usuario autenticado.
    """
    return with_links(
        UserOut.model_validate(current_user),
        {
            "self": Link(href=f"/api/users/{current_user.id}"),
            "edit": Link(href=f"/api/users/{current_user.id}", method="PUT"),
            "my_services": Link(href=f"/api/services?owner_id={current_user.id}"),
            "my_products": Link(href=f"/api/products?owner_id={current_user.id}"),
        },
    )
