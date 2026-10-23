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
        bind=engine,
        autoflush=False,
        autocommit=False,
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


def create_user(db, email, role, password="TestPass@123"):
    user = User(
        full_name=f"Test {role.value.title()}",
        email=email,
        hashed_password=hash_password(password),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_test_db():
    override = app.dependency_overrides[get_db]
    return next(override())


def customer_token(client, email="customer@example.com"):
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
        json={
            "email": email,
            "password": "CustomerPass@123",
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_customer_can_create_profile(client):
    token = customer_token(client)
    response = client.post(
        "/customers/me",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "phone": "9876543210",
            "address": "Anna Nagar",
            "city": "Chennai",
        },
    )

    assert response.status_code == 201
    assert response.json()["city"] == "Chennai"
    assert response.json()["phone"] == "9876543210"


def test_customer_can_read_own_profile(client):
    token = customer_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/customers/me",
        headers=headers,
        json={"city": "Chennai"},
    )

    response = client.get("/customers/me", headers=headers)

    assert response.status_code == 200
    assert response.json()["city"] == "Chennai"


def test_customer_can_update_own_profile(client):
    token = customer_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/customers/me",
        headers=headers,
        json={"city": "Chennai"},
    )

    response = client.put(
        "/customers/me",
        headers=headers,
        json={"city": "Coimbatore"},
    )

    assert response.status_code == 200
    assert response.json()["city"] == "Coimbatore"


def test_customer_cannot_create_duplicate_profile(client):
    token = customer_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"city": "Chennai"}

    first = client.post("/customers/me", headers=headers, json=payload)
    second = client.post("/customers/me", headers=headers, json=payload)

    assert first.status_code == 201
    assert second.status_code == 409


def test_read_profile_before_creation_returns_404(client):
    token = customer_token(client)

    response = client.get(
        "/customers/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_update_profile_before_creation_returns_404(client):
    token = customer_token(client)

    response = client.put(
        "/customers/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"city": "Chennai"},
    )

    assert response.status_code == 404


def test_customer_cannot_list_all_customers(client):
    token = customer_token(client)

    response = client.get(
        "/customers",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_admin_can_search_and_paginate_customers(client):
    db = get_test_db()
    try:
        admin = create_user(db, "admin@example.com", UserRole.ADMIN)
        customer = create_user(
            db, "searchme@example.com", UserRole.CUSTOMER
        )
        from app.models.customer import Customer
        db.add(
            Customer(
                user_id=customer.id,
                city="Chennai",
                phone="9876543210",
            )
        )
        db.commit()
    finally:
        db.close()

    login_response = client.post(
        "/auth/login",
        json={
            "email": "admin@example.com",
            "password": "TestPass@123",
        },
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    response = client.get(
        "/customers?search=searchme&skip=0&limit=1",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["email"] == "searchme@example.com"


def test_admin_can_filter_customers_by_city(client):
    db = get_test_db()
    try:
        create_user(db, "admin@example.com", UserRole.ADMIN)
        customer = create_user(
            db, "citycustomer@example.com", UserRole.CUSTOMER
        )
        from app.models.customer import Customer
        db.add(Customer(user_id=customer.id, city="Chennai"))
        db.commit()
    finally:
        db.close()

    login_response = client.post(
        "/auth/login",
        json={
            "email": "admin@example.com",
            "password": "TestPass@123",
        },
    )
    token = login_response.json()["access_token"]

    response = client.get(
        "/customers?city=Chennai",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert any(
        item["email"] == "citycustomer@example.com"
        for item in response.json()
    )


def test_admin_can_deactivate_customer(client):
    db = get_test_db()
    try:
        create_user(db, "admin@example.com", UserRole.ADMIN)
        customer = create_user(
            db, "disableme@example.com", UserRole.CUSTOMER
        )
        customer_id = customer.id
        from app.models.customer import Customer
        db.add(Customer(user_id=customer.id, city="Chennai"))
        db.commit()
    finally:
        db.close()

    login_response = client.post(
        "/auth/login",
        json={
            "email": "admin@example.com",
            "password": "TestPass@123",
        },
    )
    token = login_response.json()["access_token"]

    response = client.patch(
        f"/customers/{customer_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_active": False},
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_customer_cannot_deactivate_another_account(client):
    token = customer_token(client)

    response = client.patch(
        "/customers/999/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_active": False},
    )

    assert response.status_code == 403
