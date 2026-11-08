from fastapi import APIRouter

from app.api.routes import user, auth, service, product

apiRouter = APIRouter(prefix="/api", tags=["API"])

apiRouter.include_router(auth.router)
apiRouter.include_router(user.router)
apiRouter.include_router(service.router)
apiRouter.include_router(product.router)


@apiRouter.get("/")
def api_root():
    """
    API root — entry point with HATEOAS navigation links (Fielding constraint).
    """
    return {
        "message": "API Vecinal MVP",
        "_links": {
            "auth_register": {"href": "/api/auth/register", "method": "POST"},
            "auth_login":    {"href": "/api/auth/login", "method": "POST"},
            "auth_me":       {"href": "/api/auth/me", "method": "GET"},
            "users":         {"href": "/api/users", "method": "GET"},
            "services":      {"href": "/api/services", "method": "GET"},
            "products":      {"href": "/api/products", "method": "GET"},
        },
    }
