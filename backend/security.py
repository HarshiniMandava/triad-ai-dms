
from bson import ObjectId
from flask import current_app, jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_jwt_extended.exceptions import NoAuthorizationError
from jwt.exceptions import PyJWTError


def get_approved_user():
    user_id = get_jwt_identity()

    if not user_id or not ObjectId.is_valid(user_id):
        return None

    user = current_app.db.users.find_one({
        "_id": ObjectId(user_id)
    })

    if not user:
        return None

    if user.get("approval_status") != "approved":
        return None

    return user


def enforce_approved_account():
    # Apply this to all protected API endpoints.
    # Public registration, login, and home are excluded.

    public_endpoints = {
        "auth.register",
        "auth.login",
        "home"
    }

    if current_app.view_functions.get(
        "static"
    ) is not None:
        public_endpoints.add("static")

    from flask import request

    if request.method == "OPTIONS":
        return None

    if request.endpoint in public_endpoints:
        return None

    if not request.path.startswith("/api/"):
        return None

    # Let @jwt_required handle missing or invalid JWTs.
    verify_jwt_in_request()

    user = get_approved_user()

    if not user:
        return jsonify({
            "error": "Account approval required or user not found"
        }), 403

    return None
