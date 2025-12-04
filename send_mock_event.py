import requests
import hmac
import hashlib
import json
import os
from dotenv import load_dotenv

load_dotenv()

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "your_webhook_secret")
URL = "http://localhost:8000/webhook"

payload = {
    "action": "opened",
    "pull_request": {
        "number": 1,
        "title": "Test PR",
        "body": "This is a test PR.",
        "changed_files": 1,
        "additions": 10,
        "deletions": 5
    },
    "repository": {
        "full_name": "owner/repo"
    },
    "installation": {
        "id": 123456
    }
}

body = json.dumps(payload).encode()
signature = "sha256=" + hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()

headers = {
    "X-GitHub-Event": "pull_request",
    "X-Hub-Signature-256": signature,
    "Content-Type": "application/json"
}

try:
    response = requests.post(URL, data=body, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")
