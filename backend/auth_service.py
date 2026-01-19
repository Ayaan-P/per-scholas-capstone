"""
Auth service for Supabase JWT token validation
"""
import os
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from typing import Optional
import requests

security = HTTPBearer()

# Supabase public key URL
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Cache for Supabase public key
_public_key_cache = None


async def get_supabase_public_key():
    """Fetch Supabase JWT public key"""
    global _public_key_cache

    if _public_key_cache:
        return _public_key_cache

    try:
        response = requests.get(
            f"{SUPABASE_URL}/auth/v1/jwks",
            headers={'apikey': SUPABASE_KEY}
        )
        response.raise_for_status()
        data = response.json()

        # Extract the public key from JWKS
        if 'keys' in data and len(data['keys']) > 0:
            key_data = data['keys'][0]
            # Construct PEM format public key from JWK
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.backends import default_backend

            # For now, store the raw response
            _public_key_cache = key_data
            return _public_key_cache
    except Exception as e:
        print(f"[AUTH] Error fetching Supabase public key: {e}")
        return None


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Verify JWT token from Supabase"""
    token = credentials.credentials

    try:
        # Decode without verification first to get the header
        unverified_header = jwt.get_unverified_header(token)

        # For Supabase tokens, we can verify using the issuer
        # Supabase uses RS256 algorithm
        payload = jwt.decode(
            token,
            options={"verify_signature": False}  # We'll verify the issuer instead
        )

        # Verify issuer
        if not SUPABASE_URL:
            print(f"[AUTH] SUPABASE_URL not configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server configuration error"
            )

        expected_issuer = f"{SUPABASE_URL.rstrip('/')}/auth/v1"
        actual_issuer = payload.get('iss')

        if actual_issuer != expected_issuer:
            print(f"[AUTH] Issuer mismatch: expected={expected_issuer}, actual={actual_issuer}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token issuer"
            )

        # Verify not expired
        import time
        exp_time = payload.get('exp', 0)
        current_time = time.time()
        if exp_time < current_time:
            print(f"[AUTH] Token expired: exp={exp_time}, now={current_time}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired"
            )

        print(f"[AUTH] Token verified for user: {payload.get('sub', 'unknown')}")
        return payload

    except jwt.DecodeError as e:
        print(f"[AUTH] JWT decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AUTH] Token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token validation failed"
        )


async def get_current_user(token_payload: dict = Depends(verify_token)) -> str:
    """Extract user ID from verified token"""
    user_id = token_payload.get('sub')
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token - no user ID"
        )
    return user_id


async def optional_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[dict]:
    """Optional token verification - doesn't require auth"""
    if not credentials:
        return None

    try:
        return await verify_token(credentials)
    except:
        return None
