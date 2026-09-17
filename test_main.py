import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch
from sqlalchemy.orm.exc import StaleDataError
import os

from main import app
import database
from database import Base, get_db, get_db_session
from models import User, Reservation

# In-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override engine & SessionLocal for testing
database.SessionLocal = TestingSessionLocal
database.engine = engine

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Bienvenido a la API de Reservas IRTRA en Render"}
    assert "X-Process-Time" in response.headers

def test_register_user():
    response = client.post(
        "/users/register",
        json={"carne": "12345", "dpi": "1234567890123", "full_name": "Test User", "password": "password123", "role": "cliente"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["carne"] == "12345"
    assert data["full_name"] == "Test User"
    assert data["role"] == "cliente"

def test_register_admin():
    response = client.post(
        "/users/register",
        json={"carne": "ADM01", "dpi": "9876543210123", "full_name": "Admin User", "password": "adminpassword", "role": "administrador"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["carne"] == "ADM01"
    assert data["role"] == "administrador"

def test_register_duplicate_carne():
    client.post(
        "/users/register",
        json={"carne": "12345", "dpi": "1234567890123", "full_name": "Test User", "password": "password123"}
    )
    response = client.post(
        "/users/register",
        json={"carne": "12345", "dpi": "9999999999999", "full_name": "Test User 2", "password": "password123"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Carné ya registrado"

def test_register_duplicate_dpi():
    client.post(
        "/users/register",
        json={"carne": "12345", "dpi": "1234567890123", "full_name": "Test User", "password": "password123"}
    )
    response = client.post(
        "/users/register",
        json={"carne": "67890", "dpi": "1234567890123", "full_name": "Test User 2", "password": "password123"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "DPI ya registrado"

def test_login_success():
    client.post(
        "/users/register",
        json={"carne": "12345", "dpi": "1234567890123", "full_name": "Test User", "password": "password123", "role": "cliente"}
    )
    response = client.post(
        "/users/login",
        data={"username": "12345", "password": "password123"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"
    assert response.json()["role"] == "cliente"

def test_login_failure():
    response = client.post(
        "/users/login",
        data={"username": "12345", "password": "wrongpassword"}
    )
    assert response.status_code == 401

def test_get_current_user():
    client.post(
        "/users/register",
        json={"carne": "12345", "dpi": "1234567890123", "full_name": "Test User", "password": "password123"}
    )
    login_response = client.post(
        "/users/login",
        data={"username": "12345", "password": "password123"}
    )
    token = login_response.json()["access_token"]
    
    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["carne"] == "12345"

def test_get_current_user_invalid_token():
    response = client.get(
        "/users/me",
        headers={"Authorization": "Bearer invalidtoken"}
    )
    assert response.status_code == 401

def test_create_reservation_xetulul_brazalete():
    client.post(
        "/users/register",
        json={"carne": "12345", "dpi": "1234567890123", "full_name": "Test User", "password": "password123"}
    )
    login_response = client.post(
        "/users/login",
        data={"username": "12345", "password": "password123"}
    )
    token = login_response.json()["access_token"]
    
    response = client.post(
        "/reservations/",
        json={
            "park_name": "Xetulul", 
            "ticket_type": "Brazalete Juegos Ilimitados",
            "visit_date": "2026-10-10", 
            "beneficiaries_count": 3
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["park_name"] == "Xetulul"
    assert data["ticket_type"] == "Brazalete Juegos Ilimitados"
    assert data["status"] == "PENDIENTE"
    assert "reservation_code" in data

def test_create_reservation_xocomil_combo_xetulha():
    client.post(
        "/users/register",
        json={"carne": "12345", "dpi": "1234567890123", "full_name": "Test User", "password": "password123"}
    )
    login_response = client.post(
        "/users/login",
        data={"username": "12345", "password": "password123"}
    )
    token = login_response.json()["access_token"]
    
    response = client.post(
        "/reservations/",
        json={
            "park_name": "Xocomil y Xetulha", 
            "ticket_type": "Entrada Combo Xocomil y Xetulha",
            "visit_date": "2026-10-10", 
            "beneficiaries_count": 2
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["park_name"] == "Xocomil y Xetulha"
    assert data["ticket_type"] == "Entrada Combo Xocomil y Xetulha"

def test_create_reservation_too_many_beneficiaries():
    client.post(
        "/users/register",
        json={"carne": "12345", "dpi": "1234567890123", "full_name": "Test User", "password": "password123"}
    )
    login_response = client.post(
        "/users/login",
        data={"username": "12345", "password": "password123"}
    )
    token = login_response.json()["access_token"]
    
    response = client.post(
        "/reservations/",
        json={"park_name": "Xetulul", "visit_date": "2026-10-10", "beneficiaries_count": 6},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400

def test_get_user_reservations():
    client.post(
        "/users/register",
        json={"carne": "12345", "dpi": "1234567890123", "full_name": "Test User", "password": "password123"}
    )
    login_response = client.post(
        "/users/login",
        data={"username": "12345", "password": "password123"}
    )
    token = login_response.json()["access_token"]
    
    client.post(
        "/reservations/",
        json={"park_name": "Xetulul", "ticket_type": "Entrada General", "visit_date": "2026-10-10", "beneficiaries_count": 3},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    response = client.get(
        "/reservations/",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["park_name"] == "Xetulul"

def test_rbac_client_cannot_access_admin_all():
    client.post(
        "/users/register",
        json={"carne": "12345", "dpi": "1234567890123", "full_name": "Test User", "password": "password123", "role": "cliente"}
    )
    login_res = client.post("/users/login", data={"username": "12345", "password": "password123"})
    token = login_res.json()["access_token"]

    response = client.get("/reservations/admin/all", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403

def test_admin_delivery_flow():
    # 1. Register Client & make reservation
    client.post(
        "/users/register",
        json={"carne": "CLI01", "dpi": "1000000000001", "full_name": "Cliente Uno", "password": "clipassword", "role": "cliente"}
    )
    cli_login = client.post("/users/login", data={"username": "CLI01", "password": "clipassword"})
    cli_token = cli_login.json()["access_token"]
    
    res_response = client.post(
        "/reservations/",
        json={"park_name": "Xetulul", "ticket_type": "Brazalete Juegos Ilimitados", "visit_date": "2026-11-01", "beneficiaries_count": 4},
        headers={"Authorization": f"Bearer {cli_token}"}
    )
    reservation_id = res_response.json()["id"]

    # 2. Register Admin
    client.post(
        "/users/register",
        json={"carne": "ADM01", "dpi": "2000000000002", "full_name": "Admin Taquilla", "password": "admpassword", "role": "administrador"}
    )
    adm_login = client.post("/users/login", data={"username": "ADM01", "password": "admpassword"})
    adm_token = adm_login.json()["access_token"]

    # 3. Admin queries all reservations
    list_res = client.get("/reservations/admin/all", headers={"Authorization": f"Bearer {adm_token}"})
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1
    assert list_res.json()[0]["status"] == "PENDIENTE"

    # 4. Admin delivers reservation
    deliver_res = client.put(
        f"/reservations/{reservation_id}/deliver",
        json={"status": "ENTREGADO"},
        headers={"Authorization": f"Bearer {adm_token}"}
    )
    assert deliver_res.status_code == 200
    assert deliver_res.json()["status"] == "ENTREGADO"
    assert deliver_res.json()["delivered_at"] is not None

    # 5. Redundant delivery attempt fails
    redundant_res = client.put(
        f"/reservations/{reservation_id}/deliver",
        json={"status": "ENTREGADO"},
        headers={"Authorization": f"Bearer {adm_token}"}
    )
    assert redundant_res.status_code == 400

def test_database_session_lifecycle():
    with get_db_session(TestingSessionLocal) as db:
        users = db.query(User).all()
        assert isinstance(users, list)

def test_concurrency_stale_data_middleware_handling():
    # Simulate optimistic concurrency collision (StaleDataError)
    with patch("crud.deliver_reservation", side_effect=StaleDataError(None, "Row was updated")):
        # Register Admin
        client.post(
            "/users/register",
            json={"carne": "ADM99", "dpi": "9900000000002", "full_name": "Admin Conc", "password": "admpassword", "role": "administrador"}
        )
        adm_login = client.post("/users/login", data={"username": "ADM99", "password": "admpassword"})
        adm_token = adm_login.json()["access_token"]

        response = client.put(
            "/reservations/999/deliver",
            json={"status": "ENTREGADO"},
            headers={"Authorization": f"Bearer {adm_token}"}
        )
        assert response.status_code == 409
        assert "Conflicto de concurrencia" in response.json()["detail"]
