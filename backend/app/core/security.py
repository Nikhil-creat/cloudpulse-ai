"""Vault encryption (Fernet), password hashing, JWT + RBAC, audit hash chain."""
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from app.core.config import get_settings

ROLE_RANK = {"viewer": 1, "operator": 2, "admin": 3}


def _fernet() -> Fernet:
    key = get_settings().fernet_key
    if not key:
        raise RuntimeError("FERNET_KEY is not set")
    return Fernet(key.encode())


def encrypt(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"{salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    salt_hex, dk_hex = stored.split("$")
    dk = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
    return hmac.compare_digest(dk.hex(), dk_hex)


def create_token(sub: str, role: str) -> str:
    s = get_settings()
    exp = datetime.now(timezone.utc) + timedelta(minutes=s.jwt_ttl_minutes)
    return jwt.encode({"sub": sub, "role": role, "exp": exp}, s.jwt_secret, algorithm=s.jwt_alg)


class Principal(BaseModel):
    sub: str
    role: str


oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def principal_from_token(token: str) -> Principal:
    s = get_settings()
    try:
        data = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_alg])
        return Principal(sub=data["sub"], role=data["role"])
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")


async def current_principal(token: str = Depends(oauth2)) -> Principal:
    return principal_from_token(token)


def require_role(minimum: str):
    async def dep(p: Principal = Depends(current_principal)) -> Principal:
        if ROLE_RANK.get(p.role, 0) < ROLE_RANK[minimum]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires role: {minimum}")
        return p
    return dep

from app.security.audit_chain import chain_hash  # noqa: E402,F401  (re-export)
