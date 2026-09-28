"""Regresion de los 6 bugs reportados en Analisis_LatticeEncrypt.md.

Cada test de este archivo debe FALLAR antes del arreglo correspondiente.
"""
import os
import subprocess
import sys

import pytest

from core.LatticeLexico import Lexico
from core.LatticeSintactico import Sintactico
from core.interpreteArchivo import ejecutar_linea, ejecutar_archivo

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ev(texto):
    return Sintactico(Lexico().tokenizar(texto)).analisisSintactico()


# ---------------------------------------------------------------- bug #1
def test_bug1_reglas_json_no_depende_del_cwd(tmp_path):
    """Bug #1: abrir('reglas/reglas.json') solo funciona desde la raiz del repo."""
    codigo = (
        "import sys; sys.path.insert(0, r'%s')\n"
        "from core.LatticeLexico import Lexico\n"
        "from core.LatticeSintactico import Sintactico\n"
        "print(Sintactico(Lexico().tokenizar('VECTOR(1,2) SUMA VECTOR(3,4)')).analisisSintactico())\n"
    ) % RAIZ
    r = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=str(tmp_path), capture_output=True, text=True,
    )
    assert r.returncode == 0, "Fallo al ejecutar fuera de la raiz:\n" + r.stderr
    assert "(4.0, 6.0)" in r.stdout


def test_bug1_reglas_json_se_cachea():
    """Bug #1 (segunda mitad): releer el JSON del disco en cada instruccion es innecesario."""
    from core import LatticeSintactico as mod
    assert hasattr(mod, "_REGLAS"), "reglas.json debe cargarse una vez al importar el modulo"
    assert mod._REGLAS, "la configuracion de reglas no puede estar vacia"


# ------------------------------------------------------------- bugs #2 y #3
def test_bug2_texto_acepta_minusculas():
    """Bug #2: TEXTO "ab" fallaba porque el lexer exigia mayusculas."""
    assert ev('VECTOR(0,0) TEXTO "ab"') == (float(ord("a")), float(ord("b")))


def test_bug2_texto_acepta_frase_normal():
    """Un texto de 4 caracteres devuelve una matriz 2x2 (semantica preexistente)."""
    assert ev('VECTOR(0,0) TEXTO "Hola"') == [
        [float(ord("H")), float(ord("o"))],
        [float(ord("l")), float(ord("a"))],
    ]


def test_bug3_texto_conserva_espacios():
    """Bug #3: el lexer descartaba los espacios porque ignoraba el contexto de comillas."""
    assert ev('VECTOR(0,0) TEXTO "A "') == (float(ord("A")), float(ord(" ")))


def test_bug3_lexer_emitir_un_solo_token_cadena():
    """El lexer debe emitir CADENA literal, no una secuencia de PALABRA."""
    tokens = Lexico().tokenizar('VECTOR(0,0) TEXTO "a b"')
    cadenas = [t for t in tokens if t.tipo == "CADENA"]
    assert len(cadenas) == 1
    assert cadenas[0].valor == "a b"


def test_bug3_cadena_sin_cerrar_es_error_de_sintaxis():
    with pytest.raises(SyntaxError):
        Lexico().tokenizar('VECTOR(0,0) TEXTO "sin cerrar')


def test_bug2_minusculas_siguen_rechazadas_fuera_de_cadena():
    with pytest.raises(SyntaxError):
        ev("vector(1,2) suma vector(3,4)")


# ---------------------------------------------------------------- bug #4
def test_bug4_mod_por_cero_no_escapa_como_excepcion_del_lenguaje():
    """Bug #4: ZeroDivisionError se escapaba de ejecutar_linea."""
    from core.errores import LatticeError
    with pytest.raises(LatticeError):
        ejecutar_linea("VECTOR(5,7) MOD VECTOR(0,3)")


def test_bug4_tipo_incorrecto_no_escapa_como_excepcion_del_lenguaje():
    from core.errores import LatticeError
    with pytest.raises(LatticeError):
        ejecutar_linea("VECTOR(1,2) PUNTO MATRIZ(1,2,3,4)")


def test_bug4_error_no_se_confunde_con_el_resultado_true():
    """Un error no debe devolverse como True: IGUAL devuelve True legitimamente."""
    from core.errores import LatticeError
    with pytest.raises(LatticeError):
        ejecutar_linea("VECTOR(5,7) MOD VECTOR(0,3)")
    assert ejecutar_linea("VECTOR(1,2) IGUAL VECTOR(1,2)") is True


def test_bug4_los_errores_del_lenguaje_son_tambien_builtins():
    """Las excepciones propias deben seguir siendo capturables como las de Python."""
    from core.errores import LatticeSyntaxError, LatticeTypeError, LatticeValueError
    assert issubclass(LatticeSyntaxError, SyntaxError)
    assert issubclass(LatticeTypeError, TypeError)
    assert issubclass(LatticeValueError, ValueError)


def test_bug4b_el_script_continua_tras_una_linea_con_error(tmp_path):
    """Bug #4b: en modo batch una linea con error abortaba todo el script."""
    le = tmp_path / "con_error.le"
    le.write_text(
        "VECTOR(1,2) SUMA VECTOR(3,4)\n"
        "VECTOR(5,7) MOD VECTOR(0,3)\n"
        "VECTOR(1,1) SUMA VECTOR(1,1)\n",
        encoding="utf-8",
    )
    r = ejecutar_archivo(str(le))
    assert r == (2.0, 2.0), "la linea 3 debe ejecutarse y su resultado ser el ultimo"


def test_bug4b_el_error_se_reporta_con_numero_de_linea(tmp_path, capsys):
    le = tmp_path / "con_error.le"
    le.write_text("VECTOR(5,7) MOD VECTOR(0,3)\n", encoding="utf-8")
    ejecutar_archivo(str(le))
    salida = capsys.readouterr().out
    assert "Error en la línea 1" in salida
    assert "1 error(es)" in salida


def test_lattice_le_de_ejemplo_se_interpreta_sin_errores(capsys):
    """El archivo de ejemplo del repo debe seguir ejecutandose completo."""
    ruta = os.path.join(RAIZ, "lattice.le")
    ejecutar_archivo(ruta)
    salida = capsys.readouterr().out
    assert "error" not in salida.lower(), salida


# ---------------------------------------------------------------- bug #5
def test_bug5_matriz_igual_matriz():
    """Bug #5: IGUAL solo soportaba VECTOR IGUAL VECTOR."""
    assert ev("MATRIZ(1,2,3,4) IGUAL MATRIZ(1,2,3,4)") is True
    assert ev("MATRIZ(1,2,3,4) IGUAL MATRIZ(1,2,3,5)") is False


def test_bug5_tipos_mixtos_siguen_siendo_error():
    with pytest.raises(TypeError):
        ev("VECTOR(1,2) IGUAL MATRIZ(1,2,3,4)")


# ---------------------------------------------------------------- bug #6
def test_bug6_redondeo_es_half_away_from_zero():
    """Bug #6: round() de Python es bancario; 4.5 daba 4 en vez de 5."""
    assert ev("VECTOR(4.5,2.5) REDONDEAR") == (5, 3)
    assert ev("VECTOR(0.5,-0.5) REDONDEAR") == (1, -1)
    assert ev("VECTOR(-1.5,2.4) REDONDEAR") == (-2, 2)


def test_bug6_matriz_4_5_va_a_5():
    assert ev("MATRIZ(1.2,2.7,3.4,4.5) REDONDEAR") == [[1, 3], [3, 5]]


def test_bug6_utilidad_de_redondeo():
    from core.utilidades import redondear_lattice
    casos = [(4.5, 5), (2.5, 3), (0.5, 1), (-0.5, -1), (-1.5, -2),
             (2.4, 2), (-2.4, -2), (2.6, 3), (-2.6, -3), (0.0, 0)]
    for entrada, esperado in casos:
        assert redondear_lattice(entrada) == esperado, entrada


def test_bug6_caracteres_usa_el_redondeo_corregido():
    """CARACTERES tambien usaba round(): con 64.5 el ascii debe ser 'A' (65), no '@' (64)."""
    assert ev("VECTOR(64.5,66) CARACTERES") == "AB"
