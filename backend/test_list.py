
import requests
import json

BASE_URL = "http://127.0.0.1:5000"

print("=== TRIAD AI Document Listing Test ===")

# Step 1: Login
email = input("Enter registered email: ").strip()
password = input("Enter password: ")

login_response = requests.post(
    f"{BASE_URL}/api/auth/login",
    json={
        "email": email,
        "password": password
    },
    timeout=30
)

print("Login status:", login_response.status_code)

if login_response.status_code != 200:
    print("Login failed:", login_response.text)
    raise SystemExit(1)

token = login_response.json()["access_token"]

print("Login successful!")

# Step 2: Fetch documents
response = requests.get(
    f"{BASE_URL}/api/documents",
    headers={
        "Authorization": f"Bearer {token}"
    },
    timeout=30
)

print("Document listing status:", response.status_code)

if response.status_code != 200:
    print("Error:", response.text)
    raise SystemExit(1)

# Step 3: Display documents
data = response.json()

print("\n=== DOCUMENT LIST ===")
print(json.dumps(data, indent=4))

print("\nTotal documents:", data.get("count", 0))

for document in data.get("documents", []):
    print("------------------------")
    print("Document ID:", document["document_id"])
    print("Filename:", document["filename"])
    print("Division:", document["division"])
    print("Metadata:", document.get("metadata", {}))

print("\nDocument listing test completed!")
