"""ML-KEM-768 + AES-256-GCM a traves de la libreria cryptography."""
from core.cripto import mlkem
from core.errores import LatticeValueError

import pytest


def _invertir_bit(datos):
    return bytes([datos[0] ^ 1]) + datos[1:]


@pytest.mark.parametrize("texto", ["Hola ñ", ""])
def test_ida_y_vuelta(texto):
    publica, privada = mlkem.generar_claves()
    assert mlkem.descifrar_texto(privada, mlkem.cifrar_texto(publica, texto)) == texto


def test_cifrado_aleatorio():
    publica, _ = mlkem.generar_claves()
    assert mlkem.cifrar_texto(publica, "a")[0] != mlkem.cifrar_texto(publica, "a")[0]


def test_clave_incorrecta():
    publica, _ = mlkem.generar_claves()
    _, otra = mlkem.generar_claves()
    with pytest.raises(LatticeValueError):
        mlkem.descifrar_texto(otra, mlkem.cifrar_texto(publica, "secreto"))


def test_criptograma_alterado():
    publica, privada = mlkem.generar_claves()
    ct_kem, nonce, ct_aes = mlkem.cifrar_texto(publica, "secreto")
    with pytest.raises(LatticeValueError):
        mlkem.descifrar_texto(privada, (ct_kem, nonce, _invertir_bit(ct_aes)))


def test_kem_alterado():
    publica, privada = mlkem.generar_claves()
    ct_kem, nonce, ct_aes = mlkem.cifrar_texto(publica, "secreto")
    with pytest.raises(LatticeValueError):
        mlkem.descifrar_texto(privada, (_invertir_bit(ct_kem), nonce, ct_aes))
