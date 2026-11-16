
from datetime import datetime, timezone

from bson import ObjectId
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

admin_bp = Blueprint("admin", __name__)


def get_admin():
    user_id = get_jwt_identity()

    if not ObjectId.is_valid(user_id):
        return None

    user = current_app.db.users.find_one({
        "_id": ObjectId(user_id)
    })

    if not user:
        return None

    if user.get("role") != "admin":
        return None

    if user.get("approval_status") != "approved":
        return None

    return user


@admin_bp.route("/pending", methods=["GET"])
@jwt_required()
def pending_users():
    admin = get_admin()

    if not admin:
        return jsonify({
            "error": "Administrator access required"
        }), 403

    users = current_app.db.users.find({
        "approval_status": "pending",
        "division": admin["division"]
    })

    results = []

    for user in users:
        results.append({
            "user_id": str(user["_id"]),
            "username": user.get("username"),
            "email": user.get("email"),
            "division": user.get("division"),
            "approval_status": "pending"
        })

    return jsonify({
        "count": len(results),
        "users": results
    }), 200


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

    status = (
        "approved"
        if decision == "approve"
        else "rejected"
    )

    result = current_app.db.users.update_one(
        {
            "_id": ObjectId(user_id),
            "division": admin["division"],
            "approval_status": "pending",
            "role": "user"
        },
        {
            "$set": {
                "approval_status": status,
                "reviewed_by": admin["_id"],
                "reviewed_at": datetime.now(timezone.utc)
            }
        }
    )

    if result.modified_count == 0:
        return jsonify({
            "error": (
                "Pending user not found in your division "
                "or already reviewed"
            )
        }), 404

    return jsonify({
        "message": f"Registration {status} successfully",
        "user_id": user_id,
        "approval_status": status
    }), 200
