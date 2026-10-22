from cryptography.fernet import Fernet
from app.core import security
from app.core.config import get_settings


def test_vault_roundtrip(monkeypatch):
    monkeypatch.setattr(get_settings(), "fernet_key", Fernet.generate_key().decode())
    token = security.encrypt('{"aws_secret":"x"}')
    assert token != '{"aws_secret":"x"}' and security.decrypt(token) == '{"aws_secret":"x"}'


def test_password_and_chain():
    h = security.hash_password("pw")
    assert security.verify_password("pw", h) and not security.verify_password("no", h)
    a = security.chain_hash("0" * 64, {"x": 1})
    assert a != security.chain_hash("0" * 64, {"x": 2})
