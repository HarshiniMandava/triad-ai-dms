
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from datetime import datetime, timezone

access_bp = Blueprint("access", __name__)


# ==========================================
# CURRENT USER
# ==========================================

def get_current_user():
    user_id = get_jwt_identity()

    if not user_id or not ObjectId.is_valid(user_id):
        return None

    return current_app.db.users.find_one({
        "_id": ObjectId(user_id)
    })


# ==========================================
# SERIALIZE ACCESS REQUEST
# ==========================================

def serialize_request(item):
    return {
        "request_id": str(item["_id"]),
        "document_id": str(item["document_id"]),
        "doc_id": str(item["document_id"]),
        "requester_id": str(item["requester_id"]),
        "requester_division": item.get(
            "requester_division", ""
        ),
        "document_division": item.get(
            "document_division", ""
        ),
        "status": item.get("status", "pending")
    }


# ==========================================
# SECURE PERMISSION CHECK
# ==========================================

def can_manage_request(user, document):
    """
    Only the document owner or an administrator
    belonging to the document's division
    can approve or reject access requests.
    """

    if not user or not document:
        return False

    # Division isolation is mandatory.
    if user.get("division") != document.get("division"):
        return False

    owner_id = document.get("owner_id")
    user_id = user.get("_id")

    is_owner = (
        owner_id is not None
        and user_id is not None
        and str(owner_id) == str(user_id)
    )

    is_admin = user.get("role") == "admin"

    return is_owner or is_admin


# ==========================================
# REQUEST DOCUMENT ACCESS
#
# POST /api/access/request
# ==========================================

@access_bp.route("/request", methods=["POST"])
@jwt_required()
def request_document_access():

    user = get_current_user()

    if not user:
        return jsonify({
            "error": "User not found"
        }), 404

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "JSON object required"
        }), 400

    document_id = (
        data.get("doc_id")
        or data.get("document_id")
    )

    if (
        not document_id
        or not ObjectId.is_valid(document_id)
    ):
        return jsonify({
            "error": "Invalid document ID"
        }), 400

    document = current_app.db.documents.find_one({
        "_id": ObjectId(document_id)
    })

    if not document:
        return jsonify({
            "error": "Document not found"
        }), 404

    # Users already have access to their own division.
    if document.get("division") == user.get("division"):
        return jsonify({
            "message": "You already have access to this division"
        }), 400

    # Check for existing active requests.
    existing = current_app.db.access_requests.find_one({
        "document_id": document["_id"],
        "requester_id": user["_id"],
        "status": {
            "$in": ["pending", "approved"]
        }
    })

    if existing:
        return jsonify({
            "message": "An active access request already exists",
            "request_id": str(existing["_id"]),
            "status": existing["status"]
        }), 409

    new_request = {
        "document_id": document["_id"],
        "requester_id": user["_id"],
        "requester_division": user["division"],
        "document_division": document["division"],
        "status": "pending",
        "created_at": datetime.now(timezone.utc)
    }

    result = current_app.db.access_requests.insert_one(
        new_request
    )

    return jsonify({
        "message": "Access request submitted successfully",
        "request_id": str(result.inserted_id),
        "doc_id": str(document["_id"]),
        "status": "pending"
    }), 201


# ==========================================
# GET PENDING REQUESTS
#
# GET /api/access/pending
# ==========================================

@access_bp.route("/pending", methods=["GET"])
@jwt_required()
def get_pending_requests():

    user = get_current_user()

    if not user:
        return jsonify({
            "error": "User not found"
        }), 404

    pending = current_app.db.access_requests.find({
        "status": "pending",
        "document_division": user["division"]
    })

    results = []

    for item in pending:

        document = current_app.db.documents.find_one({
            "_id": item["document_id"]
        })

        if not document:
            continue

        if can_manage_request(user, document):
            results.append(
                serialize_request(item)
            )

    return jsonify({
        "count": len(results),
        "requests": results
    }), 200


# ==========================================
# SHARED APPROVAL / REJECTION LOGIC
# ==========================================

def process_access_decision(request_id, decision):

    user = get_current_user()

    if not user:
        return jsonify({
            "error": "User not found"
        }), 404

    if (
        not request_id
        or not ObjectId.is_valid(request_id)
    ):
        return jsonify({
            "error": "Invalid request ID"
        }), 400

    if decision not in ["approved", "rejected"]:
        return jsonify({
            "error": "Decision must be approved or rejected"
        }), 400

    access_request = current_app.db.access_requests.find_one({
        "_id": ObjectId(request_id)
    })

    if not access_request:
        return jsonify({
            "error": "Request not found"
        }), 404

    document = current_app.db.documents.find_one({
        "_id": access_request["document_id"]
    })

    if not document:
        return jsonify({
            "error": "Document not found"
        }), 404

    # Check owner/admin permissions.
    if not can_manage_request(user, document):
        return jsonify({
            "error": (
                "Only the document owner or an authorized "
                "administrator from the document's division "
                "can approve or reject this request"
            )
        }), 403

    # Update only pending requests.
    result = current_app.db.access_requests.update_one(
        {
            "_id": access_request["_id"],
            "status": "pending"
        },
        {
            "$set": {
                "status": decision,
                "decided_by": user["_id"],
                "decided_at": datetime.now(timezone.utc)
            }
        }
    )

    if result.modified_count == 0:
        return jsonify({
            "error": "Request has already been processed"
        }), 409

    return jsonify({
        "message": f"Access request {decision} successfully",
        "request_id": str(access_request["_id"]),
        "status": decision
    }), 200


# ==========================================
# APPROVE ACCESS REQUEST
#
# POST /api/access/approve
# ==========================================

@access_bp.route("/approve", methods=["POST"])
@jwt_required()
def approve_access_request():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "JSON object required"
        }), 400

    request_id = data.get("request_id")

    return process_access_decision(
        request_id,
        "approved"
    )


# ==========================================
# REJECT ACCESS REQUEST
#
# POST /api/access/reject
# ==========================================

@access_bp.route("/reject", methods=["POST"])
@jwt_required()
def reject_access_request():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "JSON object required"
        }), 400

    request_id = data.get("request_id")

    return process_access_decision(
        request_id,
        "rejected"
    )


# ==========================================
# FRONTEND-COMPATIBLE DECISION ENDPOINT
#
# POST /api/access/<request_id>/decision
# ==========================================

@access_bp.route(
    "/<request_id>/decision",
    methods=["POST"]
)
@jwt_required()
def decide_request(request_id):

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "JSON object required"
        }), 400

    decision = data.get("decision")

    return process_access_decision(
        request_id,
        decision
    )
