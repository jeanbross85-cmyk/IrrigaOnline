import hashlib, hmac, secrets
from fastapi import Request, HTTPException
from sqlalchemy import select
from .db import SessionLocal
from .models import User
ITERATIONS = 310_000
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), ITERATIONS).hex()
    return f"pbkdf2_sha256${ITERATIONS}${salt}${digest}"
def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, rounds, salt, expected = encoded.split("$")
        if scheme != "pbkdf2_sha256": return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(rounds)).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError): return False
def current_user(request: Request):
    uid = request.session.get("user_id")
    if not uid: return None
    with SessionLocal() as db:
        user = db.get(User, uid)
        if not user or not user.active: return None
        return {"id": user.id, "username": user.username}
def require_user(request: Request):
    user = current_user(request)
    if not user: raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user
def ensure_csrf(request: Request, token: str):
    expected = request.session.get("csrf_token", "")
    if not expected or not hmac.compare_digest(expected, token or ""):
        raise HTTPException(status_code=403, detail="Token de segurança inválido. Atualize a página e tente novamente.")
