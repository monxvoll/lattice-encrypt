"""FrodoPKE-640: cifrado de clave publica basado en LWE "puro" (con matrices).

Es la parte PKE de FrodoKEM con los parametros de FrodoKEM-640 (nivel 1 de
NIST, unos 128 bits de seguridad post-cuantica segun su analisis publicado).
Seguridad IND-CPA: protege contra quien escucha, no contra quien altera
criptogramas (no se aplica la transformacion Fujisaki-Okamoto de FrodoKEM).

    KeyGen:  A uniforme en Z_q^{n x n};  S, E <- chi^{n x nbar};  B = A S + E
    Enc(mu): S', E' <- chi^{mbar x n};  E'' <- chi^{mbar x nbar}
             B' = S' A + E';  V = S' B + E'';  C = V + Codificar(mu)
    Dec:     M = C - B' S;  mu = Decodificar(M)

Toda la aleatoriedad sale de os.urandom.
"""
import os

import numpy as np

from core.errores import LatticeValueError

N = 640
Q = 2 ** 15
NBAR = 8
B = 2                      # bits por entrada de la matriz de mensaje
BYTES_BLOQUE = 16          # NBAR * NBAR * B / 8

# Distribucion de error chi de FrodoKEM-640 (sigma = 2.8), tal cual la define
# la implementacion de referencia:
# https://github.com/microsoft/PQCrypto-LWEKE/blob/master/FrodoKEM/src/frodo640.c
TABLA_CDF = (4643, 13363, 20579, 25843, 29227, 31145, 32103,
             32525, 32689, 32745, 32762, 32766, 32767)

_MASCARA = Q - 1
_UMBRALES = np.array(TABLA_CDF[:-1], dtype=np.int64)


def _aleatorios_16_bits(cantidad):
    return np.frombuffer(os.urandom(2 * cantidad), dtype="<u2").astype(np.int64)


def muestrear_error(filas, cols):
    """Muestras de chi por inversion de la CDF, como frodo_sample_n (noise.c).

    Por cada muestra: el bit bajo es el signo y los 15 restantes se comparan
    contra la tabla; el valor es cuantos umbrales supera.
    """
    r = _aleatorios_16_bits(filas * cols)
    signo = r & 1
    p = r >> 1
    magnitud = (p[:, None] > _UMBRALES[None, :]).sum(axis=1)
    return np.where(signo == 1, -magnitud, magnitud).reshape(filas, cols)


def generar_claves():
    """Devuelve ((A, B), S): clave publica y clave privada."""
    a = (_aleatorios_16_bits(N * N) & _MASCARA).reshape(N, N)
    s = muestrear_error(N, NBAR)
    e = muestrear_error(N, NBAR)
    b = (a @ s + e) & _MASCARA
    return (a, b), s


def _codificar(bloque):
    """16 bytes -> matriz 8x8 de valores de 2 bits escalados a k * q/4."""
    bits = np.unpackbits(np.frombuffer(bloque, dtype=np.uint8), bitorder="little")
    valores = bits[0::2].astype(np.int64) + 2 * bits[1::2].astype(np.int64)
    return valores.reshape(NBAR, NBAR) * (Q // 2 ** B)


def _decodificar(m):
    """Redondea cada entrada al multiplo de q/4 mas cercano y rearma los bytes."""
    k = ((m * 2 ** B + Q // 2) // Q) % 2 ** B
    k = k.reshape(-1)
    bits = np.empty(k.size * 2, dtype=np.uint8)
    bits[0::2] = k & 1
    bits[1::2] = k >> 1
    return np.packbits(bits, bitorder="little").tobytes()


def cifrar_bloque(publica, bloque):
    """Cifra exactamente 16 bytes. Devuelve (C1, C2) = (B', C)."""
    if len(bloque) != BYTES_BLOQUE:
        raise LatticeValueError(f"Un bloque LWE debe tener {BYTES_BLOQUE} bytes")
    a, b = publica
    s1 = muestrear_error(NBAR, N)
    e1 = muestrear_error(NBAR, N)
    e2 = muestrear_error(NBAR, NBAR)
    c1 = (s1 @ a + e1) & _MASCARA
    v = s1 @ b + e2
    c2 = (v + _codificar(bloque)) & _MASCARA
    return c1, c2


def descifrar_bloque(privada, c1, c2):
    m = (c2 - c1 @ privada) & _MASCARA
    return _decodificar(m)


def cifrar_texto(publica, texto):
    """Texto UTF-8 de cualquier longitud -> lista de bloques cifrados.

    Formato: longitud en 4 bytes big-endian + UTF-8, con ceros hasta un
    multiplo de 16. Cada bloque usa aleatoriedad nueva.
    """
    datos = texto.encode("utf-8")
    datos = len(datos).to_bytes(4, "big") + datos
    datos += b"\x00" * (-len(datos) % BYTES_BLOQUE)
    return [
        cifrar_bloque(publica, datos[i:i + BYTES_BLOQUE])
        for i in range(0, len(datos), BYTES_BLOQUE)
    ]


def descifrar_texto(privada, bloques):
    error = LatticeValueError("No se pudo descifrar: clave incorrecta o criptograma alterado")
    datos = b"".join(descifrar_bloque(privada, c1, c2) for c1, c2 in bloques)
    if len(datos) < 4:
        raise error
    longitud = int.from_bytes(datos[:4], "big")
    if 4 + longitud > len(datos) or any(datos[4 + longitud:]):
        raise error
    try:
        return datos[4:4 + longitud].decode("utf-8")
    except UnicodeDecodeError:
        raise error from None
