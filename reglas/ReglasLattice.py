"""KEYGEN, CIFRAR y DESCIFRAR: cifrado post-cuantico basado en reticulos.

Dos modos:
  * LWE    (por defecto): FrodoPKE-640, implementado en core/cripto/frodo.py.
  * MLKEM: ML-KEM-768 (FIPS 203) + AES-256-GCM, via la libreria cryptography.

CIFRAR usa solo la parte publica de la clave y DESCIFRAR solo la privada.
"""
from core.cripto import frodo, mlkem
from core.cripto.valores import LWE, MLKEM, Cifrado, ParClaves
from core.errores import LatticeTypeError, LatticeValueError


def generar_claves(modo):
    """modo: "LWE" o "MLKEM" (como se escribe en el lenguaje)."""
    if modo == "LWE":
        publica, privada = frodo.generar_claves()
        return ParClaves(LWE, publica, privada)
    if modo == "MLKEM":
        publica, privada = mlkem.generar_claves()
        return ParClaves(MLKEM, publica, privada)
    raise LatticeValueError(f"Modo de KEYGEN desconocido: {modo}")


def _cifrar(texto, claves):
    if claves.modo == LWE:
        bloques = frodo.cifrar_texto(claves.publica, texto)
        tamano = sum((c1.size + c2.size) * 2 for c1, c2 in bloques)
        return Cifrado(LWE, bloques, tamano)
    datos = mlkem.cifrar_texto(claves.publica, texto)
    return Cifrado(MLKEM, datos, sum(len(d) for d in datos))


def _descifrar(cifrado, claves):
    if cifrado.modo != claves.modo:
        raise LatticeTypeError(
            f"El criptograma es {cifrado.modo} pero las claves son {claves.modo}"
        )
    if claves.modo == LWE:
        return frodo.descifrar_texto(claves.privada, cifrado.datos)
    return mlkem.descifrar_texto(claves.privada, cifrado.datos)


def revisarSintaxisLattice(sintactico, lado_izquierdo, operador):
    """Maneja CIFRAR y DESCIFRAR: <operando> CIFRAR|DESCIFRAR <claves>."""
    claves = sintactico.parsear_operando()
    if not isinstance(claves, ParClaves):
        raise LatticeTypeError(f"{operador} requiere unas claves generadas con KEYGEN a la derecha")

    if operador == "CIFRAR":
        if not isinstance(lado_izquierdo, str):
            raise LatticeTypeError('CIFRAR requiere un texto: TEXTO "..." CIFRAR CLAVES')
        return _cifrar(lado_izquierdo, claves)

    if operador == "DESCIFRAR":
        if not isinstance(lado_izquierdo, Cifrado):
            raise LatticeTypeError("DESCIFRAR requiere un criptograma producido por CIFRAR")
        return _descifrar(lado_izquierdo, claves)
