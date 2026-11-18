
from datetime import datetime, timezone

from bson import ObjectId
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

admin_bp = Blueprint("admin", __name__)


def normalize_division(value):
    """Make division comparisons consistent."""
    if not isinstance(value, str):
        return ""
    return value.strip().casefold()


def get_admin():
    """Get the currently authenticated administrator."""
    user_id = get_jwt_identity()

    if not isinstance(user_id, str):
        return None

    if not ObjectId.is_valid(user_id):
        return None

    admin = current_app.db.users.find_one({
        "_id": ObjectId(user_id)
    })

    if not admin:
        return None

    if str(admin.get("role", "")).lower() != "admin":
        return None

    if admin.get("approval_status") != "approved":
        return None

    if not normalize_division(admin.get("division")):
        return None

    return admin


# ==========================================
# LIST PENDING USERS FOR CURRENT ADMIN
# ==========================================

@admin_bp.route("/pending", methods=["GET"])
@jwt_required()
def pending_users():

    admin = get_admin()

    if not admin:
        return jsonify({
            "error": "Administrator access required"
        }), 403

    admin_division = normalize_division(
        admin.get("division")
    )

    pending = current_app.db.users.find({
        "approval_status": "pending",
        "role": "user"
    })

    results = []

    for user in pending:

        user_division = normalize_division(
            user.get("division")
        )

        if user_division != admin_division:
            continue

        results.append({
            "user_id": str(user["_id"]),
            "username": user.get("username", ""),
            "email": user.get("email", ""),
            "division": user.get("division", ""),
            "approval_status": "pending"
        })

    results.sort(
        key=lambda item: item["username"].lower()
    )

    return jsonify({
        "count": len(results),
        "users": results
    }), 200


# ==========================================
# APPROVE OR REJECT REGISTRATION
# ==========================================

@admin_bp.route("/<user_id>/decision", methods=["POST"])
@jwt_required()
def decide_registration(user_id):

    admin = get_admin()

    if not admin:
        return jsonify({
            "error": "Administrator access required"
        }), 403

    if not ObjectId.is_valid(user_id):
        return jsonify({
            "error": "Invalid user ID"
        }), 400

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "JSON body required"
        }), 400

    decision = data.get("decision")

    if decision not in ["approve", "reject"]:
        return jsonify({
            "error": "Decision must be approve or reject"
        }), 400

    target = current_app.db.users.find_one({
        "_id": ObjectId(user_id),
        "role": "user",
        "approval_status": "pending"
    })

    if not target:
        return jsonify({
            "error": "Pending user not found or already reviewed"
        }), 404

    admin_division = normalize_division(
        admin.get("division")
    )

    target_division = normalize_division(
        target.get("division")
    )

    if (
        not target_division
        or target_division != admin_division
    ):
        return jsonify({
            "error": (
                "You can approve users "
                "only from your own division"
            )
        }), 403

    new_status = (
        "approved"
        if decision == "approve"
        else "rejected"
    )

    result = current_app.db.users.update_one(
        {
            "_id": target["_id"],
            "division": target["division"],
            "role": "user",
            "approval_status": "pending"
        },
        {
            "$set": {
                "approval_status": new_status,
                "reviewed_by": admin["_id"],
                "reviewed_at": datetime.now(
                    timezone.utc
                )
            }
        }
    )

    if result.modified_count != 1:
        return jsonify({
            "error": "Account already reviewed. Refresh the page."
        }), 409

    return jsonify({
        "message": f"User {new_status} successfully",
        "user_id": user_id,
        "approval_status": new_status
    }), 200
