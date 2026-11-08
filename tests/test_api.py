import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.domain.models.role import Roles
from app.domain.models.user import User
from app.infrastructure.database.connection import SessionLocal

client = TestClient(app)


def test_root_and_docs_public():
    """Root, docs, and HATEOAS endpoints are publicly accessible."""
    r = client.get("/")
    assert r.status_code == 200
    assert "_links" in r.json()

    r_api = client.get("/api/")
    assert r_api.status_code == 200
    assert "_links" in r_api.json()

    r_docs = client.get("/openapi.json")
    assert r_docs.status_code == 200


def test_dni_required_and_unique():
    """DNI is required on signup and must be unique per user account."""
    suffix = uuid.uuid4().hex[:6]
    dni_test = f"7{uuid.uuid4().int % 10000000:07d}"

    # 1. Registration fails without DNI
    bad_user = {
        "username": f"user_nodni_{suffix}",
        "email": f"nodni_{suffix}@example.com",
        "password": "Password123!",
        "full_name": "Vecino Sin DNI",
    }
    r_no_dni = client.post("/api/auth/register", json=bad_user)
    assert r_no_dni.status_code == 422

    # 2. Registration succeeds with valid unique DNI
    good_user1 = {
        "username": f"user_dni1_{suffix}",
        "email": f"dni1_{suffix}@example.com",
        "password": "Password123!",
        "full_name": "Vecino Con DNI",
        "dni": dni_test,
    }
    r_ok = client.post("/api/auth/register", json=good_user1)
    assert r_ok.status_code == 201
    assert r_ok.json()["dni"] == dni_test

    # 3. Registration fails if another account uses the exact same DNI (duplicate)
    duplicate_dni_user = {
        "username": f"user_dni2_{suffix}",
        "email": f"dni2_{suffix}@example.com",
        "password": "Password123!",
        "full_name": "Vecino Clon DNI",
        "dni": dni_test,
    }
    r_dup = client.post("/api/auth/register", json=duplicate_dni_user)
    assert r_dup.status_code == 409
    assert "DNI" in r_dup.json()["detail"]


def test_catalog_public_read_access():
    """Services and Products catalogs are public: anyone can list and view details without logging in."""
    # List services without auth header
    r_srv = client.get("/api/services/")
    assert r_srv.status_code == 200
    assert "items" in r_srv.json()
    assert "total" in r_srv.json()

    # List products without auth header
    r_prod = client.get("/api/products/")
    assert r_prod.status_code == 200
    assert "items" in r_prod.json()
    assert "total" in r_prod.json()


def test_offering_services_and_products_strictly_requires_auth():
    """Unauthenticated users cannot create, update or delete services/products."""
    fake_uuid = str(uuid.uuid4())

    # 1. Unauthenticated creation is rejected (401)
    r_post_srv = client.post(
        "/api/services/",
        json={
            "title": "Hack Plomería",
            "description": "Intento anónimo sin credenciales",
            "price_per_hour": 50.0,
            "category": "plomeria",
        },
    )
    assert r_post_srv.status_code == 401

    r_post_prod = client.post(
        "/api/products/",
        json={
            "title": "Hack Producto",
            "description": "Intento anónimo de publicar producto",
            "price": 100.0,
            "stock": 1,
            "category": "otro",
        },
    )
    assert r_post_prod.status_code == 401

    # 2. Unauthenticated modification is rejected (401)
    r_put_srv = client.put(f"/api/services/{fake_uuid}", json={"price_per_hour": 10.0})
    assert r_put_srv.status_code == 401

    r_put_prod = client.put(f"/api/products/{fake_uuid}", json={"price": 10.0})
    assert r_put_prod.status_code == 401

    # 3. Unauthenticated deletion is rejected (401)
    r_del_srv = client.delete(f"/api/services/{fake_uuid}")
    assert r_del_srv.status_code == 401

    r_del_prod = client.delete(f"/api/products/{fake_uuid}")
    assert r_del_prod.status_code == 401


def test_only_creator_can_edit_and_delete_service_and_product():
    """Logged-in users can only modify and delete their own published offerings."""
    suffix = uuid.uuid4().hex[:6]
    dni_owner = f"1{uuid.uuid4().int % 10000000:07d}"
    dni_other = f"2{uuid.uuid4().int % 10000000:07d}"

    # Register Creator (User A)
    client.post(
        "/api/auth/register",
        json={
            "username": f"owner_{suffix}",
            "email": f"owner_{suffix}@example.com",
            "password": "Password123!",
            "full_name": "Vecino Creador",
            "dni": dni_owner,
        },
    )
    token_owner = client.post(
        "/api/auth/login",
        data={"username": f"owner_{suffix}@example.com", "password": "Password123!"},
    ).json()["access_token"]
    headers_owner = {"Authorization": f"Bearer {token_owner}"}

    # Register Other User (User B)
    client.post(
        "/api/auth/register",
        json={
            "username": f"other_{suffix}",
            "email": f"other_{suffix}@example.com",
            "password": "Password123!",
            "full_name": "Otro Vecino",
            "dni": dni_other,
        },
    )
    token_other = client.post(
        "/api/auth/login",
        data={"username": f"other_{suffix}@example.com", "password": "Password123!"},
    ).json()["access_token"]
    headers_other = {"Authorization": f"Bearer {token_other}"}

    # ==========================================
    # SERVICE LIFECYCLE BY OWNER
    # ==========================================
    srv_payload = {
        "title": "Reparación de cerraduras",
        "description": "Cerrajería vecinal 24/7 disponible para todos los bloques.",
        "price_per_hour": 35.0,
        "category": "otro",
    }
    r_create_srv = client.post("/api/services/", json=srv_payload, headers=headers_owner)
    assert r_create_srv.status_code == 201
    srv_id = r_create_srv.json()["id"]

    # Public can view detail
    r_public_srv = client.get(f"/api/services/{srv_id}")
    assert r_public_srv.status_code == 200
    assert r_public_srv.json()["title"] == srv_payload["title"]

    # User B attempts to edit User A's service -> 403 Forbidden
    r_unauth_srv_edit = client.put(
        f"/api/services/{srv_id}",
        json={"price_per_hour": 1.0},
        headers=headers_other,
    )
    assert r_unauth_srv_edit.status_code == 403

    # User B attempts to delete User A's service -> 403 Forbidden
    r_unauth_srv_del = client.delete(f"/api/services/{srv_id}", headers=headers_other)
    assert r_unauth_srv_del.status_code == 403

    # User A (Creator) successfully edits service -> 200
    r_auth_srv_edit = client.put(
        f"/api/services/{srv_id}",
        json={"price_per_hour": 45.0},
        headers=headers_owner,
    )
    assert r_auth_srv_edit.status_code == 200
    assert r_auth_srv_edit.json()["price_per_hour"] == 45.0

    # User A (Creator) successfully deletes service -> 204
    r_auth_srv_del = client.delete(f"/api/services/{srv_id}", headers=headers_owner)
    assert r_auth_srv_del.status_code == 204

    # Deleted service now returns 404 (soft deleted)
    assert client.get(f"/api/services/{srv_id}").status_code == 404

    # ==========================================
    # PRODUCT LIFECYCLE BY OWNER
    # ==========================================
    prod_payload = {
        "title": "Taladro inalámbrico",
        "description": "Taladro percutor con 2 baterías de litio y maletín.",
        "price": 120.0,
        "stock": 1,
        "category": "herramientas",
    }
    r_create_prod = client.post("/api/products/", json=prod_payload, headers=headers_owner)
    assert r_create_prod.status_code == 201
    prod_id = r_create_prod.json()["id"]

    # Public can view product detail
    r_public_prod = client.get(f"/api/products/{prod_id}")
    assert r_public_prod.status_code == 200
    assert r_public_prod.json()["title"] == prod_payload["title"]

    # User B attempts to edit User A's product -> 403 Forbidden
    r_unauth_prod_edit = client.put(
        f"/api/products/{prod_id}",
        json={"price": 5.0},
        headers=headers_other,
    )
    assert r_unauth_prod_edit.status_code == 403

    # User B attempts to delete User A's product -> 403 Forbidden
    r_unauth_prod_del = client.delete(f"/api/products/{prod_id}", headers=headers_other)
    assert r_unauth_prod_del.status_code == 403

    # User A (Creator) successfully edits product -> 200
    r_auth_prod_edit = client.put(
        f"/api/products/{prod_id}",
        json={"price": 110.0, "stock": 2},
        headers=headers_owner,
    )
    assert r_auth_prod_edit.status_code == 200
    assert r_auth_prod_edit.json()["price"] == 110.0
    assert r_auth_prod_edit.json()["stock"] == 2

    # User A (Creator) successfully deletes product -> 204
    r_auth_prod_del = client.delete(f"/api/products/{prod_id}", headers=headers_owner)
    assert r_auth_prod_del.status_code == 204

    # Deleted product now returns 404
    assert client.get(f"/api/products/{prod_id}").status_code == 404
