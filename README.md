# TRIAD AI — Document Management System

## Project Overview

A full-stack Document Management System (DMS) developed for the **TRIAD AI Full Stack Developer Internship Take-Home Assignment**.

The application allows users to securely upload, store, search, preview, and download documents. It supports division-based access control, customizable document metadata, OCR-powered search, and cross-division access requests.

The system is designed to ensure secure document handling, controlled access between organizational divisions, and efficient document retrieval.

## Technology Stack

| Component | Technologies |
|---|---|
| Backend | Python 3.12, Flask, REST APIs |
| Database | MongoDB Atlas |
| File Storage | MongoDB GridFS |
| Authentication | JWT Authentication |
| Frontend | HTML, CSS, JavaScript |
| Document Processing | PyMuPDF, Tesseract OCR, Pytesseract |
| Testing | Pytest |

## Key Features

### 1. User Authentication and Account Approval
- User registration and JWT-based login
- Administrator approval and rejection of new user accounts
- Restricted access for pending and rejected accounts
- Role-based permissions for administrators and regular users

### 2. Division-Based Access Control
- Users are assigned to organizational divisions such as IT and HR
- Users can access documents belonging to their own division by default
- Unauthorized cross-division downloads are blocked
- Division administrators can manage permitted approval requests

### 3. Document Management
- Upload PDF and supported image documents
- Store uploaded files using MongoDB GridFS
- View and download authorized documents
- Organize documents using metadata and filters
- Edit document metadata according to user permissions

### 4. Dynamic Custom Metadata
- Configurable document metadata fields
- Support for different document categories and attributes
- Metadata editing and document filtering
- Extensible metadata organization

### 5. OCR-Powered Search
- Extract text from PDF documents
- Use Tesseract OCR for scanned documents and images
- Search across extracted document content
- Search and filter using document metadata

### 6. Cross-Division Access Requests
- Request access to documents belonging to another division
- Review pending access requests
- Approve or reject requests based on authorization rules
- Allow authorized downloads after approval

### 7. Web Dashboard
- Document listing and management
- Document upload interface
- Search and filtering
- Document preview
- Access request management
- User approval workflows
- Custom metadata management

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
├── test_report.txt
└── README.md
```

The structure above shows the main project components and submission files.

## Installation and Setup

### 1. Prerequisites

Ensure the following are available:

- Python 3.12
- MongoDB Atlas database
- Tesseract OCR for scanned PDFs and images
- Git (for cloning and submission)

### 2. Clone the Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd triad-ai-dms
```

Replace the placeholder URL with your repository link after publishing the project.

### 3. Create and Activate Virtual Environment

Open PowerShell in the project folder.

```powershell
python -m venv venv
```

Activate the environment:

```powershell
.\venv\Scripts\Activate.ps1
```

### 4. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Create a `.env` file in the project root using `.env.example` as a reference.

Configure the MongoDB connection URI, JWT secret, and any other settings required by the application.

**Security note:** Never upload `.env`, passwords, JWT secrets, or MongoDB credentials to GitHub.

### 6. Start the Backend

In the first VS Code terminal, activate the virtual environment and run:

```powershell
python backend\app.py
```

Backend URL:

http://127.0.0.1:5000

### 7. Start the Frontend

Open a second VS Code terminal in the project root.

```powershell
python -m http.server 5500 --directory frontend
```

Frontend URL:

http://127.0.0.1:5500/index.html

Open the frontend URL in your browser to access the application.

## Main REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register` | Register a new user |
| POST | `/api/auth/login` | Authenticate a user |
| POST | `/api/documents/upload` | Upload a document |
| GET | `/api/documents` | List accessible documents |
| GET | `/api/documents/<doc_id>/download` | Download an authorized document |
| POST | `/api/access/request` | Request cross-division document access |
| POST | `/api/access/approve` | Approve an access request |
| GET | `/api/access/pending` | View pending access requests |
| GET | `/api/search?q=keyword` | Search document content and metadata |
| GET | `/api/admin/pending` | List pending user accounts |
| POST | `/api/admin/<user_id>/decision` | Approve or reject a user account |

## Security Implementation

The application implements multiple security controls:

- JWT authentication for protected endpoints
- Administrator and regular-user permissions
- Division-based access restrictions
- Approved-account validation
- Restricted access for pending and rejected users
- Cross-division document access approval
- Prevention of unauthorized document downloads
- Owner-based document metadata permissions
- Validation of administrator approval privileges
- Sensitive configuration stored in environment variables

## Testing and Validation

The application was tested using **Pytest** and additional manual API tests.

### Automated Testing

Run the complete automated test suite from the project root:

```powershell
python -m pytest tests/ -v
```

### Final Automated Test Results

| Metric | Result |
|---|---|
| Total tests | 32 |
| Passed | 32 |
| Failed | 0 |
| Pass rate | 100% |

All 32 automated tests passed successfully during final local testing.

### Automated Test Coverage

The tests cover:

- User approval and rejection security
- JWT authentication and authorization
- Blocking pending and rejected users
- Prevention of unauthorized administrator actions
- Division-based user approval restrictions
- Same-division document downloads
- Cross-division download restrictions
- Pending and approved document access requests
- Document metadata editing permissions
- Missing authentication tokens
- API authorization and error handling

### Manual Testing

Additional manual tests were executed to verify the application.

| Test | Result |
|---|---|
| MongoDB Atlas connection | Passed |
| Document listing | Passed |
| Cross-division access restriction | Passed |
| Authorized document download | Passed |
| Document upload and text extraction | Passed |

The upload test returned HTTP `201 Created` and successfully extracted 4,720 characters from the test document.

The cross-division security test confirmed that an HR user attempting to download an unauthorized IT document received HTTP `403 Forbidden`.

The authorized download test returned HTTP `200 OK`.

### Test Report

The `test_report.txt` file contains the automated test execution results.

To regenerate it, run:

```powershell
python -m pytest tests/ -v 2>&1 | Tee-Object -FilePath test_report.txt
```

## Deployment

The backend includes a `Procfile` for compatible hosting environments.

For deployment:

1. Configure the MongoDB Atlas connection.
2. Set the required environment variables securely.
3. Install the Python dependencies.
4. Configure the backend startup command.
5. Update `frontend/config.js` with the deployed backend API URL.
6. Install Tesseract OCR on the hosting environment when scanned-document OCR is required.

Docker deployment is optional under the assignment requirements.

## Future Enhancements

Potential improvements include:

- Document version history
- Audit logs for document activities
- Bulk document uploads
- Advanced search filters
- Cloud-based deployment and monitoring

## Assignment Information

**Project:** Document Management System (DMS)

**Organization:** TRIAD AI

**Assignment:** Full Stack Developer Internship — Take-Home Assignment

**Submission Deliverables:**
- Complete source code
- Project README
- Automated test report
- GitHub repository link

---

Developed as part of the TRIAD AI Full Stack Developer Internship assignment.