
import re
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)
from pymongo.errors import DuplicateKeyError


auth_bp = Blueprint("auth", __name__)

ALLOWED_DIVISIONS = {"HR", "IT", "FINANCE"}


def normalize_division(value):
    """Store division names consistently."""
    if not isinstance(value, str):
        return ""
    return value.strip().upper()


# ==========================================
# REGISTER USER
# ==========================================

@auth_bp.route("/register", methods=["POST"])
def register():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "A JSON object is required"
        }), 400

    username = str(data.get("username") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    password = data.get("password")
    division = normalize_division(data.get("division"))

    if not username or not email or not password or not division:
        return jsonify({
            "error": "All fields are required"
        }), 400

    if len(username) > 100:
        return jsonify({
            "error": "Username is too long"
        }), 400

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return jsonify({
            "error": "Invalid email address"
        }), 400

    if not isinstance(password, str) or len(password) < 8:
        return jsonify({
            "error": "Password must contain at least 8 characters"
        }), 400

    if division not in ALLOWED_DIVISIONS:
        return jsonify({
            "error": "Invalid division. Choose HR, IT or FINANCE."
        }), 400

    users = current_app.db.users

    try:
        users.create_index("email", unique=True)

        users.insert_one({
            "username": username,
            "email": email,
            "password": generate_password_hash(password),
            "division": division,

            # Public registration cannot create administrators.
            "role": "user",

            # Every new account needs division admin approval.
            "approval_status": "pending",

            "created_at": datetime.now(timezone.utc)
        })

    except DuplicateKeyError:
        return jsonify({
            "error": "Email already registered"
        }), 409

    return jsonify({
        "message": (
            "Registration successful. "
            "Your account is awaiting approval "
            "from your division administrator."
        ),
        "approval_status": "pending",
        "division": division
    }), 201


# ==========================================
# LOGIN USER
# ==========================================

@auth_bp.route("/login", methods=["POST"])
def login():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "A JSON object is required"
        }), 400

    email = str(data.get("email") or "").strip().lower()
    password = data.get("password")

    if not email or not isinstance(password, str) or not password:
        return jsonify({
            "error": "Email and password are required"
        }), 400

    user = current_app.db.users.find_one({
        "email": email
    })

    if not user or not check_password_hash(
        user.get("password", ""),
        password
    ):
        return jsonify({
            "error": "Invalid credentials"
        }), 401

    approval_status = user.get("approval_status")

    if approval_status == "pending":
        return jsonify({
            "error": (
                "Your account is awaiting approval "
                "from your division administrator."
            ),
            "approval_status": "pending",
            "division": user.get("division")
        }), 403

    if approval_status == "rejected":
        return jsonify({
            "error": (
                "Your registration was rejected. "
                "Contact your division administrator."
            ),
            "approval_status": "rejected"
        }), 403

    if approval_status != "approved":
        return jsonify({
            "error": "Your account is not approved."
        }), 403

    token = create_access_token(
        identity=str(user["_id"])
    )

    return jsonify({
        "access_token": token,
        "token": token,
        "username": user.get("username"),
        "division": user.get("division"),
        "role": user.get("role", "user"),
        "approval_status": "approved"
    }), 200
