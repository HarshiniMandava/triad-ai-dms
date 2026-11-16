
import os

from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from pymongo import MongoClient
from dotenv import load_dotenv

from auth import auth_bp
from documents import documents_bp
from access import access_bp
from search import search_bp
from admin import admin_bp
from security import enforce_approved_account


# ==========================================
# LOAD ENVIRONMENT VARIABLES
# ==========================================

load_dotenv()


# ==========================================
# INITIALIZE FLASK APPLICATION
# ==========================================

app = Flask(__name__)

app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")

# Allow only configured frontend origins
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "http://127.0.0.1:5500,http://localhost:5500"
    ).split(",")
    if origin.strip()
]

CORS(
    app,
    resources={
        r"/api/*": {
            "origins": allowed_origins
        }
    }
)

jwt = JWTManager(app)


# ==========================================
# CONNECT TO MONGODB ATLAS
# ==========================================

mongo_uri = os.getenv("MONGO_URI")
db_name = os.getenv("DB_NAME", "triad_ai_dms")

if not mongo_uri:
    raise ValueError("MONGO_URI is missing from .env")

if not app.config["JWT_SECRET_KEY"]:
    raise ValueError("JWT_SECRET_KEY is missing from .env")

client = MongoClient(
    mongo_uri,
    serverSelectionTimeoutMS=15000
)

client.admin.command("ping")

app.db = client[db_name]

print("MongoDB connected successfully!")


# ==========================================
# REGISTER API BLUEPRINTS
# ==========================================

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

app.register_blueprint(
    admin_bp,
    url_prefix="/api/admin"
)


# ==========================================
# ACCOUNT APPROVAL SECURITY
# ==========================================

@app.before_request
def check_account_approval():
    return enforce_approved_account()


# ==========================================
# HOME API
# ==========================================

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "TRIAD AI Document Management System API",
        "status": "running"
    }), 200


# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "false").lower() == "true",
        use_reloader=False
    )
