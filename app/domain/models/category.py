from enum import Enum


class ServiceCategory(str, Enum):
    """Categories for neighborhood services. Extend as needed."""
    PLUMBING = "plomeria"
    ELECTRICAL = "electricidad"
    CLEANING = "limpieza"
    TUTORING = "tutoria"
    CARPENTRY = "carpinteria"
    GARDENING = "jardineria"
    OTHER = "otro"


class ProductCategory(str, Enum):
    """Categories for neighborhood products. Extend as needed."""
    FOOD = "alimentos"
    CLOTHING = "ropa"
    ELECTRONICS = "electronica"
    FURNITURE = "muebles"
    TOOLS = "herramientas"
    BOOKS = "libros"
    OTHER = "otro"


class AlertCategory(str, Enum):
    """Categories for neighborhood emergency and hazard alerts."""
    INFRASTRUCTURE = "infraestructura"   # buzon de desague abierto, poste caido, cable expuesto
    NATURAL_DISASTER = "desastre_natural" # rio desbordado, inundacion, huaico
    SECURITY = "seguridad"                # lugar peligroso, robo, actividad sospechosa
    ACCIDENT = "accidente"                # choque, fuga de gas, incendio
    HEALTH = "salud"                      # emergencia medica
    OTHER = "otro"


class UrgencyLevel(str, Enum):
    """Urgency / severity level of an alert."""
    LOW = "baja"
    MEDIUM = "media"
    HIGH = "alta"
    CRITICAL = "critica"

