"""Jerarquia de excepciones del lenguaje Lattice Encrypt.

Cada clase hereda de LatticeError y ademas del builtin de Python
correspondiente. Esa herencia multiple es deliberada: permite que el codigo
existente que captura SyntaxError, TypeError o ZeroDivisionError siga
funcionando sin cambios, y a la vez permite distinguir un error del lenguaje
de un fallo real de Python captured por except Exception.
"""


class LatticeError(Exception):
    """Excepcion base para cualquier error del lenguaje Lattice."""


class LatticeSyntaxError(LatticeError, SyntaxError):
    """Error de lexico o de sintaxis: token inesperado, cadena sin cerrar, etc."""


class LatticeTypeError(LatticeError, TypeError):
    """Operacion aplicada a operandos de tipos incompatibles."""


class LatticeValueError(LatticeError, ValueError):
    """Operacion con un valor fuera del dominio permitido por la regla."""


class LatticeDivisionError(LatticeError, ZeroDivisionError):
    """Modulo o division por cero."""
