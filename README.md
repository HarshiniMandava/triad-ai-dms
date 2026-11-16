# TRIAD AI — Document Management System

## Project Overview

A full-stack Document Management System developed for the TRIAD AI Full Stack Developer Internship assignment.

The application allows users to securely upload, store, search, preview, and download documents. It supports division-based access control, customizable document metadata, OCR-powered search, and cross-division access requests.

## Technology Stack

**Backend:** Python, Flask, REST APIs, JWT Authentication

**Database:** MongoDB Atlas, GridFS

**Frontend:** HTML, CSS, JavaScript

**Document Processing:** PyMuPDF, Tesseract OCR, Pytesseract

**Testing:** Pytest

## Features

- User registration and JWT-based login
- Admin approval of new user accounts
- Division-based role-based access control (RBAC)
- Document upload, preview, and download
- PDF and image text extraction using OCR
- Search across document text and metadata
- Dynamic document metadata editing
- Cross-division access requests
- Approval and rejection workflows
- Document dashboard with search and filters

## Project Structure

```text
triad-ai-dms/
├── backend/
├── frontend/
├── tests/
├── requirements.txt
├── Procfile
├── .env.example
├── .gitignore
└── README.md
```

## Installation and Setup

### 1. Requirements

- Python 3.12
- MongoDB Atlas database
- Tesseract OCR for scanned PDFs and images

### 2. Install Python Dependencies

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the project root using `.env.example` as a reference.

Set the MongoDB connection string and a secure JWT secret.

Never upload `.env` to GitHub.

### 4. Start Backend

```powershell
python backend\app.py
```

Backend URL:

`http://127.0.0.1:5000`

### 5. Start Frontend

Open a second terminal:

```powershell
python -m http.server 5500 --directory frontend
```

Frontend URL:

`http://127.0.0.1:5500/index.html`

### 6. Run Automated Tests

```powershell
python -m pytest tests/ -v
```

The original development version passed 32 automated tests.

## Main REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register` | Register a user |
| POST | `/api/auth/login` | Authenticate user |
| POST | `/api/documents/upload` | Upload a document |
| GET | `/api/documents` | List accessible documents |
| GET | `/api/documents/<doc_id>/download` | Download an authorized document |
| POST | `/api/access/request` | Request cross-division access |
| POST | `/api/access/approve` | Approve an access request |
| GET | `/api/search?q=keyword` | Search documents |
| GET | `/api/admin/pending` | List pending accounts |
| POST | `/api/admin/<user_id>/decision` | Approve or reject an account |

## Security

- JWT authentication protects API endpoints.
- Users are assigned to divisions.
- Users can access their own division's documents by default.
- Cross-division downloads require approval.
- Pending and rejected accounts cannot use protected APIs.
- Environment variables store sensitive configuration.

## Deployment

The backend includes a Procfile for compatible Linux hosting environments.

Configure the backend environment variables on the hosting platform and update `frontend/config.js` with the deployed backend API URL.

Tesseract must also be installed on the hosting environment for scanned-document OCR.

Docker deployment is optional under the assignment requirements.

## Testing and Validation

The project includes automated tests covering authentication, API functionality, document access restrictions, and administrator security.

The complete application should be verified locally before final submission.

## Assignment

Developed as part of the TRIAD AI Full Stack Developer Internship take-home assignment.