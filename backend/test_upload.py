
import json
from pathlib import Path
import requests

BASE_URL = "http://127.0.0.1:5000"

# Enter your registered login details
email = input("Enter registered email: ")
password = input("Enter password: ")

# Login and get JWT token
login = requests.post(
    f"{BASE_URL}/api/auth/login",
    json={"email": email, "password": password},
    timeout=30
)

print("Login status:", login.status_code)

if login.status_code != 200:
    print("Login failed:", login.text)
    raise SystemExit(1)

token = login.json()["access_token"]

# Locate sample PDF
pdf_path = Path(__file__).resolve().parent.parent / "sample.pdf"

if not pdf_path.exists():
    print("sample.pdf not found!")
    raise SystemExit(1)

# Upload document
with open(pdf_path, "rb") as pdf:
    response = requests.post(
        f"{BASE_URL}/api/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("sample.pdf", pdf, "application/pdf")},
        data={
            "metadata": json.dumps({
                "category": "Reports",
                "year": 2026
            })
        },
        timeout=60
    )

print("Upload status:", response.status_code)
print("Response:", response.text)
