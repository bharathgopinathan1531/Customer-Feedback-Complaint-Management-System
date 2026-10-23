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

    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    response = client.post(
        "/customers/me",
        json={"phone": "9876543210", "city": "Chennai"},
        headers=headers,
    )
    assert response.status_code == 201
    return headers


def register_staff(client, email, role):
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        db.add(
            User(
                full_name=f"Test {role.title()}",
                email=email,
                hashed_password=hash_password("StaffPass@123"),
                role=UserRole(role),
                is_active=True,
            )
        )
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


def create_category(client, headers, name="Billing"):
    return client.post(
        "/categories",
        json={"name": name, "description": "Billing related issues"},
        headers=headers,
    )


def create_complaint(client, headers, category_id, subject="Payment issue"):
    return client.post(
        "/complaints",
        json={
            "category_id": category_id,
            "subject": subject,
            "description": "I need help resolving this billing problem.",
            "priority": "high",
        },
        headers=headers,
    )


def setup_customer_and_category(client, email):
    customer_headers = register_customer(client, email)
    admin_headers = register_staff(client, f"admin-{email}", "admin")
    category_response = create_category(client, admin_headers)
    assert category_response.status_code == 201
    return customer_headers, category_response.json()["id"], admin_headers


def test_customer_can_create_complaint(client):
    headers, category_id, _ = setup_customer_and_category(
        client, "complaint1@example.com"
    )
    response = create_complaint(client, headers, category_id)

    assert response.status_code == 201
    assert response.json()["subject"] == "Payment issue"
    assert response.json()["priority"] == "high"
    assert response.json()["status"] == "open"


def test_complaint_requires_authentication(client):
    response = client.post(
        "/complaints",
        json={
            "category_id": 1,
            "subject": "Payment issue",
            "description": "Please resolve this billing problem.",
        },
    )
    assert response.status_code in (401, 403)


def test_complaint_rejects_invalid_category(client):
    headers = register_customer(client, "complaint2@example.com")
    response = create_complaint(client, headers, 9999)

    assert response.status_code == 404


def test_complaint_rejects_short_subject(client):
    headers, category_id, _ = setup_customer_and_category(
        client, "complaint3@example.com"
    )
    response = create_complaint(client, headers, category_id, subject="No")

    assert response.status_code == 422


def test_customer_can_list_own_complaints(client):
    headers, category_id, _ = setup_customer_and_category(
        client, "complaint4@example.com"
    )
    create_complaint(client, headers, category_id)

    response = client.get("/complaints/me", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_customer_cannot_list_all_complaints(client):
    headers = register_customer(client, "complaint5@example.com")
    response = client.get("/complaints", headers=headers)

    assert response.status_code == 403


def test_customer_cannot_read_another_customers_complaint(client):
    first_headers, category_id, _ = setup_customer_and_category(
        client, "complaint6@example.com"
    )
    second_headers = register_customer(client, "complaint7@example.com")
    created = create_complaint(client, first_headers, category_id).json()

    response = client.get(
        f"/complaints/{created['id']}", headers=second_headers
    )

    assert response.status_code == 403


def test_staff_can_list_complaints(client):
    customer_headers, category_id, _ = setup_customer_and_category(
        client, "complaint8@example.com"
    )
    create_complaint(client, customer_headers, category_id)

    agent_headers = register_staff(client, "complaint-agent@example.com", "agent")
    response = client.get("/complaints", headers=agent_headers)

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_staff_can_update_complaint_status(client):
    customer_headers, category_id, _ = setup_customer_and_category(
        client, "complaint9@example.com"
    )
    created = create_complaint(
        client, customer_headers, category_id
    ).json()

    manager_headers = register_staff(
        client, "complaint-manager@example.com", "manager"
    )
    response = client.patch(
        f"/complaints/{created['id']}/status",
        json={"status": "in_progress"},
        headers=manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


def test_customer_can_update_own_open_complaint(client):
    headers, category_id, _ = setup_customer_and_category(
        client, "complaint10@example.com"
    )
    created = create_complaint(client, headers, category_id).json()

    response = client.put(
        f"/complaints/{created['id']}",
        json={"subject": "Updated payment issue"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["subject"] == "Updated payment issue"


def test_customer_cannot_update_another_customers_complaint(client):
    first_headers, category_id, _ = setup_customer_and_category(
        client, "complaint11@example.com"
    )
    second_headers = register_customer(client, "complaint12@example.com")
    created = create_complaint(client, first_headers, category_id).json()

    response = client.put(
        f"/complaints/{created['id']}",
        json={"subject": "Unauthorized update"},
        headers=second_headers,
    )

    assert response.status_code == 403


def test_staff_can_filter_complaints_by_priority(client):
    customer_headers, category_id, _ = setup_customer_and_category(
        client, "complaint13@example.com"
    )
    create_complaint(client, customer_headers, category_id)

    agent_headers = register_staff(client, "complaint-filter-agent@example.com", "agent")
    response = client.get(
        "/complaints?priority=high", headers=agent_headers
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["priority"] == "high"

def test_admin_can_assign_complaint_to_agent(client):
    customer_headers, category_id, admin_headers = setup_customer_and_category(
        client, "assign-success@example.com"
    )
    created = create_complaint(
        client, customer_headers, category_id
    ).json()
    agent_headers = register_staff(client, "assign-agent@example.com", "agent")

    from app.core.security import decode_access_token
    from app.models.user import User

    # Get the agent's ID from the authenticated token.
    token = agent_headers["Authorization"].split(" ", 1)[1]
    token_data = decode_access_token(token)
    agent_id = int(token_data["sub"])

    response = client.patch(
        f"/complaints/{created['id']}/assign",
        json={"assigned_to_user_id": agent_id},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["assigned_to_user_id"] == agent_id


def test_manager_can_assign_complaint_to_manager(client):
    customer_headers, category_id, _ = setup_customer_and_category(
        client, "assign-manager-customer@example.com"
    )
    created = create_complaint(
        client, customer_headers, category_id
    ).json()
    manager_headers = register_staff(
        client, "assign-manager@example.com", "manager"
    )
    token = manager_headers["Authorization"].split(" ", 1)[1]

    from app.core.security import decode_access_token

    manager_id = int(decode_access_token(token)["sub"])
    admin_headers = register_staff(
        client, "assign-manager-admin@example.com", "admin"
    )

    response = client.patch(
        f"/complaints/{created['id']}/assign",
        json={"assigned_to_user_id": manager_id},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["assigned_to_user_id"] == manager_id


def test_assignment_rejects_customer_as_assignee(client):
    customer_headers, category_id, admin_headers = setup_customer_and_category(
        client, "assign-customer@example.com"
    )
    created = create_complaint(
        client, customer_headers, category_id
    ).json()
    token = customer_headers["Authorization"].split(" ", 1)[1]

    from app.core.security import decode_access_token

    customer_id = int(decode_access_token(token)["sub"])

    response = client.patch(
        f"/complaints/{created['id']}/assign",
        json={"assigned_to_user_id": customer_id},
        headers=admin_headers,
    )

    assert response.status_code == 400


def test_assignment_rejects_nonexistent_complaint(client):
    admin_headers = register_staff(
        client, "assign-missing-admin@example.com", "admin"
    )
    agent_headers = register_staff(
        client, "assign-missing-agent@example.com", "agent"
    )
    token = agent_headers["Authorization"].split(" ", 1)[1]

    from app.core.security import decode_access_token

    agent_id = int(decode_access_token(token)["sub"])

    response = client.patch(
        "/complaints/99999/assign",
        json={"assigned_to_user_id": agent_id},
        headers=admin_headers,
    )

    assert response.status_code == 404


def test_agent_cannot_assign_complaint(client):
    customer_headers, category_id, _ = setup_customer_and_category(
        client, "assign-forbidden@example.com"
    )
    created = create_complaint(
        client, customer_headers, category_id
    ).json()
    agent_headers = register_staff(
        client, "assign-forbidden-agent@example.com", "agent"
    )
    another_agent_headers = register_staff(
        client, "assign-forbidden-target@example.com", "agent"
    )
    token = another_agent_headers["Authorization"].split(" ", 1)[1]

    from app.core.security import decode_access_token

    agent_id = int(decode_access_token(token)["sub"])

    response = client.patch(
        f"/complaints/{created['id']}/assign",
        json={"assigned_to_user_id": agent_id},
        headers=agent_headers,
    )

    assert response.status_code == 403
