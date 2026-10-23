import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import Base, get_db
from app.core.security import hash_password
from app.models.user import User, UserRole


@pytest.fixture
def client():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )

    Base.metadata.create_all(bind=test_engine)

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
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def create_admin():
    return User(
        full_name="Test Admin",
        email="admin@example.com",
        hashed_password=hash_password("AdminPass@123"),
        role=UserRole.ADMIN,
        is_active=True,
    )


def register_customer(client, email="customer@example.com"):
    return client.post(
        "/auth/register",
        json={
            "full_name": "Test Customer",
            "email": email,
            "password": "CustomerPass@123",
        },
    )


def login(client, email, password):
    return client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_register_customer(client):
    response = register_customer(client)

    assert response.status_code == 201
    assert response.json()["email"] == "customer@example.com"
    assert response.json()["role"] == "customer"
    assert "hashed_password" not in response.json()


def test_duplicate_email_rejected(client):
    register_customer(client)
    response = register_customer(client)

    assert response.status_code == 409


def test_short_password_rejected(client):
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Test Customer",
            "email": "short@example.com",
            "password": "123",
        },
    )

    assert response.status_code == 422


def test_login_returns_access_token(client):
    register_customer(client)

    response = login(
        client,
        "customer@example.com",
        "CustomerPass@123",
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_wrong_password_rejected(client):
    register_customer(client)

    response = login(
        client,
        "customer@example.com",
        "WrongPassword@123",
    )

    assert response.status_code == 401


def test_current_user_requires_token(client):
    response = client.get("/auth/me")
    assert response.status_code == 401

def test_current_user_with_valid_token(client):
    register_customer(client)
    token_response = login(
        client,
        "customer@example.com",
        "CustomerPass@123",
    )
    token = token_response.json()["access_token"]

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "customer@example.com"


def test_customer_cannot_access_admin_users(client):
    register_customer(client)
    token_response = login(
        client,
        "customer@example.com",
        "CustomerPass@123",
    )
    token = token_response.json()["access_token"]

    response = client.get(
        "/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_admin_can_list_users(client):
    from app.db.session import SessionLocal

    # Seed the admin in the isolated test database through the overridden
    # database dependency's session factory.
    db_dependency = app.dependency_overrides[get_db]
    db = next(db_dependency())
    try:
        db.add(create_admin())
        db.commit()
    finally:
        db.close()

    # The test client uses the isolated database for authentication.
    response = login(
        client,
        "admin@example.com",
        "AdminPass@123",
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    response = client.get(
        "/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert any(user["email"] == "admin@example.com" for user in response.json())


def test_deactivated_user_cannot_login(client):
    from app.db.session import SessionLocal

    db_dependency = app.dependency_overrides[get_db]
    db = next(db_dependency())
    try:
        db.add(
            User(
                full_name="Inactive User",
                email="inactive@example.com",
                hashed_password=hash_password("InactivePass@123"),
                role=UserRole.CUSTOMER,
                is_active=False,
            )
        )
        db.commit()
    finally:
        db.close()

    response = login(
        client,
        "inactive@example.com",
        "InactivePass@123",
    )

    assert response.status_code == 403

def register_and_login(client, email="refresh@example.com"):
    register_response = client.post(
        "/auth/register",
        json={
            "full_name": "Refresh Customer",
            "email": email,
            "password": "CustomerPass@123",
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "CustomerPass@123",
        },
    )
    assert login_response.status_code == 200
    return login_response.json()


def test_login_returns_refresh_token(client):
    tokens = register_and_login(client)

    assert tokens["access_token"]
    assert tokens["refresh_token"]
    assert tokens["token_type"] == "bearer"


def test_refresh_rotates_refresh_token(client):
    tokens = register_and_login(client)

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )

    assert response.status_code == 200
    new_tokens = response.json()
    assert new_tokens["access_token"]
    assert new_tokens["refresh_token"] != tokens["refresh_token"]


def test_old_refresh_token_rejected_after_rotation(client):
    tokens = register_and_login(client)

    first_refresh = client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert first_refresh.status_code == 200

    reuse_response = client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert reuse_response.status_code == 401


def test_logout_revokes_refresh_token(client):
    tokens = register_and_login(client)

    response = client.post(
        "/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert response.status_code == 200

    refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh_response.status_code == 401


def test_invalid_refresh_token_rejected(client):
    response = client.post(
        "/auth/refresh",
        json={"refresh_token": "invalid-refresh-token-value-123456"},
    )
    assert response.status_code == 401


def test_invalid_logout_token_rejected(client):
    response = client.post(
        "/auth/logout",
        json={"refresh_token": "invalid-refresh-token-value-123456"},
    )
    assert response.status_code == 401



def test_password_reset_changes_password(client):
    register_customer(client, "reset@example.com")

    request_response = client.post(
        "/auth/password-reset/request",
        json={"email": "reset@example.com"},
    )
    assert request_response.status_code == 200

    reset_token = request_response.json().get("reset_token")
    assert reset_token

    confirm_response = client.post(
        "/auth/password-reset/confirm",
        json={
            "token": reset_token,
            "new_password": "NewCustomerPass@123",
        },
    )
    assert confirm_response.status_code == 200

    old_login = login(
        client, "reset@example.com", "CustomerPass@123"
    )
    assert old_login.status_code == 401

    new_login = login(
        client, "reset@example.com", "NewCustomerPass@123"
    )
    assert new_login.status_code == 200


def test_password_reset_token_cannot_be_reused(client):
    register_customer(client, "reuse-reset@example.com")

    request_response = client.post(
        "/auth/password-reset/request",
        json={"email": "reuse-reset@example.com"},
    )
    token = request_response.json().get("reset_token")
    assert token

    payload = {
        "token": token,
        "new_password": "NewCustomerPass@123",
    }

    first_response = client.post(
        "/auth/password-reset/confirm", json=payload
    )
    assert first_response.status_code == 200

    second_response = client.post(
        "/auth/password-reset/confirm", json=payload
    )
    assert second_response.status_code == 400


def test_password_reset_unknown_email_does_not_reveal_account(client):
    response = client.post(
        "/auth/password-reset/request",
        json={"email": "not-registered@example.com"},
    )

    assert response.status_code == 200
    assert "reset_token" not in response.json()
