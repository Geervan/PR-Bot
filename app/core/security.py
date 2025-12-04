import time
import jwt
import requests
from app.core.config import settings


def get_jwt():
    """Generates a JWT for the GitHub App."""
    private_key = settings.private_key_content
    
    if not private_key:
        raise ValueError("No private key configured. Set PRIVATE_KEY or PRIVATE_KEY_PATH.")
    
    payload = {
        'iat': int(time.time()),
        'exp': int(time.time()) + (10 * 60),
        'iss': settings.APP_ID
    }
    
    encoded_jwt = jwt.encode(payload, private_key, algorithm='RS256')
    return encoded_jwt

def get_installation_access_token(installation_id: int):
    """Fetches an installation access token."""
    jwt_token = get_jwt()
    headers = {
        'Authorization': f'Bearer {jwt_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    url = f'https://api.github.com/app/installations/{installation_id}/access_tokens'
    response = requests.post(url, headers=headers)
    response.raise_for_status()
    return response.json()['token']
