from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.routes import api
from app.infrastructure.database.base import Base
from app.infrastructure.database.connection import engine

# Import all models so SQLAlchemy registers them before create_all
from app.domain.models import user, service, product, alert, order  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all tables and columns on startup (dev/MVP mode)."""
    Base.metadata.create_all(bind=engine)
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(20) UNIQUE;"))
            conn.commit()
    except Exception:
        pass
    yield


app = FastAPI(
    title="API Vecinal",
    version="0.1.0",
    description="REST API para la comunidad vecinal — servicios y productos entre vecinos.",
    lifespan=lifespan,
)

# Enable CORS for frontend applications
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "message": "API Vecinal",
        "_links": {
            "api": {"href": "/api/", "method": "GET"},
            "docs": {"href": "/docs", "method": "GET"},
            "redoc": {"href": "/redoc", "method": "GET"},
        },
    }


app.include_router(api.apiRouter)