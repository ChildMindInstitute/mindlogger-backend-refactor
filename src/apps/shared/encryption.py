from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from config import settings


def generate_iv(unique_identifier: str, output_length=16) -> bytes:
    cipher = Cipher(
        algorithms.AES(settings.secrets.key), modes.CFB(settings.secrets.iv)
    )
    encryptor = cipher.encryptor()
    return (
        encryptor.update(unique_identifier.encode()) + encryptor.finalize()
    )[:output_length]


def encrypt(
    value: bytes,
    key: bytes = settings.secrets.key,
    iv: bytes = settings.secrets.iv,
) -> bytes:
    cipher = Cipher(algorithms.AES(key), modes.CTR(iv))
    encryptor = cipher.encryptor()
    ct = encryptor.update(value) + encryptor.finalize()
    return ct


def decrypt(
    value: bytes,
    key: bytes = settings.secrets.key,
    iv: bytes = settings.secrets.iv,
) -> bytes:
    cipher = Cipher(algorithms.AES(key), modes.CTR(iv))
    decryptor = cipher.decryptor()
    ct = decryptor.update(value) + decryptor.finalize()
    return ct
