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
    phone_test = f"+519{uuid.uuid4().int % 100000000:08d}"

    # 1. Registration fails without DNI
    bad_user = {
        "username": f"user_nodni_{suffix}",
        "email": f"nodni_{suffix}@example.com",
        "password": "Password123!",
        "full_name": "Vecino Sin DNI",
        "phone": phone_test,
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
        "phone": phone_test,
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
        "phone": f"+519{uuid.uuid4().int % 100000000:08d}",
    }
    r_dup = client.post("/api/auth/register", json=duplicate_dni_user)
    assert r_dup.status_code == 409
    assert "DNI" in r_dup.json()["detail"]


def test_peru_phone_format_and_uniqueness():
    """Phone must follow Peru cellular format (+51 followed by 9 digits starting with 9) and be unique."""
    suffix = uuid.uuid4().hex[:6]
    dni_base = uuid.uuid4().int % 10000000
    phone_unique = f"+519{uuid.uuid4().int % 100000000:08d}"

    # 1. Invalid phone formats
    # Missing country code +51
    r_bad1 = client.post(
        "/api/auth/register",
        json={
            "username": f"bad_ph1_{suffix}",
            "email": f"bad_ph1_{suffix}@example.com",
            "password": "Password123!",
            "full_name": "Test Phone",
            "dni": f"1{dni_base:07d}",
            "phone": "987654321",
        },
    )
    assert r_bad1.status_code == 422

    # Doesn't start with 9 after +51
    r_bad2 = client.post(
        "/api/auth/register",
        json={
            "username": f"bad_ph2_{suffix}",
            "email": f"bad_ph2_{suffix}@example.com",
            "password": "Password123!",
            "full_name": "Test Phone",
            "dni": f"2{dni_base:07d}",
            "phone": "+51887654321",
        },
    )
    assert r_bad2.status_code == 422

    # Too short
    r_bad3 = client.post(
        "/api/auth/register",
        json={
            "username": f"bad_ph3_{suffix}",
            "email": f"bad_ph3_{suffix}@example.com",
            "password": "Password123!",
            "full_name": "Test Phone",
            "dni": f"3{dni_base:07d}",
            "phone": "+5198765432",
        },
    )
    assert r_bad3.status_code == 422

    # 2. Valid phone (with spaces that should be normalized)
    phone_with_spaces = f"+51 9{phone_unique[4:7]} {phone_unique[7:10]} {phone_unique[10:]}"
    r_valid = client.post(
        "/api/auth/register",
        json={
            "username": f"good_ph_{suffix}",
            "email": f"good_ph_{suffix}@example.com",
            "password": "Password123!",
            "full_name": "Vecino Con Buen Telefono",
            "dni": f"4{dni_base:07d}",
            "phone": phone_with_spaces,
        },
    )
    assert r_valid.status_code == 201
    assert r_valid.json()["phone"] == phone_unique

    # 3. Duplicate phone registration rejected (409 Conflict)
    r_dup_phone = client.post(
        "/api/auth/register",
        json={
            "username": f"dup_ph_{suffix}",
            "email": f"dup_ph_{suffix}@example.com",
            "password": "Password123!",
            "full_name": "Vecino Clon Telefono",
            "dni": f"5{dni_base:07d}",
            "phone": phone_unique,
        },
    )
    assert r_dup_phone.status_code == 409
    assert "teléfono" in r_dup_phone.json()["detail"].lower()


def test_admin_and_moderator_role_management():
    """Only administrators can change user roles."""
    suffix = uuid.uuid4().hex[:6]
    dni_num = uuid.uuid4().int % 10000000

    # 1. Register regular user
    r_u1 = client.post(
        "/api/auth/register",
        json={
            "username": f"reg_user_{suffix}",
            "email": f"reg_{suffix}@example.com",
            "password": "Password123!",
            "full_name": "Usuario Regular",
            "dni": f"6{dni_num:07d}",
            "phone": f"+5191{uuid.uuid4().int % 10000000:07d}",
        },
    )
    assert r_u1.status_code == 201
    user_id = r_u1.json()["id"]

    token_u1 = client.post(
        "/api/auth/login",
        data={"username": f"reg_{suffix}@example.com", "password": "Password123!"},
    ).json()["access_token"]
    headers_u1 = {"Authorization": f"Bearer {token_u1}"}

    # 2. Register admin user and set role in DB
    r_admin = client.post(
        "/api/auth/register",
        json={
            "username": f"admin_usr_{suffix}",
            "email": f"admin_{suffix}@example.com",
            "password": "Password123!",
            "full_name": "Usuario Admin",
            "dni": f"7{dni_num:07d}",
            "phone": f"+5192{uuid.uuid4().int % 10000000:07d}",
        },
    )
    assert r_admin.status_code == 201
    admin_id = r_admin.json()["id"]

    db = SessionLocal()
    admin_record = db.query(User).filter(User.id == uuid.UUID(admin_id)).first()
    admin_record.role = Roles.ADMIN
    db.commit()
    db.close()

    token_admin = client.post(
        "/api/auth/login",
        data={"username": f"admin_{suffix}@example.com", "password": "Password123!"},
    ).json()["access_token"]
    headers_admin = {"Authorization": f"Bearer {token_admin}"}

    # 3. Regular user attempts to promote themselves or anyone -> 403 Forbidden
    r_fail_promote = client.patch(
        f"/api/users/{user_id}/role",
        json={"role": "administrator"},
        headers=headers_u1,
    )
    assert r_fail_promote.status_code == 403

    # 4. Administrator successfully promotes user to moderator
    r_ok_promote = client.patch(
        f"/api/users/{user_id}/role",
        json={"role": "moderator"},
        headers=headers_admin,
    )
    assert r_ok_promote.status_code == 200
    assert r_ok_promote.json()["role"] == "moderator"


def test_catalog_public_read_access():
    """Services and Products catalogs are public: anyone can list and view details without logging in."""
    r_srv = client.get("/api/services/")
    assert r_srv.status_code == 200
    assert "items" in r_srv.json()
    assert "total" in r_srv.json()

    r_prod = client.get("/api/products/")
    assert r_prod.status_code == 200
    assert "items" in r_prod.json()
    assert "total" in r_prod.json()


def test_offering_services_and_products_strictly_requires_auth():
    """Unauthenticated users cannot create, update or delete services/products."""
    fake_uuid = str(uuid.uuid4())

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

    r_put_srv = client.put(f"/api/services/{fake_uuid}", json={"price_per_hour": 10.0})
    assert r_put_srv.status_code == 401

    r_put_prod = client.put(f"/api/products/{fake_uuid}", json={"price": 10.0})
    assert r_put_prod.status_code == 401

    r_del_srv = client.delete(f"/api/services/{fake_uuid}")
    assert r_del_srv.status_code == 401

    r_del_prod = client.delete(f"/api/products/{fake_uuid}")
    assert r_del_prod.status_code == 401


def test_only_creator_can_edit_and_delete_service_and_product():
    """Logged-in users can only modify and delete their own published offerings."""
    suffix = uuid.uuid4().hex[:6]
    dni_owner = f"8{uuid.uuid4().int % 10000000:07d}"
    dni_other = f"9{uuid.uuid4().int % 10000000:07d}"
    phone_owner = f"+5193{uuid.uuid4().int % 10000000:07d}"
    phone_other = f"+5194{uuid.uuid4().int % 10000000:07d}"

    # Register Creator (User A)
    client.post(
        "/api/auth/register",
        json={
            "username": f"owner_{suffix}",
            "email": f"owner_{suffix}@example.com",
            "password": "Password123!",
            "full_name": "Vecino Creador",
            "dni": dni_owner,
            "phone": phone_owner,
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
            "phone": phone_other,
        },
    )
    token_other = client.post(
        "/api/auth/login",
        data={"username": f"other_{suffix}@example.com", "password": "Password123!"},
    ).json()["access_token"]
    headers_other = {"Authorization": f"Bearer {token_other}"}

    # Create Service
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

    # Create Product
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

    # User A (Creator) successfully deletes product -> 204
    r_auth_prod_del = client.delete(f"/api/products/{prod_id}", headers=headers_owner)
    assert r_auth_prod_del.status_code == 204
    assert client.get(f"/api/products/{prod_id}").status_code == 404


def test_emergency_alerts_lifecycle():
    """Emergency alerts can be viewed publicly, created by logged-in users, edited/deleted by author or staff."""
    suffix = uuid.uuid4().hex[:6]
    dni_author = f"5{uuid.uuid4().int % 10000000:07d}"
    dni_other = f"6{uuid.uuid4().int % 10000000:07d}"
    phone_author = f"+5195{uuid.uuid4().int % 10000000:07d}"
    phone_other = f"+5196{uuid.uuid4().int % 10000000:07d}"

    # 1. Register Author (User A)
    client.post(
        "/api/auth/register",
        json={
            "username": f"alert_author_{suffix}",
            "email": f"alert_author_{suffix}@example.com",
            "password": "Password123!",
            "full_name": "Vecino Alerta",
            "dni": dni_author,
            "phone": phone_author,
        },
    )
    token_author = client.post(
        "/api/auth/login",
        data={"username": f"alert_author_{suffix}@example.com", "password": "Password123!"},
    ).json()["access_token"]
    headers_author = {"Authorization": f"Bearer {token_author}"}

    # 2. Register Other User (User B)
    client.post(
        "/api/auth/register",
        json={
            "username": f"alert_other_{suffix}",
            "email": f"alert_other_{suffix}@example.com",
            "password": "Password123!",
            "full_name": "Vecino Observador",
            "dni": dni_other,
            "phone": phone_other,
        },
    )
    token_other = client.post(
        "/api/auth/login",
        data={"username": f"alert_other_{suffix}@example.com", "password": "Password123!"},
    ).json()["access_token"]
    headers_other = {"Authorization": f"Bearer {token_other}"}

    # 3. Unauthenticated attempt to publish alert -> 401
    r_unauth_alert = client.post(
        "/api/alerts/",
        json={
            "title": "Buzón de desagüe abierto sin tapa",
            "description": "Peligro inminente para peatones y autos en la esquina de la cuadra 4.",
            "category": "infraestructura",
            "urgency": "alta",
            "location": "Av. Los Sauces cdra 4 esquina con Jr. Tarapacá",
        },
    )
    assert r_unauth_alert.status_code == 401

    # 4. Author publishes alert -> 201
    alert_payload = {
        "title": "Buzón de desagüe abierto sin tapa",
        "description": "Peligro inminente para peatones y autos en la esquina de la cuadra 4.",
        "category": "infraestructura",
        "urgency": "alta",
        "location": "Av. Los Sauces cdra 4 esquina con Jr. Tarapacá",
    }
    r_create = client.post("/api/alerts/", json=alert_payload, headers=headers_author)
    assert r_create.status_code == 201
    alert_data = r_create.json()
    alert_id = alert_data["id"]
    assert alert_data["title"] == alert_payload["title"]
    assert alert_data["category"] == "infraestructura"
    assert alert_data["urgency"] == "alta"
    assert alert_data["is_resolved"] is False

    # 5. Public listing of alerts without auth -> 200
    r_list = client.get("/api/alerts/")
    assert r_list.status_code == 200
    assert any(a["id"] == alert_id for a in r_list.json()["items"])

    # 6. Public filter by category -> 200
    r_filter = client.get("/api/alerts/?category=infraestructura")
    assert r_filter.status_code == 200
    assert any(a["id"] == alert_id for a in r_filter.json()["items"])

    # 7. Public detail of alert -> 200
    r_get = client.get(f"/api/alerts/{alert_id}")
    assert r_get.status_code == 200
    assert r_get.json()["location"] == alert_payload["location"]

    # 8. Other user attempts to modify or delete alert -> 403 Forbidden
    r_fail_edit = client.put(
        f"/api/alerts/{alert_id}",
        json={"title": "Hacker Mod Alert"},
        headers=headers_other,
    )
    assert r_fail_edit.status_code == 403

    r_fail_del = client.delete(f"/api/alerts/{alert_id}", headers=headers_other)
    assert r_fail_del.status_code == 403

    # 9. Author modifies alert (marks it resolved when municipality fixes it) -> 200
    r_ok_edit = client.put(
        f"/api/alerts/{alert_id}",
        json={"is_resolved": True},
        headers=headers_author,
    )
    assert r_ok_edit.status_code == 200
    assert r_ok_edit.json()["is_resolved"] is True

    # 10. Author deletes alert -> 204
    r_ok_del = client.delete(f"/api/alerts/{alert_id}", headers=headers_author)
    assert r_ok_del.status_code == 204

    # Deleted alert returns 404
    assert client.get(f"/api/alerts/{alert_id}").status_code == 404


def test_orders_and_history_lifecycle():
    """Users can order services and products, view client/provider history, and transition order states."""
    suffix = uuid.uuid4().hex[:6]
    dni_client = f"3{uuid.uuid4().int % 10000000:07d}"
    dni_seller = f"4{uuid.uuid4().int % 10000000:07d}"
    phone_client = f"+5197{uuid.uuid4().int % 10000000:07d}"
    phone_seller = f"+5198{uuid.uuid4().int % 10000000:07d}"

    # 1. Register Client (User A)
    client.post(
        "/api/auth/register",
        json={
            "username": f"cli_{suffix}",
            "email": f"cli_{suffix}@example.com",
            "password": "Password123!",
            "full_name": "Vecino Comprador",
            "dni": dni_client,
            "phone": phone_client,
        },
    )
    token_client = client.post(
        "/api/auth/login",
        data={"username": f"cli_{suffix}@example.com", "password": "Password123!"},
    ).json()["access_token"]
    headers_client = {"Authorization": f"Bearer {token_client}"}

    # 2. Register Provider/Seller (User B)
    client.post(
        "/api/auth/register",
        json={
            "username": f"prov_{suffix}",
            "email": f"prov_{suffix}@example.com",
            "password": "Password123!",
            "full_name": "Vecino Proveedor",
            "dni": dni_seller,
            "phone": phone_seller,
        },
    )
    token_seller = client.post(
        "/api/auth/login",
        data={"username": f"prov_{suffix}@example.com", "password": "Password123!"},
    ).json()["access_token"]
    headers_seller = {"Authorization": f"Bearer {token_seller}"}

    # 3. Provider publishes a service and a product
    r_srv = client.post(
        "/api/services/",
        json={
            "title": "Jardinería y poda",
            "description": "Mantenimiento integral de jardines y cercos vivos.",
            "price_per_hour": 25.0,
            "category": "jardineria",
        },
        headers=headers_seller,
    )
    assert r_srv.status_code == 201
    service_id = r_srv.json()["id"]

    r_prod = client.post(
        "/api/products/",
        json={
            "title": "Miel artesanal de abeja 1kg",
            "description": "Pura miel de flores silvestres del valle.",
            "price": 30.0,
            "stock": 5,
            "category": "alimentos",
        },
        headers=headers_seller,
    )
    assert r_prod.status_code == 201
    product_id = r_prod.json()["id"]

    # 4. Self-order rejected (Provider cannot buy their own offering) -> 400
    r_self_srv = client.post(
        "/api/orders/",
        json={"item_type": "service", "item_id": service_id, "quantity": 1},
        headers=headers_seller,
    )
    assert r_self_srv.status_code == 400
    assert "propio" in r_self_srv.json()["detail"].lower()

    # 5. Stock overflow rejected (Client orders more than available stock) -> 400
    r_overstock = client.post(
        "/api/orders/",
        json={"item_type": "product", "item_id": product_id, "quantity": 10},
        headers=headers_client,
    )
    assert r_overstock.status_code == 400
    assert "stock" in r_overstock.json()["detail"].lower()

    # 6. Client successfully requests service -> 201
    r_order_srv = client.post(
        "/api/orders/",
        json={
            "item_type": "service",
            "item_id": service_id,
            "quantity": 3,
            "notes": "Necesito poda urgente el domingo por la mañana",
        },
        headers=headers_client,
    )
    assert r_order_srv.status_code == 201
    srv_order_data = r_order_srv.json()
    order_srv_id = srv_order_data["id"]
    assert srv_order_data["unit_price"] == 25.0
    assert srv_order_data["total_price"] == 75.0
    assert srv_order_data["status"] == "pendiente"

    # 7. Client successfully orders product -> 201
    r_order_prod = client.post(
        "/api/orders/",
        json={
            "item_type": "product",
            "item_id": product_id,
            "quantity": 2,
            "notes": "Dejar con la vecina del 201 si no contesto",
        },
        headers=headers_client,
    )
    assert r_order_prod.status_code == 201
    prod_order_data = r_order_prod.json()
    order_prod_id = prod_order_data["id"]
    assert prod_order_data["unit_price"] == 30.0
    assert prod_order_data["total_price"] == 60.0
    assert prod_order_data["status"] == "pendiente"

    # 8. Check History: Client view (role=client)
    r_my_buys = client.get("/api/orders/my-orders?role=client", headers=headers_client)
    assert r_my_buys.status_code == 200
    client_orders = r_my_buys.json()
    assert client_orders["total"] >= 2
    assert any(o["id"] == order_srv_id for o in client_orders["items"])
    assert any(o["id"] == order_prod_id for o in client_orders["items"])

    # 9. Check History: Provider view (role=provider)
    r_my_jobs = client.get("/api/orders/my-orders?role=provider", headers=headers_seller)
    assert r_my_jobs.status_code == 200
    provider_orders = r_my_jobs.json()
    assert provider_orders["total"] >= 2
    assert any(o["id"] == order_srv_id for o in provider_orders["items"])
    assert any(o["id"] == order_prod_id for o in provider_orders["items"])

    # 10. Status updates by Provider:
    # Accept service order -> 200
    r_accept = client.patch(
        f"/api/orders/{order_srv_id}/status",
        json={"status": "aceptado"},
        headers=headers_seller,
    )
    assert r_accept.status_code == 200
    assert r_accept.json()["status"] == "aceptado"

    # Advance service to in_progress -> 200
    r_prog = client.patch(
        f"/api/orders/{order_srv_id}/status",
        json={"status": "en_progreso"},
        headers=headers_seller,
    )
    assert r_prog.status_code == 200
    assert r_prog.json()["status"] == "en_progreso"

    # Complete product order -> 200, checks that product stock decreased from 5 to 3
    r_comp_prod = client.patch(
        f"/api/orders/{order_prod_id}/status",
        json={"status": "completado"},
        headers=headers_seller,
    )
    assert r_comp_prod.status_code == 200
    assert r_comp_prod.json()["status"] == "completado"

    # Verify product stock decreased in catalog
    r_check_prod = client.get(f"/api/products/{product_id}")
    assert r_check_prod.status_code == 200
    assert r_check_prod.json()["stock"] == 3

    # Client cancels another pending order if created
    r_order_cancel = client.post(
        "/api/orders/",
        json={"item_type": "product", "item_id": product_id, "quantity": 1},
        headers=headers_client,
    )
    cancel_id = r_order_cancel.json()["id"]
    r_cancel_ok = client.patch(
        f"/api/orders/{cancel_id}/status",
        json={"status": "cancelado"},
        headers=headers_client,
    )
    assert r_cancel_ok.status_code == 200
    assert r_cancel_ok.json()["status"] == "cancelado"

