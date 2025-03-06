import jwt
import time
import os
import requests

# Load environment variables (if not done yet)
from django.conf import settings

GITHUB_APP_ID = os.getenv("GITHUB_APP_ID")
GITHUB_PRIVATE_KEY_PATH = os.getenv("GITHUB_PRIVATE_KEY_PATH")

_cached_jwt = None  # Store the JWT
_cached_expiration = 0  # Store expiration timestamp

def generate_jwt():
    global _cached_jwt, _cached_expiration

    # If JWT is still valid, return cached version
    if _cached_jwt and time.time() < _cached_expiration:
        return _cached_jwt

    # Ensure absolute path for private key
    private_key_path = os.path.join(settings.PROJECT_ROOT, settings.GITHUB_PRIVATE_KEY_PATH)

    # should print:  /app/social/social-activity-fetcher.2025-03-05.private-key.pem
    print(f"Attempting to open the file at: {private_key_path}")

    with open(private_key_path, "r") as f:
        private_key = f.read()

    # Generate new JWT
    payload = {
        "iat": int(time.time()),  # Issued at
        "exp": int(time.time()) + 600,  # Expires in 10 min
        "iss": GITHUB_APP_ID,  # GitHub App ID
    }

    _cached_jwt = jwt.encode(payload, private_key, algorithm="RS256")
    print(f"Generated JWT: {_cached_jwt}")
    _cached_expiration = payload["exp"]  # Store expiration time

    return _cached_jwt

def get_installation_id(jwt_token):
    url = "https://api.github.com/app/installations"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {jwt_token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        installations = response.json()
        return installations[0]["id"]  # Assuming the app is installed at least once
    else:
        print(f"Error fetching installations: {response.status_code} - {response.text}")
        return None
    
def get_installation_token(jwt_token, installation_id):
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {jwt_token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    response = requests.post(url, headers=headers)
    if response.status_code == 201:
        return response.json()["token"]
    else:
        print(f"Error fetching installation token: {response.status_code} - {response.text}")
        return None

def fetch_user_activity(username):
    jwt_token = generate_jwt()
    installation_id = get_installation_id(jwt_token)
    if not installation_id:
        return None

    installation_token = get_installation_token(jwt_token, installation_id)
    if not installation_token:
        return None

    url = f"https://api.github.com/users/{username}/events/public"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {installation_token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }   

    response = requests.get(url, headers=headers)
    print(f"Response Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")

    if response.status_code == 200:
        data = response.json()
        if data:  # If there's any activity, return it, else return None
            return data
        else:
            print("No recent public activity.")
            return None
    else:
        print("Error: Could not fetch user activity.")
        return None

