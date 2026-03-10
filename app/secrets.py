import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken


def encrypt_secret(value: str, secret_key: str) -> str:
    fernet = _fernet(secret_key)
    return fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str, secret_key: str) -> str:
    fernet = _fernet(secret_key)
    try:
        return fernet.decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Unable to decrypt secret with current SECRET_KEY.") from exc


def _fernet(secret_key: str) -> Fernet:
    digest = hashlib.sha256(secret_key.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)
