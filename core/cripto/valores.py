"""Valores del lenguaje para el cifrado: un par de claves y un criptograma.

Su repr es un resumen: al imprimir o al devolverlos por la API nunca se
muestra el material de clave (son miles de numeros, y la privada es secreta).
"""
from dataclasses import dataclass

LWE = "LWE"
MLKEM = "ML-KEM"

_NOMBRE = {LWE: "LWE FrodoPKE-640", MLKEM: "ML-KEM-768"}


@dataclass(frozen=True, eq=False, repr=False)
class ParClaves:
    modo: str
    publica: object
    privada: object

    def __repr__(self):
        return f"<CLAVES {_NOMBRE[self.modo]}>"


@dataclass(frozen=True, eq=False, repr=False)
class Cifrado:
    modo: str
    datos: object
    tamano: int  # bytes

    def __repr__(self):
        kb = self.tamano / 1024
        if self.modo == LWE:
            n = len(self.datos)
            return f"<CIFRADO {_NOMBRE[LWE]}, {n} bloque{'s' if n != 1 else ''}, {kb:.1f} KB>"
        return f"<CIFRADO {_NOMBRE[MLKEM]}, {kb:.1f} KB>"
