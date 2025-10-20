#!/usr/bin/env python3
"""
Setup Claude Code authentication on server using environment variables.
This script creates the credentials file that Claude Code CLI expects.
"""
import os
import json
from pathlib import Path

def setup_claude_credentials():
    """
    Create Claude Code credentials file from environment variables.
    Must be run before using Claude Code CLI on the server.
    """
    access_token = os.getenv('CLAUDE_ACCESS_TOKEN')
    refresh_token = os.getenv('CLAUDE_REFRESH_TOKEN')

    if not access_token or not refresh_token:
        raise ValueError(
            "Missing credentials! Set CLAUDE_ACCESS_TOKEN and CLAUDE_REFRESH_TOKEN "
            "environment variables on your Render service."
        )

    # Claude Code stores credentials in ~/.claude/.credentials.json
    claude_dir = Path.home() / '.claude'
    claude_dir.mkdir(exist_ok=True)

    credentials_file = claude_dir / '.credentials.json'

    credentials = {
        "claudeAiOauth": {
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "expiresAt": 1760995500077,  # Will be refreshed automatically by Claude CLI
            "scopes": ["user:inference", "user:profile"],
            "subscriptionType": "pro"
        }
    }

    # Write credentials file with restricted permissions
    credentials_file.write_text(json.dumps(credentials))
    credentials_file.chmod(0o600)  # Read/write for owner only

    print(f"✓ Claude Code credentials configured at {credentials_file}")
    return True

if __name__ == "__main__":
    setup_claude_credentials()
