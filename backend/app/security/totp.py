"""RFC 6238 TOTP (SHA-1, 30 s, 6 digits) for MFA. No third-party dependency."""
import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote


def new_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def code(secret: str, at: float | None = None, step: int = 30, digits: int = 6) -> str:
    key = base64.b32decode(secret + "=" * (-len(secret) % 8), casefold=True)
    counter = int((at if at is not None else time.time()) // step)
    mac = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    off = mac[-1] & 0x0F
    num = (struct.unpack(">I", mac[off:off + 4])[0] & 0x7FFFFFFF) % (10 ** digits)
    return str(num).zfill(digits)


def verify(secret: str, supplied: str, window: int = 1, at: float | None = None) -> bool:
    now = at if at is not None else time.time()
    return any(hmac.compare_digest(code(secret, now + d * 30), supplied.strip()) for d in range(-window, window + 1))


def uri(secret: str, account: str, issuer: str = "CloudPulse AI") -> str:
    return f"otpauth://totp/{quote(issuer)}:{quote(account)}?secret={secret}&issuer={quote(issuer)}"
