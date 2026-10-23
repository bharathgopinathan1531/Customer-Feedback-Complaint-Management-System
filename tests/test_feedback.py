import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.session import Base, get_db


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


def register_customer(client, email):
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

    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/customers/me",
        json={"phone": "9876543210", "city": "Chennai"},
        headers=headers,
    )
    assert response.status_code == 201

    return headers


def register_staff(client, email, role):
    from app.core.security import hash_password
    from app.db.session import SessionLocal
    from app.models.user import User, UserRole

    # Use the test database supplied by the active dependency override.
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


def create_feedback(client, headers, rating=5):
    return client.post(
        "/feedback",
        json={
            "category": "Service",
            "rating": rating,
            "description": "The service was helpful and professional.",
        },
        headers=headers,
    )


def test_customer_can_submit_feedback(client):
    headers = register_customer(client, "feedback1@example.com")
    response = create_feedback(client, headers)

    assert response.status_code == 201
    assert response.json()["rating"] == 5
    assert response.json()["category"] == "Service"
    assert response.json()["status"] == "submitted"


def test_feedback_rejects_rating_above_five(client):
    headers = register_customer(client, "feedback2@example.com")
    response = create_feedback(client, headers, rating=6)

    assert response.status_code == 422


def test_feedback_rejects_rating_below_one(client):
    headers = register_customer(client, "feedback3@example.com")
    response = create_feedback(client, headers, rating=0)

    assert response.status_code == 422


def test_customer_can_list_own_feedback(client):
    headers = register_customer(client, "feedback4@example.com")
    create_feedback(client, headers, rating=4)

    response = client.get("/feedback/me", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["rating"] == 4


def test_customer_can_update_submitted_feedback(client):
    headers = register_customer(client, "feedback5@example.com")
    created = create_feedback(client, headers).json()

    response = client.put(
        f"/feedback/{created['id']}",
        json={"rating": 3, "description": "Updated feedback description."},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["rating"] == 3
    assert response.json()["description"] == "Updated feedback description."


def test_customer_cannot_read_another_customers_feedback(client):
    first_headers = register_customer(client, "feedback6@example.com")
    second_headers = register_customer(client, "feedback7@example.com")

    created = create_feedback(client, first_headers).json()

    response = client.get(
        f"/feedback/{created['id']}",
        headers=second_headers,
    )

    assert response.status_code == 403


def test_customer_cannot_update_another_customers_feedback(client):
    first_headers = register_customer(client, "feedback8@example.com")
    second_headers = register_customer(client, "feedback9@example.com")

    created = create_feedback(client, first_headers).json()

    response = client.put(
        f"/feedback/{created['id']}",
        json={"rating": 2},
        headers=second_headers,
    )

    assert response.status_code == 403


def test_customer_cannot_list_all_feedback(client):
    headers = register_customer(client, "feedback10@example.com")

    response = client.get("/feedback", headers=headers)

    assert response.status_code == 403


def test_staff_can_list_feedback(client):
    customer_headers = register_customer(client, "feedback11@example.com")
    create_feedback(client, customer_headers)

    staff_headers = register_staff(client, "agent@example.com", "agent")
    response = client.get("/feedback", headers=staff_headers)

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_feedback_status_can_be_updated_by_staff(client):
    customer_headers = register_customer(client, "feedback12@example.com")
    created = create_feedback(client, customer_headers).json()

    staff_headers = register_staff(client, "manager@example.com", "manager")
    response = client.patch(
        f"/feedback/{created['id']}/status",
        json={"status": "under_review"},
        headers=staff_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "under_review"


def test_feedback_requires_authentication(client):
    response = client.post(
        "/feedback",
        json={
            "category": "Service",
            "rating": 5,
            "description": "A useful feedback description.",
        },
    )

    assert response.status_code in (401, 403)
