
import requests
import getpass

BASE_URL = "http://127.0.0.1:5000"

print("=== DIVISION ACCESS SECURITY TEST ===")

email = input("Enter HR employee email: ")
password = getpass.getpass("Enter HR employee password: ")

# Login as HR employee
login_response = requests.post(
    f"{BASE_URL}/api/auth/login",
    json={"email": email, "password": password},
    timeout=15
)

print("Login status:", login_response.status_code)

if login_response.status_code != 200:
    print("Login failed:", login_response.text)
    raise SystemExit(1)

login_data = login_response.json()
token = login_data.get("access_token") or login_data.get("token")

if not token:
    print("Login response did not contain a token.")
    raise SystemExit(1)

print("Logged-in division:", login_data.get("division"))

if login_data.get("division", "").upper() != "HR":
    print("Please use an HR employee account for this test.")
    raise SystemExit(1)

headers = {"Authorization": f"Bearer {token}"}

# Use the IT document ID from our successful upload
document_id = "6afa0407e4729815b1b39d12"

download_response = requests.get(
    f"{BASE_URL}/api/documents/{document_id}/download",
    headers=headers,
    timeout=30
)

print("Download status:", download_response.status_code)

if download_response.status_code == 403:
    print("TEST PASSED: HR employee cannot download the IT document.")
elif download_response.status_code == 200:
    print("TEST FAILED: HR employee was allowed to download the document.")
elif download_response.status_code == 404:
    print("Document not found. Check the document ID.")
else:
    print("Unexpected response:", download_response.text)
