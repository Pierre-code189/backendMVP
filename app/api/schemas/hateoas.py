import uuid
from typing import Dict, Any

from pydantic import BaseModel


class Link(BaseModel):
    href: str
    method: str = "GET"


def with_links(model: BaseModel, links: Dict[str, Link]) -> Dict[str, Any]:
    """
    Serializes a Pydantic model and injects HATEOAS _links.
    Implements Fielding's HATEOAS (Hypermedia As The Engine Of Application State) constraint.

    Usage:
        return with_links(UserOut.model_validate(user), {
            "self": Link(href=f"/api/users/{user.id}"),
        })
    """
    data = model.model_dump()

    # Ensure UUIDs are serialized as strings
    for key, value in data.items():
        if isinstance(value, uuid.UUID):
            data[key] = str(value)

    data["_links"] = {k: v.model_dump() for k, v in links.items()}
    return data
