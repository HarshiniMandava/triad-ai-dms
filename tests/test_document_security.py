
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from bson import ObjectId
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from documents import documents_bp


@pytest.fixture
def env():
    app = Flask(__name__)

    app.config.update(
        TESTING=True,
        JWT_SECRET_KEY="triad-dms-isolated-testing-secret-key-2026"
    )

    JWTManager(app)

    app.register_blueprint(
        documents_bp,
        url_prefix="/api/documents"
    )

    owner_id = ObjectId()
    colleague_id = ObjectId()
    hr_id = ObjectId()
    document_id = ObjectId()
    file_id = ObjectId()

    users = {
        owner_id: {
            "_id": owner_id,
            "division": "IT",
            "role": "user"
        },
        colleague_id: {
            "_id": colleague_id,
            "division": "IT",
            "role": "user"
        },
        hr_id: {
            "_id": hr_id,
            "division": "HR",
            "role": "user"
        }
    }

    document = {
        "_id": document_id,
        "filename": "security_test.pdf",
        "division": "IT",
        "owner_id": owner_id,
        "file_id": file_id,
        "metadata": {"category": "Test"},
        "extracted_text": "Security test content"
    }

    access_records = {}

    class FakeCollection:
        def __init__(self, records):
            self.records = records

        def find_one(self, query):
            for record in self.records.values():
                if all(
                    record.get(key) == value
                    for key, value in query.items()
                ):
                    return record
            return None

        def update_one(self, query, update):
            record = self.find_one(query)

            if record is None:
                return SimpleNamespace(modified_count=0)

            record.update(update["$set"])
            return SimpleNamespace(modified_count=1)

    app.db = SimpleNamespace(
        users=FakeCollection(users),
        documents=FakeCollection({
            document_id: document
        }),
        access_requests=FakeCollection(access_records)
    )

    class FakeStoredFile:
        content_type = "application/pdf"

        def read(self):
            return b"%PDF-1.4\nTest document\n%%EOF"

    class FakeGridFS:
        def __init__(self, database):
            pass

        def get(self, requested_file_id):
            assert requested_file_id == file_id
            return FakeStoredFile()

    def headers_for(user_id):
        with app.app_context():
            token = create_access_token(
                identity=str(user_id)
            )

        return {
            "Authorization": f"Bearer {token}"
        }

    with patch("documents.gridfs.GridFS", FakeGridFS):
        yield SimpleNamespace(
            client=app.test_client(),
            headers_for=headers_for,
            owner_id=owner_id,
            colleague_id=colleague_id,
            hr_id=hr_id,
            document_id=document_id,
            access_records=access_records,
            document=document
        )


def download(env, user_id, document_id=None):
    document_id = document_id or env.document_id

    return env.client.get(
        f"/api/documents/{document_id}/download",
        headers=env.headers_for(user_id)
    )


def grant_request(env, status):
    request_id = ObjectId()

    env.access_records[request_id] = {
        "_id": request_id,
        "document_id": env.document_id,
        "requester_id": env.hr_id,
        "status": status
    }


def test_same_division_download_allowed(env):
    response = download(env, env.colleague_id)

    assert response.status_code == 200
    assert response.data.startswith(b"%PDF")


def test_cross_division_download_denied(env):
    response = download(env, env.hr_id)

    assert response.status_code == 403


def test_pending_request_cannot_download(env):
    grant_request(env, "pending")

    response = download(env, env.hr_id)

    assert response.status_code == 403


def test_approved_request_can_download(env):
    grant_request(env, "approved")

    response = download(env, env.hr_id)

    assert response.status_code == 200
    assert response.data.startswith(b"%PDF")


def test_missing_document_returns_404(env):
    response = download(
        env,
        env.owner_id,
        ObjectId()
    )

    assert response.status_code == 404


def test_non_owner_cannot_edit_metadata(env):
    response = env.client.patch(
        f"/api/documents/{env.document_id}/metadata",
        json={
            "metadata": {
                "category": "Unauthorized change"
            }
        },
        headers=env.headers_for(env.colleague_id)
    )

    assert response.status_code == 403
    assert env.document["metadata"] == {
        "category": "Test"
    }


def test_owner_can_edit_metadata(env):
    response = env.client.patch(
        f"/api/documents/{env.document_id}/metadata",
        json={
            "metadata": {
                "category": "Updated"
            }
        },
        headers=env.headers_for(env.owner_id)
    )

    assert response.status_code == 200
    assert env.document["metadata"] == {
        "category": "Updated"
    }


def test_download_without_token_returns_401(env):
    response = env.client.get(
        f"/api/documents/{env.document_id}/download"
    )

    assert response.status_code == 401
