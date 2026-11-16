
import re

from bson import ObjectId
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

search_bp = Blueprint("search", __name__)


def metadata_matches(metadata, pattern):
    """
    Search all custom metadata field names and values.
    Supports nested dictionaries and lists.
    """
    if isinstance(metadata, dict):
        for key, value in metadata.items():
            if pattern.search(str(key)):
                return True

            if metadata_matches(value, pattern):
                return True

    elif isinstance(metadata, list):
        for item in metadata:
            if metadata_matches(item, pattern):
                return True

    elif metadata is not None:
        return bool(pattern.search(str(metadata)))

    return False


@search_bp.route("", methods=["GET"])
@search_bp.route("/", methods=["GET"])
@jwt_required()
def search_documents():
    # =====================================
    # 1. AUTHENTICATE USER
    # =====================================

    user_id = get_jwt_identity()

    if not ObjectId.is_valid(user_id):
        return jsonify({
            "error": "Invalid user"
        }), 401

    user = current_app.db.users.find_one({
        "_id": ObjectId(user_id)
    })

    if not user:
        return jsonify({
            "error": "User not found"
        }), 404

    # =====================================
    # 2. VALIDATE SEARCH QUERY
    # =====================================

    query = request.args.get("q", "").strip()

    if not query:
        return jsonify({
            "error": "Please enter a search keyword"
        }), 400

    if len(query) > 100:
        return jsonify({
            "error": "Search query too long"
        }), 400

    pattern = re.compile(
        re.escape(query),
        re.IGNORECASE
    )

    # =====================================
    # 3. FIND APPROVED DOCUMENTS
    # =====================================

    approved_ids = current_app.db.access_requests.distinct(
        "document_id",
        {
            "requester_id": user["_id"],
            "status": "approved"
        }
    )

    # =====================================
    # 4. ENFORCE DIVISION ACCESS
    # =====================================

    accessible_documents = current_app.db.documents.find({
        "$or": [
            {
                "division": user["division"]
            },
            {
                "_id": {
                    "$in": approved_ids
                }
            }
        ]
    })

    # =====================================
    # 5. SEARCH ALL DOCUMENT FIELDS
    # =====================================

    results = []

    for doc in accessible_documents:
        filename = doc.get("filename", "")
        extracted_text = doc.get("extracted_text", "")
        metadata = doc.get("metadata", {})

        filename_match = bool(
            pattern.search(str(filename))
        )

        ocr_match = bool(
            pattern.search(str(extracted_text))
        )

        metadata_match = metadata_matches(
            metadata,
            pattern
        )

        if not (
            filename_match
            or ocr_match
            or metadata_match
        ):
            continue

        results.append({
            "document_id": str(doc["_id"]),
            "filename": filename,
            "division": doc.get("division", ""),
            "metadata": metadata,
            "access_status": "accessible",
            "can_download": True
        })

    # =====================================
    # 6. RETURN RESULTS
    # =====================================

    return jsonify({
        "query": query,
        "count": len(results),
        "documents": results
    }), 200
