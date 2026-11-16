
import os
import sys
from pathlib import Path

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager

# Allow imports from the backend folder
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from auth import auth_bp
from documents import documents_bp
from access import access_bp
from search import search_bp


@pytest.fixture
def client():
    """
    Create a Flask test app without connecting to
    the real MongoDB database.
    """
    app = Flask(__name__)

    app.config.update(
        TESTING=True,
        JWT_SECRET_KEY="test-only-secret-key",
    )

    JWTManager(app)

    app.register_blueprint(
        auth_bp,
        url_prefix="/api/auth"
    )
    app.register_blueprint(
        documents_bp,
        url_prefix="/api/documents"
    )
    app.register_blueprint(
        access_bp,
        url_prefix="/api/access"
    )
    app.register_blueprint(
        search_bp,
        url_prefix="/api/search"
    )

    with app.test_client() as test_client:
        yield test_client


def test_search_without_token(client):
    response = client.get("/api/search?q=test")

    assert response.status_code == 401


def test_search_without_query(client):
    response = client.get("/api/search")

    assert response.status_code == 401


def test_documents_without_token(client):
    response = client.get("/api/documents/")

    assert response.status_code == 401


def test_upload_without_token(client):
    response = client.post("/api/documents/upload")

    assert response.status_code == 401


def test_download_without_token(client):
    document_id = "507f1f77bcf86cd799439011"

    response = client.get(
        f"/api/documents/{document_id}/download"
    )

    assert response.status_code == 401


def test_access_request_without_token(client):
    response = client.post(
        "/api/access/request",
        json={
            "doc_id": "507f1f77bcf86cd799439011"
        }
    )

    assert response.status_code == 401


def test_pending_requests_without_token(client):
    response = client.get("/api/access/pending")

    assert response.status_code == 401


def test_approval_without_token(client):
    request_id = "507f1f77bcf86cd799439011"

    response = client.post(
        f"/api/access/{request_id}/decision",
        json={
            "decision": "approved"
        }
    )

    assert response.status_code == 401


def test_home_endpoint():
    """
    Test the public home endpoint using a minimal
    Flask app. No database connection required.
    """
    app = Flask(__name__)

    @app.get("/")
    def home():
        return {
            "message": "TRIAD AI Document Management System API",
            "status": "running"
        }, 200

    with app.test_client() as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.json["status"] == "running"
