import hashlib
import os
import uuid

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.utils import int_to_bytes

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


def get_key() -> bytes:
    return settings.secrets.key


def generate_dh_user_private_key(
    user_id: uuid.UUID, email: str, password: str
) -> list:
    key1 = hashlib.sha512((password + email).encode()).digest()
    key2 = hashlib.sha512((str(user_id) + email).encode()).digest()

    return list(key1 + key2)


def generate_dh_public_key(private_key: list, prime: list, base: list) -> list:
    p = int.from_bytes(bytes(prime), "big")
    g = int.from_bytes(bytes(base), "big")
    a = int.from_bytes(bytes(private_key), "big")

    key = int_to_bytes(pow(g, a, p))

    return list(key)


def generate_dh_aes_key(
    private_key: list, public_key: list, prime: list
) -> list:
    p = int.from_bytes(bytes(prime), "big")
    a = int.from_bytes(bytes(private_key), "big")
    b = int.from_bytes(bytes(public_key), "big")

    shared_key = pow(b, a, p)

    key = hashlib.sha256(int_to_bytes(shared_key)).digest()
    return list(key)


def encrypt_cbc(
    key: bytes, data: bytes, iv: bytes | None = None
) -> tuple[bytes, bytes]:
    """

    @param key: AES key
    @param data: data to encrypt
    @param iv: vector. Random bytes if not set
    @return: encrypted bytes, iv
    """
    if not iv:
        iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()

    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(data) + padder.finalize()

    ct = encryptor.update(padded_data) + encryptor.finalize()

    return ct, iv


def decrypt_cbc(key: bytes, data: bytes, iv: bytes) -> bytes:
    cipher = Cipher(algorithms.AES(bytes(key)), modes.CBC(iv))
    decryptor = cipher.decryptor()
    decrypted = decryptor.update(data) + decryptor.finalize()

    unpadder = padding.PKCS7(128).unpadder()
    decrypted = unpadder.update(decrypted) + unpadder.finalize()

    return decrypted
