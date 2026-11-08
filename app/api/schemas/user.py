import re
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.domain.models.role import Roles


class UserCreate(BaseModel):
    """Schema for user registration."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1, max_length=150)
    dni: str = Field(..., min_length=8, max_length=20, description="DNI único obligatorio")
    phone: str = Field(..., description="Teléfono celular de Perú (+51 seguido de 9 dígitos que inician con 9)")

    @field_validator("phone")
    @classmethod
    def validate_peru_phone(cls, v: str) -> str:
        cleaned = re.sub(r"[\s\-]", "", v)
        if not re.match(r"^\+519\d{8}$", cleaned):
            raise ValueError("El teléfono debe seguir el formato de Perú (+51 seguido de 9 dígitos que comiencen con 9, ej: +51987654321)")
        return cleaned


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    full_name: Optional[str] = Field(default=None, max_length=150)
    email: Optional[EmailStr] = None
    dni: Optional[str] = Field(default=None, min_length=8, max_length=20)
    phone: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def validate_peru_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        cleaned = re.sub(r"[\s\-]", "", v)
        if not re.match(r"^\+519\d{8}$", cleaned):
            raise ValueError("El teléfono debe seguir el formato de Perú (+51 seguido de 9 dígitos que comiencen con 9, ej: +51987654321)")
        return cleaned


class UserRoleUpdate(BaseModel):
    """Schema for administrator updating user role."""
    role: Roles


class UserOut(BaseModel):
    """Public representation of a user (no password)."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    email: str
    full_name: str
    dni: str
    phone: str
    role: Roles
    is_active: bool
    created_at: datetime


class UserPublic(BaseModel):
    """Minimal public profile visible to other neighbors."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    full_name: str
    role: Roles
    is_active: bool
