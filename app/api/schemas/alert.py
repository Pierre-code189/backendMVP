import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models.category import AlertCategory, UrgencyLevel


class AlertCreate(BaseModel):
    """Schema for reporting a new emergency or hazard alert."""
    title: str = Field(..., min_length=3, max_length=200, description="Título breve de la alerta")
    description: str = Field(..., min_length=10, description="Detalle de la emergencia o peligro")
    category: AlertCategory = Field(..., description="Categoría de la emergencia")
    urgency: UrgencyLevel = Field(default=UrgencyLevel.MEDIUM, description="Nivel de urgencia")
    location: str = Field(..., min_length=3, max_length=255, description="Ubicación o referencia exacta")


class AlertUpdate(BaseModel):
    """Schema for editing an emergency alert."""
    title: Optional[str] = Field(default=None, min_length=3, max_length=200)
    description: Optional[str] = Field(default=None, min_length=10)
    category: Optional[AlertCategory] = None
    urgency: Optional[UrgencyLevel] = None
    location: Optional[str] = Field(default=None, min_length=3, max_length=255)
    is_resolved: Optional[bool] = None
    is_active: Optional[bool] = None


class AlertOut(BaseModel):
    """Public representation of an emergency alert."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str
    category: AlertCategory
    urgency: UrgencyLevel
    location: str
    owner_id: uuid.UUID
    is_resolved: bool
    is_active: bool
    created_at: datetime
