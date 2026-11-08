from typing import TypeVar, Generic, List, Any, Dict
from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response with HATEOAS navigation links."""
    total: int
    page: int
    page_size: int
    items: List[T]
    _links: Dict[str, Any] = {}
