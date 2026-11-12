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


# --- Parser: asignacion, variables y operandos -------------------------------
from core.errores import LatticeSyntaxError, LatticeTypeError
from core.LatticeSintactico import Sintactico


def correr(*lineas):
    e = Entorno()
    r = None
    for linea in lineas:
        r = Sintactico(Lexico().tokenizar(linea), e).analisisSintactico()
    return r, e


def test_asignacion_y_reuso():
    assert correr("A = VECTOR(1,2)", "A SUMA A")[0] == (2.0, 4.0)


def test_variable_como_operando_derecho():
    assert correr("A = VECTOR(3,4)", "VECTOR(1,2) RESTA A")[0] == (-2.0, -2.0)


def test_reasignacion_y_copia():
    _, e = correr("A = VECTOR(1,1)", "B = A", "A = A SUMA VECTOR(1,1)")
    assert e.obtener("B") == (1.0, 1.0)
    assert e.obtener("A") == (2.0, 2.0)


def test_texto_como_operando():
    assert correr('M = TEXTO "Hola ñ"')[0] == "Hola ñ"


def test_igual_entre_textos():
    assert correr('A = TEXTO "x"', 'B = TEXTO "x"', "A IGUAL B")[0] is True


def test_texto_en_operacion_vectorial_es_error_de_tipo():
    with pytest.raises(LatticeTypeError):
        correr('M = TEXTO "AB"', "M SUMA VECTOR(1,2)")


def test_suma_de_matrices_es_error_de_tipo():
    with pytest.raises(LatticeTypeError):
        correr("MATRIZ(1,2,3,4) SUMA MATRIZ(1,2,3,4)")


def test_variable_no_definida_en_expresion():
    with pytest.raises(LatticeNameError):
        correr("X SUMA VECTOR(1,2)")


@pytest.mark.parametrize("linea", [
    "SUMA = VECTOR(1,2)", "VECTOR = VECTOR(1,2)", "KEYGEN = VECTOR(1,2)",
])
def test_nombre_reservado(linea):
    with pytest.raises(LatticeSyntaxError, match="palabra reservada"):
        correr(linea)


def test_asignacion_sin_expresion():
    with pytest.raises(LatticeSyntaxError):
        correr("A =")


@pytest.mark.parametrize("linea", [
    "VECTOR(1,2) REDONDEAR VECTOR(1,1)",
    "VECTOR(1,2) SUMA VECTOR(1,1) VECTOR(2,2)",
])
def test_tokens_sobrantes(linea):
    with pytest.raises(LatticeSyntaxError, match="Sobra"):
        correr(linea)


def test_vector_literal_sigue_igual():
    assert correr('VECTOR(0,0) TEXTO "AB"')[0] == (65.0, 66.0)
