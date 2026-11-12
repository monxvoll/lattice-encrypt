"""FrodoPKE-640: el LWE implementado en el proyecto."""
import os
import time

import numpy as np
import pytest

from core.cripto import frodo
from core.cripto.frodo import B, N, NBAR, Q, TABLA_CDF
from core.errores import LatticeValueError


def test_parametros():
    assert N == 640 and Q == 2**15 and NBAR == 8 and B == 2
    assert TABLA_CDF == (4643, 13363, 20579, 25843, 29227, 31145, 32103,
                         32525, 32689, 32745, 32762, 32766, 32767)


def test_distribucion_error():
    x = frodo.muestrear_error(400, 250)
    assert x.shape == (400, 250)
    assert abs(x.mean()) < 0.05
    assert abs(x.var() - 2.8**2) < 0.35
    assert np.abs(x).max() <= 12


def test_bloque_ida_y_vuelta():
    publica, privada = frodo.generar_claves()
    for _ in range(20):
        bloque = os.urandom(16)
        c1, c2 = frodo.cifrar_bloque(publica, bloque)
        assert frodo.descifrar_bloque(privada, c1, c2) == bloque


@pytest.mark.parametrize("texto", ["", "HOLA", "Hola mundo, ñandú y acción", "x" * 100])
def test_texto_ida_y_vuelta(texto):
    publica, privada = frodo.generar_claves()
    assert frodo.descifrar_texto(privada, frodo.cifrar_texto(publica, texto)) == texto


def test_cifrado_aleatorio():
    publica, _ = frodo.generar_claves()
    a = frodo.cifrar_texto(publica, "HOLA")
    b = frodo.cifrar_texto(publica, "HOLA")
    assert not np.array_equal(a[0][1], b[0][1])


def test_clave_incorrecta():
    publica, _ = frodo.generar_claves()
    for _ in range(5):
        _, otra = frodo.generar_claves()
        bloques = frodo.cifrar_texto(publica, "secreto")
        try:
            assert frodo.descifrar_texto(otra, bloques) != "secreto"
        except LatticeValueError:
            pass


def test_rapidez():
    inicio = time.perf_counter()
    publica, privada = frodo.generar_claves()
    frodo.descifrar_texto(privada, frodo.cifrar_texto(publica, "HOLA"))
    assert time.perf_counter() - inicio < 1.0
