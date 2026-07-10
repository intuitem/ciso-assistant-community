"""Fernet encryption for workflow secrets.

The key is derived from SECRET_KEY (nothing else in the codebase encrypts at
rest, so there is no shared key infrastructure to reuse). A dedicated
WORKFLOWS_ENCRYPTION_KEY env var overrides the derivation so deployments can
rotate SECRET_KEY without losing stored secrets.
"""

import base64
import hashlib
import os
from functools import lru_cache

from cryptography.fernet import Fernet
from django.conf import settings


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    material = os.environ.get("WORKFLOWS_ENCRYPTION_KEY") or settings.SECRET_KEY
    key = base64.urlsafe_b64encode(hashlib.sha256(material.encode()).digest())
    return Fernet(key)


def encrypt_secret(value: str) -> bytes:
    return _fernet().encrypt(value.encode())


def decrypt_secret(token: bytes) -> str:
    return _fernet().decrypt(token).decode()
