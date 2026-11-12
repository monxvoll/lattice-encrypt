"""ML-KEM-768 (FIPS 203) + AES-256-GCM, con la libreria cryptography.

ML-KEM no cifra texto: acuerda un secreto compartido. Con ese secreto se
deriva (HKDF-SHA256) una clave AES-256 y el mensaje se cifra con AES-GCM,
que ademas detecta cualquier alteracion del criptograma.
"""
import os

from core.errores import LatticeError, LatticeValueError

from cryptography.exceptions import InvalidTag, UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

try:
    from cryptography.hazmat.primitives.asymmetric import mlkem as _mlkem
except ImportError:  # cryptography < 50: sin ML-KEM
    _mlkem = None

INFO_HKDF = b"LatticeEncrypt ML-KEM-768 AES-256-GCM"
BYTES_NONCE = 12

_NO_DISPONIBLE = "ML-KEM no esta disponible en esta instalacion de cryptography (se requiere 50.0.2)"
_ERROR_DESCIFRADO = "No se pudo descifrar: clave incorrecta o criptograma alterado"


def disponible():
    return _mlkem is not None


def _clave_aes(secreto):
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=INFO_HKDF).derive(secreto)


def generar_claves():
    """Devuelve (clave_publica, clave_privada) de ML-KEM-768."""
    if not disponible():
        raise LatticeError(_NO_DISPONIBLE)
    try:
        privada = _mlkem.MLKEM768PrivateKey.generate()
    except UnsupportedAlgorithm:
        raise LatticeError(_NO_DISPONIBLE) from None
    return privada.public_key(), privada


def cifrar_texto(publica, texto):
    """Devuelve (ct_kem, nonce, ct_aes)."""
    secreto, ct_kem = publica.encapsulate()
    nonce = os.urandom(BYTES_NONCE)
    ct_aes = AESGCM(_clave_aes(secreto)).encrypt(nonce, texto.encode("utf-8"), None)
    return ct_kem, nonce, ct_aes


def descifrar_texto(privada, datos):
    ct_kem, nonce, ct_aes = datos
    try:
        secreto = privada.decapsulate(ct_kem)
        claro = AESGCM(_clave_aes(secreto)).decrypt(nonce, ct_aes, None)
        return claro.decode("utf-8")
    except (InvalidTag, ValueError):
        raise LatticeValueError(_ERROR_DESCIFRADO) from None
