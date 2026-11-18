
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from bson import ObjectId
from flask import Flask, jsonify
from flask_jwt_extended import JWTManager, create_access_token

# Allow imports from the backend folder.
BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from admin import admin_bp
from security import enforce_approved_account


# ==========================================
# TEST USERS
# ==========================================

ADMIN_ID = ObjectId()
PENDING_ID = ObjectId()
REJECTED_ID = ObjectId()
APPROVED_ID = ObjectId()
HR_USER_ID = ObjectId()

USERS = [
    {
        "_id": ADMIN_ID,
        "username": "itadmin",
        "email": "itadmin@example.com",
        "division": "IT",
        "role": "admin",
        "approval_status": "approved"
    },
    {
        "_id": PENDING_ID,
        "username": "pendinguser",
        "email": "pending@example.com",
        "division": "IT",
        "role": "user",
        "approval_status": "pending"
    },
    {
        "_id": REJECTED_ID,
        "username": "rejecteduser",
        "email": "rejected@example.com",
        "division": "IT",
        "role": "user",
        "approval_status": "rejected"
    },
    {
        "_id": APPROVED_ID,
        "username": "approveduser",
        "email": "approved@example.com",
        "division": "IT",
        "role": "user",
        "approval_status": "approved"
    },
    {
        "_id": HR_USER_ID,
        "username": "hruser",
        "email": "hr@example.com",
        "division": "HR",
        "role": "user",
        "approval_status": "pending"
    }
]


# ==========================================
# TEST DATABASE
# ==========================================

class FakeUsersCollection:
    def __init__(self):
        self.users = [user.copy() for user in USERS]

    def find_one(self, query):
        for user in self.users:
            if all(user.get(k) == v for k, v in query.items()):
                return user
        return None

    def find(self, query):
        return [
            user for user in self.users
            if all(user.get(k) == v for k, v in query.items())
        ]

    def update_one(self, query, update):
        for user in self.users:
            if all(user.get(k) == v for k, v in query.items()):
                user.update(update.get("$set", {}))
                return SimpleNamespace(modified_count=1)
        return SimpleNamespace(modified_count=0)


# ==========================================
# TEST APPLICATION
# ==========================================

@pytest.fixture
def app():
    application = Flask(__name__)

    application.config["TESTING"] = True
    application.config["JWT_SECRET_KEY"] = (
        "triad-ai-dms-admin-security-test-secret-2026"
    )

    JWTManager(application)

    application.db = SimpleNamespace(
        users=FakeUsersCollection()
    )

    application.register_blueprint(
        admin_bp,
        url_prefix="/api/admin"
    )

    @application.before_request
    def check_approval():
        return enforce_approved_account()

    @application.route("/api/protected")
    def protected():
        return jsonify({"message": "Access granted"}), 200

    return application


@pytest.fixture
def client(app):
    return app.test_client()


def auth_headers(app, user_id):
    with app.app_context():
        token = create_access_token(identity=str(user_id))

    return {"Authorization": f"Bearer {token}"}


# ==========================================
# TEST 1: PENDING USER BLOCKED
# ==========================================

def test_pending_user_cannot_access_api(app, client):
    response = client.get(
        "/api/protected",
        headers=auth_headers(app, PENDING_ID)
    )

    assert response.status_code == 403


# ==========================================
# TEST 2: REJECTED USER BLOCKED
# ==========================================

def test_rejected_user_cannot_access_api(app, client):
    response = client.get(
        "/api/protected",
        headers=auth_headers(app, REJECTED_ID)
    )

    assert response.status_code == 403


# ==========================================
# TEST 3: APPROVED USER ALLOWED
# ==========================================

def test_approved_user_can_access_api(app, client):
    response = client.get(
        "/api/protected",
        headers=auth_headers(app, APPROVED_ID)
    )

    assert response.status_code == 200


# ==========================================
# TEST 4: OLD TOKEN BLOCKED AFTER REJECTION
# ==========================================

def test_old_token_blocked_after_rejection(app, client):
    headers = auth_headers(app, APPROVED_ID)

    # Token was issued while the user was approved.
    first_response = client.get(
        "/api/protected",
        headers=headers
    )

    assert first_response.status_code == 200

    # Administrator later rejects/revokes account.
    user = app.db.users.find_one({"_id": APPROVED_ID})
    user["approval_status"] = "rejected"

    # Previously issued token must no longer work.
    second_response = client.get(
        "/api/protected",
        headers=headers
    )

    assert second_response.status_code == 403


# ==========================================
# TEST 5: IT ADMIN CAN VIEW PENDING IT USERS
# ==========================================

def test_it_admin_can_view_pending_users(app, client):
    response = client.get(
        "/api/admin/pending",
        headers=auth_headers(app, ADMIN_ID)
    )

    assert response.status_code == 200

    emails = [
        user["email"]
        for user in response.get_json()["users"]
    ]

    assert "pending@example.com" in emails
    assert "hr@example.com" not in emails


# ==========================================
# TEST 6: IT ADMIN CAN APPROVE IT USER
# ==========================================

def test_it_admin_can_approve_it_user(app, client):
    response = client.post(
        f"/api/admin/{PENDING_ID}/decision",
        headers=auth_headers(app, ADMIN_ID),
        json={"decision": "approve"}
    )

    assert response.status_code == 200

    user = app.db.users.find_one({"_id": PENDING_ID})

    assert user["approval_status"] == "approved"


# ==========================================
# TEST 7: IT ADMIN CANNOT APPROVE HR USER
# ==========================================

def test_it_admin_cannot_approve_hr_user(app, client):
    response = client.post(
        f"/api/admin/{HR_USER_ID}/decision",
        headers=auth_headers(app, ADMIN_ID),
        json={"decision": "approve"}
    )

    # Cross-division approval is forbidden.
    assert response.status_code == 403

    user = app.db.users.find_one({"_id": HR_USER_ID})

    assert user["approval_status"] == "pending"


# ==========================================
# TEST 8: ORDINARY USER CANNOT APPROVE
# ==========================================

def test_regular_user_cannot_approve(app, client):
    response = client.post(
        f"/api/admin/{PENDING_ID}/decision",
        headers=auth_headers(app, APPROVED_ID),
        json={"decision": "approve"}
    )

    assert response.status_code == 403


# ==========================================
# TEST 9: MISSING TOKEN BLOCKED
# ==========================================

def test_missing_token_blocked(client):
    response = client.get("/api/protected")

    assert response.status_code == 401
