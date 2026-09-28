"""Caracterizacion del comportamiento que YA funciona correctamente.

Estos tests pasan hoy y existen para demostrar que los arreglos de los bugs
no rompen nada. No son tests de comportamiento nuevo.
"""
import pytest

from core.LatticeLexico import Lexico
from core.LatticeSintactico import Sintactico


def ev(texto):
    return Sintactico(Lexico().tokenizar(texto)).analisisSintactico()


@pytest.mark.parametrize("linea,esperado", [
    ("VECTOR(1,2) SUMA VECTOR(3,4)", (4.0, 6.0)),
    ("MATRIZ(2,1,0,2) POR VECTOR(3,4)", (10.0, 8.0)),
    ("VECTOR(1,2) PUNTO VECTOR(2,3)", 8.0),
    ("VECTOR(5,7) RESTA VECTOR(2,3)", (3.0, 4.0)),
    ("VECTOR(5,7) MOD VECTOR(3,3)", (2.0, 1.0)),
    ("VECTOR(1,2) IGUAL VECTOR(1,2)", True),
    ("VECTOR(1,2) IGUAL VECTOR(1,3)", False),
    ("VECTOR(0,0) TEXTO \"AB\"", (65.0, 66.0)),
    ("VECTOR(65,66) CARACTERES", "AB"),
])
def test_operaciones_conservadas(linea, esperado):
    assert ev(linea) == esperado


def test_ruido_explicito():
    assert ev("VECTOR(1,2) RUIDO VECTOR(0.1,0.2)") == pytest.approx((1.1, 2.2))


def test_ruido_estocastico_permanece_en_el_rango():
    for _ in range(50):
        x, y = ev("VECTOR(10,10) RUIDO")
        assert 9.5 <= x <= 10.5
        assert 9.5 <= y <= 10.5


def test_redondear_enteriza():
    assert ev("VECTOR(1.4,2.6) REDONDEAR") == (1, 3)


def test_matriz_por_vector():
    assert ev("MATRIZ(72,79,76,65) CARACTERES") == "HOLA"


def test_negativos_admitidos():
    assert ev("VECTOR(-1,2.5) SUMA VECTOR(1,1)") == (0.0, 3.5)


def test_operando_sin_operador_se_retorna():
    assert ev("VECTOR(1,2)") == (1.0, 2.0)


def test_minusculas_siguen_sin_aceptarse_fuera_de_cadena():
    with pytest.raises(SyntaxError):
        ev("vector(1,2) suma vector(3,4)")
