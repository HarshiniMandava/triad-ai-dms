
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from bson import ObjectId
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from access import access_bp


@pytest.fixture
def setup_app():
    app = Flask(__name__)

    app.config["TESTING"] = True
    app.config["JWT_SECRET_KEY"] = (
        "triad-ai-dms-testing-secret-key-2026-secure"
    )

    JWTManager(app)

    app.register_blueprint(
        access_bp,
        url_prefix="/api/access"
    )

    owner_id = ObjectId()
    other_it_id = ObjectId()
    hr_id = ObjectId()
    admin_id = ObjectId()
    document_id = ObjectId()
    request_id = ObjectId()

    users = {
        owner_id: {
            "_id": owner_id,
            "division": "IT",
            "role": "user"
        },
        other_it_id: {
            "_id": other_it_id,
            "division": "IT",
            "role": "user"
        },
        hr_id: {
            "_id": hr_id,
            "division": "HR",
            "role": "user"
        },
        admin_id: {
            "_id": admin_id,
            "division": "IT",
            "role": "admin"
        }
    }

    document = {
        "_id": document_id,
        "division": "IT",
        "owner_id": owner_id
    }

    access_request = {
        "_id": request_id,
        "document_id": document_id,
        "requester_id": hr_id,
        "requester_division": "HR",
        "document_division": "IT",
        "status": "pending"
    }

    class FakeCollection:
        def __init__(self, records):
            self.records = records

        def find_one(self, query):
            record_id = query.get("_id")
            return self.records.get(record_id)

        def find(self, query):
            return [
                record
                for record in self.records.values()
                if all(
                    record.get(key) == value
                    for key, value in query.items()
                )
            ]

        def update_one(self, query, update):
            record = self.records.get(query.get("_id"))

            if not record:
                return SimpleNamespace(modified_count=0)

            if record.get("status") != query.get("status"):
                return SimpleNamespace(modified_count=0)

            record.update(update["$set"])
            return SimpleNamespace(modified_count=1)

    app.db = SimpleNamespace(
        users=FakeCollection(users),
        documents=FakeCollection({
            document_id: document
        }),
        access_requests=FakeCollection({
            request_id: access_request
        })
    )

    def headers_for(user_id):
        with app.app_context():
            token = create_access_token(
                identity=str(user_id)
            )

        return {
            "Authorization": f"Bearer {token}"
        }

    return SimpleNamespace(
        client=app.test_client(),
        headers_for=headers_for,
        owner_id=owner_id,
        other_it_id=other_it_id,
        hr_id=hr_id,
        admin_id=admin_id,
        request_id=request_id
    )


def approve(env, user_id):
    return env.client.post(
        "/api/access/approve",
        json={
            "request_id": str(env.request_id)
        },
        headers=env.headers_for(user_id)
    )


def test_owner_can_approve(setup_app):
    response = approve(
        setup_app,
        setup_app.owner_id
    )

    assert response.status_code == 200
    assert response.json["status"] == "approved"


def test_other_it_user_cannot_approve(setup_app):
    response = approve(
        setup_app,
        setup_app.other_it_id
    )

    assert response.status_code == 403


def test_hr_user_cannot_approve_it_request(setup_app):
    response = approve(
        setup_app,
        setup_app.hr_id
    )

    assert response.status_code == 403


def test_it_admin_can_approve(setup_app):
    response = approve(
        setup_app,
        setup_app.admin_id
    )

    assert response.status_code == 200


def test_duplicate_approval_is_blocked(setup_app):
    first = approve(
        setup_app,
        setup_app.owner_id
    )

    second = approve(
        setup_app,
        setup_app.owner_id
    )

    assert first.status_code == 200
    assert second.status_code == 409


def test_unauthorized_user_sees_no_pending_requests(setup_app):
    response = setup_app.client.get(
        "/api/access/pending",
        headers=setup_app.headers_for(
            setup_app.other_it_id
        )
    )

    assert response.status_code == 200
    assert response.json["count"] == 0
