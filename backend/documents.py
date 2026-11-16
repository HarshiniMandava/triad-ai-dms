
import json
from io import BytesIO
from datetime import datetime, timezone

import gridfs
from bson import ObjectId
from flask import Blueprint, current_app, jsonify, request, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename

from ocr import extract_text


documents_bp = Blueprint("documents", __name__)

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"}
MAX_FILE_SIZE = 15 * 1024 * 1024


# ==========================================
# GET CURRENT LOGGED-IN USER
# ==========================================

def get_current_user():
    user_id = get_jwt_identity()

    if not ObjectId.is_valid(user_id):
        return None

    return current_app.db.users.find_one({
        "_id": ObjectId(user_id)
    })


# ==========================================
# UPLOAD DOCUMENT WITH OCR
# ==========================================

@documents_bp.route("/upload", methods=["POST"])
@jwt_required()
def upload_document():
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found"}), 404

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    filename = secure_filename(file.filename or "")

    if not filename:
        return jsonify({"error": "Invalid filename"}), 400

    extension = "." + filename.rsplit(".", 1)[-1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        return jsonify({"error": "Unsupported file type"}), 400

    metadata_text = request.form.get("metadata", "{}")

    try:
        metadata = json.loads(metadata_text)
    except json.JSONDecodeError:
        return jsonify({"error": "Metadata must be valid JSON"}), 400

    if not isinstance(metadata, dict):
        return jsonify({"error": "Metadata must be a JSON object"}), 400

    if any(
        not isinstance(key, str)
        or not key.strip()
        or key.startswith("$")
        or "." in key
        for key in metadata
    ):
        return jsonify({
            "error": "Metadata contains invalid field names."
        }), 400

    file_bytes = file.read(MAX_FILE_SIZE + 1)

    if len(file_bytes) > MAX_FILE_SIZE:
        return jsonify({"error": "File exceeds 15 MB limit"}), 413

    if not file_bytes:
        return jsonify({"error": "File is empty"}), 400

    extracted_text = extract_text(file_bytes, filename)

    fs = gridfs.GridFS(current_app.db)

    file_id = fs.put(
        file_bytes,
        filename=filename,
        content_type=file.content_type
    )

    document_data = {
        "filename": filename,
        "file_id": file_id,
        "owner_id": user["_id"],
        "division": user["division"],
        "metadata": metadata,
        "extracted_text": extracted_text,
        "created_at": datetime.now(timezone.utc)
    }

    try:
        result = current_app.db.documents.insert_one(document_data)
    except Exception:
        fs.delete(file_id)
        raise

    return jsonify({
        "message": "Document uploaded successfully",
        "document_id": str(result.inserted_id),
        "file_id": str(file_id),
        "extracted_characters": len(extracted_text)
    }), 201


# ==========================================
# LIST DOCUMENTS WITH DYNAMIC METADATA FILTERS
# ==========================================

@documents_bp.route("", methods=["GET"])
@documents_bp.route("/", methods=["GET"])
@jwt_required()
def list_documents():
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found"}), 404

    # Find documents with approved cross-division access.
    approved_ids = current_app.db.access_requests.distinct(
        "document_id",
        {
            "requester_id": user["_id"],
            "status": "approved"
        }
    )

    # Mandatory RBAC filter.
    # Users can only list documents in their own division
    # or documents for which they have approved access.
    access_filter = {
        "$or": [
            {"division": user["division"]},
            {"_id": {"$in": approved_ids}}
        ]
    }

    # Additional filters supplied in the URL.
    # Examples:
    # ?Department=HR
    # ?Report%20Type=Financial
    # ?Priority=High
    # ?Department=HR&Priority=High

    extra_filters = []

    for key, value in request.args.items():
        if not key or key.startswith("$") or "." in key:
            return jsonify({
                "error": "Invalid filter field name."
            }), 400

        if key == "division":
            # Division is stored directly on the document.
            extra_filters.append({
                "division": value
            })
        else:
            # All other fields are dynamic metadata fields.
            extra_filters.append({
                f"metadata.{key}": value
            })

    # $and ensures user filters cannot override RBAC.
    if extra_filters:
        query = {
            "$and": [
                access_filter,
                *extra_filters
            ]
        }
    else:
        query = access_filter

    documents = current_app.db.documents.find(
        query
    ).sort("created_at", -1)

    results = []

    for doc in documents:
        results.append({
            "document_id": str(doc["_id"]),
            "filename": doc["filename"],
            "division": doc["division"],
            "metadata": doc.get("metadata", {}),
            "owner_id": str(doc["owner_id"])
        })

    return jsonify({
        "count": len(results),
        "documents": results
    }), 200


# ==========================================
# DOWNLOAD DOCUMENT WITH RBAC
# ==========================================

@documents_bp.route("/<doc_id>/download", methods=["GET"])
@jwt_required()
def download_document(doc_id):
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found"}), 404

    if not ObjectId.is_valid(doc_id):
        return jsonify({"error": "Invalid document ID"}), 400

    document = current_app.db.documents.find_one({
        "_id": ObjectId(doc_id)
    })

    if not document:
        return jsonify({"error": "Document not found"}), 404

    same_division = document["division"] == user["division"]

    approved_request = current_app.db.access_requests.find_one({
        "document_id": document["_id"],
        "requester_id": user["_id"],
        "status": "approved"
    })

    if not same_division and not approved_request:
        return jsonify({
            "error": "Access denied. Approval required."
        }), 403

    fs = gridfs.GridFS(current_app.db)

    try:
        stored_file = fs.get(document["file_id"])
    except gridfs.errors.NoFile:
        return jsonify({"error": "Stored file not found"}), 404

    return send_file(
        BytesIO(stored_file.read()),
        as_attachment=True,
        download_name=document["filename"],
        mimetype=stored_file.content_type or "application/octet-stream"
    )


# ==========================================
# DOCUMENT DETAILS API
# ==========================================

@documents_bp.route("/<doc_id>", methods=["GET"])
@jwt_required()
def get_document_details(doc_id):
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found"}), 404

    if not ObjectId.is_valid(doc_id):
        return jsonify({"error": "Invalid document ID"}), 400

    document = current_app.db.documents.find_one({
        "_id": ObjectId(doc_id)
    })

    if not document:
        return jsonify({"error": "Document not found"}), 404

    same_division = document["division"] == user["division"]

    approved_request = current_app.db.access_requests.find_one({
        "document_id": document["_id"],
        "requester_id": user["_id"],
        "status": "approved"
    })

    # Security fix:
    # Admins cannot bypass cross-division restrictions.
    if not (same_division or approved_request):
        return jsonify({
            "error": "Access denied. Approval required."
        }), 403

    created_at = document.get("created_at")

    return jsonify({
        "document_id": str(document["_id"]),
        "filename": document["filename"],
        "division": document["division"],
        "owner_id": str(document["owner_id"]),
        "metadata": document.get("metadata", {}),
        "extracted_text": document.get("extracted_text", ""),
        "created_at": (
            created_at.isoformat() if created_at else None
        )
    }), 200


# ==========================================
# SECURE DOCUMENT PREVIEW API
# ==========================================

@documents_bp.route("/<doc_id>/preview", methods=["GET"])
@jwt_required()
def preview_document(doc_id):
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found"}), 404

    if not ObjectId.is_valid(doc_id):
        return jsonify({"error": "Invalid document ID"}), 400

    document = current_app.db.documents.find_one({
        "_id": ObjectId(doc_id)
    })

    if not document:
        return jsonify({"error": "Document not found"}), 404

    same_division = document["division"] == user["division"]

    approved_request = current_app.db.access_requests.find_one({
        "document_id": document["_id"],
        "requester_id": user["_id"],
        "status": "approved"
    })

    is_owner = document["owner_id"] == user["_id"]

    if not (same_division or approved_request or is_owner):
        return jsonify({
            "error": "Access denied. Approval required."
        }), 403

    if not document["filename"].lower().endswith(".pdf"):
        return jsonify({
            "error": "Preview is currently supported for PDF files only."
        }), 400

    fs = gridfs.GridFS(current_app.db)

    try:
        stored_file = fs.get(document["file_id"])
    except gridfs.errors.NoFile:
        return jsonify({"error": "Stored file not found"}), 404

    return send_file(
        BytesIO(stored_file.read()),
        mimetype="application/pdf",
        as_attachment=False,
        download_name=document["filename"]
    )


# ==========================================
# UPDATE DOCUMENT METADATA
# ==========================================

@documents_bp.route("/<doc_id>/metadata", methods=["PATCH"])
@jwt_required()
def update_document_metadata(doc_id):
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found"}), 404

    if not ObjectId.is_valid(doc_id):
        return jsonify({"error": "Invalid document ID"}), 400

    document = current_app.db.documents.find_one({
        "_id": ObjectId(doc_id)
    })

    if not document:
        return jsonify({"error": "Document not found"}), 404

    # Only the owner can edit metadata.
    if document["owner_id"] != user["_id"]:
        return jsonify({
            "error": "Only the document owner can edit metadata."
        }), 403

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Request body must be a JSON object."
        }), 400

    metadata = data.get("metadata")

    if not isinstance(metadata, dict):
        return jsonify({
            "error": "Metadata must be a JSON object."
        }), 400

    if any(
        not isinstance(key, str)
        or not key.strip()
        or key.startswith("$")
        or "." in key
        for key in metadata
    ):
        return jsonify({
            "error": "Metadata contains invalid field names."
        }), 400

    current_app.db.documents.update_one(
        {"_id": document["_id"]},
        {"$set": {"metadata": metadata}}
    )

    return jsonify({
        "message": "Metadata updated successfully.",
        "document_id": doc_id,
        "metadata": metadata
    }), 200


# ==========================================
# DISCOVER DOCUMENTS ACROSS DIVISIONS
# ==========================================

@documents_bp.route("/discover", methods=["GET"])
@jwt_required()
def discover_documents():
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found"}), 404

    documents = current_app.db.documents.find(
        {},
        {
            "filename": 1,
            "division": 1,
            "created_at": 1
        }
    ).sort("created_at", -1)

    results = []

    for doc in documents:
        same_division = doc["division"] == user["division"]

        access_request = current_app.db.access_requests.find_one(
            {
                "document_id": doc["_id"],
                "requester_id": user["_id"],
                "status": {
                    "$in": ["pending", "approved"]
                }
            },
            sort=[("created_at", -1)]
        )

        if same_division:
            access_status = "accessible"
        elif access_request:
            access_status = access_request["status"]
        else:
            access_status = "restricted"

        results.append({
            "document_id": str(doc["_id"]),
            "filename": doc["filename"],
            "division": doc["division"],
            "access_status": access_status,
            "can_download": access_status in [
                "accessible",
                "approved"
            ]
        })

    return jsonify({
        "count": len(results),
        "documents": results
    }), 200
