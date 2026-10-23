import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.session import Base, get_db
from app.core.security import hash_password
from app.models.user import User, UserRole


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def register_customer(client, email="customer_category@test.com"):
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Test Customer",
            "email": email,
            "password": "CustomerPass@123",
        },
    )
    assert response.status_code == 201

    response = client.post(
        "/auth/login",
        json={"email": email, "password": "CustomerPass@123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def register_staff(client, email, role):
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        user = User(
            full_name=f"Test {role.title()}",
            email=email,
            hashed_password=hash_password("StaffPass@123"),
            role=UserRole(role),
            is_active=True,
        )
        db.add(user)
        db.commit()
    finally:
        db.close()
        db_generator.close()

    response = client.post(
        "/auth/login",
        json={"email": email, "password": "StaffPass@123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_admin_can_create_category(client):
    headers = register_staff(client, "admin_category@test.com", "admin")
    response = client.post(
        "/categories/",
        headers=headers,
        json={"name": "Billing", "description": "Billing-related feedback"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Billing"
    assert response.json()["is_active"] is True


def test_manager_can_create_category(client):
    headers = register_staff(client, "manager_category@test.com", "manager")
    response = client.post(
        "/categories/",
        headers=headers,
        json={"name": "Delivery", "description": "Delivery feedback"},
    )
    assert response.status_code == 201


def test_customer_cannot_create_category(client):
    headers = register_customer(client)
    response = client.post(
        "/categories/",
        headers=headers,
        json={"name": "Billing"},
    )
    assert response.status_code == 403


def test_duplicate_category_name_is_rejected_case_insensitively(client):
    headers = register_staff(client, "admin_duplicate@test.com", "admin")
    first = client.post(
        "/categories/",
        headers=headers,
        json={"name": "Billing"},
    )
    assert first.status_code == 201

    second = client.post(
        "/categories/",
        headers=headers,
        json={"name": "billing"},
    )
    assert second.status_code == 409


def test_category_list_requires_authentication(client):
    response = client.get("/categories/")
    assert response.status_code in (401, 403)


def test_customer_can_list_active_categories(client):
    admin_headers = register_staff(client, "admin_list@test.com", "admin")
    client.post(
        "/categories/",
        headers=admin_headers,
        json={"name": "Billing"},
    )

    customer_headers = register_customer(client)
    response = client.get("/categories/", headers=customer_headers)

    assert response.status_code == 200
    assert any(item["name"] == "Billing" for item in response.json())


def test_inactive_category_is_hidden_from_customers(client):
    admin_headers = register_staff(client, "admin_inactive@test.com", "admin")
    created = client.post(
        "/categories/",
        headers=admin_headers,
        json={"name": "Archived"},
    )
    assert created.status_code == 201
    category_id = created.json()["id"]

    changed = client.patch(
        f"/categories/{category_id}/status",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert changed.status_code == 200

    customer_headers = register_customer(client)
    response = client.get("/categories/", headers=customer_headers)
    assert response.status_code == 200
    assert all(item["id"] != category_id for item in response.json())


def test_staff_can_request_inactive_categories(client):
    admin_headers = register_staff(client, "admin_stafflist@test.com", "admin")
    created = client.post(
        "/categories/",
        headers=admin_headers,
        json={"name": "Archived"},
    )
    category_id = created.json()["id"]

    client.patch(
        f"/categories/{category_id}/status",
        headers=admin_headers,
        json={"is_active": False},
    )

    response = client.get(
        "/categories/?active_only=false",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert any(item["id"] == category_id for item in response.json())


def test_manager_can_update_category(client):
    headers = register_staff(client, "manager_update@test.com", "manager")
    created = client.post(
        "/categories/",
        headers=headers,
        json={"name": "Old Name"},
    )
    assert created.status_code == 201

    response = client.patch(
        f"/categories/{created.json()['id']}",
        headers=headers,
        json={"name": "New Name", "description": "Updated description"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    assert response.json()["description"] == "Updated description"


def test_renaming_to_existing_category_returns_conflict(client):
    headers = register_staff(client, "admin_rename@test.com", "admin")
    first = client.post(
        "/categories/",
        headers=headers,
        json={"name": "Billing"},
    )
    second = client.post(
        "/categories/",
        headers=headers,
        json={"name": "Delivery"},
    )
    assert first.status_code == 201
    assert second.status_code == 201

    response = client.patch(
        f"/categories/{second.json()['id']}",
        headers=headers,
        json={"name": "billing"},
    )
    assert response.status_code == 409


def test_admin_can_soft_delete_category(client):
    headers = register_staff(client, "admin_delete@test.com", "admin")
    created = client.post(
        "/categories/",
        headers=headers,
        json={"name": "To Delete"},
    )
    assert created.status_code == 201

    response = client.delete(
        f"/categories/{created.json()['id']}",
        headers=headers,
    )
    assert response.status_code == 204


def test_customer_cannot_update_category(client):
    admin_headers = register_staff(client, "admin_protect@test.com", "admin")
    created = client.post(
        "/categories/",
        headers=admin_headers,
        json={"name": "Protected"},
    )
    customer_headers = register_customer(client)

    response = client.patch(
        f"/categories/{created.json()['id']}",
        headers=customer_headers,
        json={"name": "Changed"},
    )
    assert response.status_code == 403


def test_category_search(client):
    headers = register_staff(client, "admin_search@test.com", "admin")
    client.post("/categories/", headers=headers, json={"name": "Billing"})
    client.post("/categories/", headers=headers, json={"name": "Delivery"})

    response = client.get(
        "/categories/?search=bill",
        headers=headers,
    )
    assert response.status_code == 200
    assert any(item["name"] == "Billing" for item in response.json())
    assert all("bill" in item["name"].lower() for item in response.json())


def test_category_validation_rejects_short_name(client):
    headers = register_staff(client, "admin_validation@test.com", "admin")
    response = client.post(
        "/categories/",
        headers=headers,
        json={"name": " "},
    )
    assert response.status_code == 422
