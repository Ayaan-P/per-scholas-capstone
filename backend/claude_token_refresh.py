#!/usr/bin/env python3
"""
Token refresh utility for Claude Code on server.
Handles OAuth token refresh when access tokens expire.
"""
import os
import json
import requests
from pathlib import Path
import time

def refresh_claude_token():
    """
    Refresh Claude OAuth access token using refresh token.
    Updates the credentials file with new tokens.

    Returns:
        bool: True if refresh successful, False otherwise
    """
    credentials_file = Path.home() / '.claude' / '.credentials.json'

    if not credentials_file.exists():
        print("[TOKEN REFRESH] Credentials file not found")
        return False

    # Read current credentials
    with open(credentials_file, 'r') as f:
        credentials = json.load(f)

    refresh_token = credentials.get('claudeAiOauth', {}).get('refreshToken')

    if not refresh_token:
        print("[TOKEN REFRESH] No refresh token found")
        return False

    print(f"[TOKEN REFRESH] Attempting to refresh token...")

    # Anthropic OAuth token refresh endpoint
    # Note: This is the standard OAuth2 flow, but Anthropic's exact endpoint might differ
    try:
        response = requests.post(
            'https://api.anthropic.com/v1/oauth/token',
            headers={
                'Content-Type': 'application/json',
            },
            json={
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token
            },
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            new_access_token = data.get('access_token')
            new_refresh_token = data.get('refresh_token', refresh_token)  # Use old if not provided
            expires_in = data.get('expires_in', 86400)  # Default 24 hours

            # Update credentials
            credentials['claudeAiOauth']['accessToken'] = new_access_token
            credentials['claudeAiOauth']['refreshToken'] = new_refresh_token
            credentials['claudeAiOauth']['expiresAt'] = int((time.time() + expires_in) * 1000)

            # Write updated credentials
            with open(credentials_file, 'w') as f:
                json.dump(credentials, f)

            credentials_file.chmod(0o600)

            print(f"[TOKEN REFRESH] ✓ Token refreshed successfully")
            print(f"[TOKEN REFRESH]   New access token: {new_access_token[:20]}...")
            print(f"[TOKEN REFRESH]   Expires in: {expires_in} seconds")

            # Also update environment variables for next restart
            os.environ['CLAUDE_ACCESS_TOKEN'] = new_access_token
            os.environ['CLAUDE_REFRESH_TOKEN'] = new_refresh_token

            return True
        else:
            print(f"[TOKEN REFRESH] ✗ Refresh failed: {response.status_code}")
            print(f"[TOKEN REFRESH]   Response: {response.text}")
            return False

    except Exception as e:
        print(f"[TOKEN REFRESH] ✗ Error during refresh: {e}")
        return False

if __name__ == "__main__":
    success = refresh_claude_token()
    exit(0 if success else 1)
