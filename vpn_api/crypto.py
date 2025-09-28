from __future__ import annotations

import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken


def _get_fernet() -> Fernet:
    key = os.getenv("CONFIG_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("CONFIG_ENCRYPTION_KEY is not set")
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_text(plaintext: str) -> str:
    f = _get_fernet()
    token = f.encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_text(token: str) -> Optional[str]:
    try:
        f = _get_fernet()
        data = f.decrypt(token.encode("utf-8"))
        return data.decode("utf-8")
    except (InvalidToken, Exception):
        return None
