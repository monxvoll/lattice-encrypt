"""Utilidades numericas compartidas por las reglas del lenguaje."""
import math


def redondear_lattice(x):
    """Redondea al entero mas cercano, con los empates hacia fuera del cero.

    Python usa round() con redondeo bancario (half-to-even): round(4.5) es 4 y
    round(2.5) es 2. En el paso REDONDEAR del descifrado LWE eso produce
    resultados incorrectos justo en el limite x.5, asi que el lenguaje usa
    esta funcion explicita en su lugar.

        >>> redondear_lattice(4.5), redondear_lattice(2.5)
        (5, 3)
        >>> redondear_lattice(-1.5), redondear_lattice(-2.4)
        (-2, -2)
    """
    if x >= 0:
        return math.floor(x + 0.5)
    return -math.floor(-x + 0.5)
