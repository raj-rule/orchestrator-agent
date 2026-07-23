import os
import hmac
import hashlib
import secrets
from typing import Optional
from fastapi import HTTPException

# ponytail: persist secret to disk so sessions survive backend restarts
_SECRET_FILE = os.path.join(os.path.dirname(__file__), ".session_secret")
if os.path.exists(_SECRET_FILE):
    with open(_SECRET_FILE, "r") as f:
        SESSION_SECRET = f.read().strip()
else:
    SESSION_SECRET = os.getenv("CRITICAI_SESSION_SECRET") or secrets.token_hex(32)
    with open(_SECRET_FILE, "w") as f:
        f.write(SESSION_SECRET)
SESSION_SECRET_BYTES = SESSION_SECRET.encode("utf-8")

BACKEND_TOKEN = os.getenv("CRITICAI_BACKEND_TOKEN")

def sign_session_id(session_id: str) -> str:
    """Signs a raw session ID using HMAC-SHA256."""
    signature = hmac.new(SESSION_SECRET_BYTES, session_id.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{session_id}.{signature}"

def verify_session_id(signed_session_id: str) -> Optional[str]:
    """
    Verifies the signature of a signed session ID.
    Returns the raw session ID if valid, or None if invalid/tampered.
    """
    try:
        if not signed_session_id or "." not in signed_session_id:
            return None
        session_id, signature = signed_session_id.rsplit(".", 1)
        expected_signature = hmac.new(SESSION_SECRET_BYTES, session_id.encode("utf-8"), hashlib.sha256).hexdigest()
        if hmac.compare_digest(signature, expected_signature):
            return session_id
    except Exception:
        pass
    return None

def check_backend_token(token: Optional[str]) -> None:
    """
    Validates the provided backend access token against CRITICAI_BACKEND_TOKEN.
    If the backend token is not configured in env, validation is bypassed.
    """
    if BACKEND_TOKEN:
        if not token or not hmac.compare_digest(token, BACKEND_TOKEN):
            raise HTTPException(status_code=401, detail="Unauthorized: Invalid Backend Access Token")
