"""Tabla de simbolos: las variables que el programa va definiendo.

Un Entorno vive lo que dura un programa del editor, un archivo .le o una
sesion de consola; quien ejecuta decide cuando crear uno nuevo.
"""
from core.errores import LatticeNameError


class Entorno:
    def __init__(self):
        self._valores = {}

    def definir(self, nombre, valor):
        self._valores[nombre] = valor

    def obtener(self, nombre):
        if nombre not in self._valores:
            raise LatticeNameError(f"Variable no definida: {nombre}")
        return self._valores[nombre]

    def existe(self, nombre):
        return nombre in self._valores
