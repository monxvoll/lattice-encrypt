"""Variables, asignacion y tabla de simbolos del lenguaje."""
import pytest

from core.entorno import Entorno
from core.errores import LatticeError, LatticeNameError
from core.LatticeLexico import Lexico


def test_entorno_definir_y_obtener():
    e = Entorno()
    e.definir("A", (1.0, 2.0))
    assert e.existe("A") and e.obtener("A") == (1.0, 2.0)


def test_variable_no_definida():
    with pytest.raises(LatticeNameError, match="Variable no definida: X"):
        Entorno().obtener("X")
    assert issubclass(LatticeNameError, LatticeError)


def test_identificador_con_digitos_y_guion_bajo():
    tipos = [(t.tipo, t.valor) for t in Lexico().tokenizar("CLAVES_2 = KEYGEN")]
    assert tipos == [("PALABRA", "CLAVES_2"), ("IGUAL", "="), ("PALABRA", "KEYGEN")]


def test_minusculas_en_identificador_siguen_prohibidas():
    with pytest.raises(LatticeError):
        Lexico().tokenizar("Claves = KEYGEN")
