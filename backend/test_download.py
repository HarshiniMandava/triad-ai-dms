
from pathlib import Path
import requests

BASE_URL = "http://127.0.0.1:5000"

print("=== DOCUMENT DOWNLOAD TEST ===")

email = input("Enter registered email: ").strip()
password = input("Enter password: ")

# Login
login = requests.post(
    f"{BASE_URL}/api/auth/login",
    json={"email": email, "password": password},
    timeout=30
)

if login.status_code != 200:
    print("Login failed:", login.text)
    raise SystemExit(1)

token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

print("Login successful!")

# Get available documents
response = requests.get(
    f"{BASE_URL}/api/documents",
    headers=headers,
    timeout=30
)

if response.status_code != 200:
    print("Listing failed:", response.text)
    raise SystemExit(1)

documents = response.json().get("documents", [])

if not documents:
    print("No documents available to download.")
    raise SystemExit(1)

# Choose the uploaded sample PDF
document = next(
    (doc for doc in documents if doc["filename"] == "sample.pdf"),
    None
)

if document is None:
    print("sample.pdf not found in document list.")
    raise SystemExit(1)

document_id = document["document_id"]

# Download the document
download = requests.get(
    f"{BASE_URL}/api/documents/{document_id}/download",
    headers=headers,
    timeout=60
)

print("Download status:", download.status_code)

if download.status_code != 200:
    print("Download failed:", download.text)
    raise SystemExit(1)

# Save downloaded PDF
output_path = (
    Path(__file__).resolve().parent.parent
    / "downloaded_sample.pdf"
)

output_path.write_bytes(download.content)

print("Document downloaded successfully!")
print("Saved at:", output_path)
print("File size:", output_path.stat().st_size, "bytes")
