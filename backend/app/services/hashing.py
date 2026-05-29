import hashlib


def content_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
