import hashlib


def hash_sha224(value: str):
    value_hash = hashlib.sha224(value.encode("utf-8")).hexdigest()
    return value_hash
