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
