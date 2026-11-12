"""KEYGEN, CIFRAR y DESCIFRAR desde el lenguaje."""
import os

import pytest
from fastapi.testclient import TestClient

from core.entorno import Entorno
from core.errores import LatticeSyntaxError, LatticeTypeError, LatticeValueError
from core.LatticeLexico import Lexico
from core.LatticeSintactico import Sintactico
from servidor import app

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def correr(*lineas):
    e = Entorno()
    r = None
    for linea in lineas:
        r = Sintactico(Lexico().tokenizar(linea), e).analisisSintactico()
    return r, e


@pytest.mark.parametrize("keygen", ["KEYGEN", "KEYGEN MLKEM"])
def test_flujo_completo(keygen):
    r, _ = correr(f"C = {keygen}", 'X = TEXTO "Hola ñ" CIFRAR C', "X DESCIFRAR C")
    assert r == "Hola ñ"


def test_keygen_lwe_explicito():
    assert repr(correr("C = KEYGEN LWE")[0]) == "<CLAVES LWE FrodoPKE-640>"


def test_keygen_mlkem_repr():
    assert repr(correr("C = KEYGEN MLKEM")[0]) == "<CLAVES ML-KEM-768>"


def test_repr_cifrado():
    r, _ = correr("C = KEYGEN", 'TEXTO "HOLA" CIFRAR C')
    assert repr(r).startswith("<CIFRADO LWE FrodoPKE-640, 1 bloque")
    r, _ = correr("C = KEYGEN MLKEM", 'TEXTO "HOLA" CIFRAR C')
    assert repr(r).startswith("<CIFRADO ML-KEM-768, ")


def test_verificar_con_igual():
    r, _ = correr("C = KEYGEN MLKEM", 'O = TEXTO "abc"', "X = O CIFRAR C",
                  "M = X DESCIFRAR C", "M IGUAL O")
    assert r is True


def test_mezcla_de_modos():
    with pytest.raises(LatticeTypeError, match="LWE"):
        correr("L = KEYGEN", "K = KEYGEN MLKEM", 'X = TEXTO "a" CIFRAR L', "X DESCIFRAR K")


@pytest.mark.parametrize("linea", [
    "VECTOR(1,2) CIFRAR C",
    'TEXTO "a" CIFRAR VECTOR(1,2)',
    "C DESCIFRAR C",
    "X CIFRAR X",
    "X DESCIFRAR X",
    "C SUMA VECTOR(1,2)",
])
def test_tipos_invalidos(linea):
    with pytest.raises(LatticeTypeError):
        correr("C = KEYGEN", 'X = TEXTO "a" CIFRAR C', linea)


def test_clave_ajena_mlkem():
    with pytest.raises(LatticeValueError):
        correr("C = KEYGEN MLKEM", "D = KEYGEN MLKEM", 'X = TEXTO "a" CIFRAR C', "X DESCIFRAR D")


def test_keygen_infijo():
    with pytest.raises(LatticeSyntaxError, match="NOMBRE = KEYGEN"):
        correr("MATRIZ(3,1,2,4) KEYGEN VECTOR(1,2)")


@pytest.mark.parametrize("linea", ["C = KEYGEN MLKEM X", "C = KEYGEN RSA"])
def test_keygen_con_sobrante(linea):
    with pytest.raises(LatticeSyntaxError):
        correr(linea)


def test_api_programa_completo():
    with open(os.path.join(RAIZ, "cifrado.le"), encoding="utf-8") as f:
        codigo = f.read()
    r = TestClient(app).post("/ejecutar", json={"codigo": codigo, "tokens": False})
    informe = r.json()
    assert informe["errores"] == 0, informe
    resultados = [l["resultado"] for l in informe["lineas"]]
    assert "Hola, mundo poscuantico" in resultados
    assert "Mensaje con ñ y tildes: acción" in resultados
    assert resultados.count(True) == 2
    assert "<CLAVES ML-KEM-768>" in resultados
    assert "privada" not in r.text and "array" not in r.text


@pytest.mark.parametrize("codigo, resumen", [
    ("KEYGEN", "<CLAVES LWE FrodoPKE-640>"),
    ("KEYGEN MLKEM", "<CLAVES ML-KEM-768>"),
])
def test_api_iniciar_keygen_devuelve_solo_el_resumen(codigo, resumen):
    r = TestClient(app).post("/iniciar", json={"codigo": codigo})
    assert r.status_code == 200
    assert r.json()["resultado"] == resumen


@pytest.mark.parametrize("izquierdo", ['S = TEXTO "AB"', "S = KEYGEN"])
def test_texto_como_operador_valida_el_operando_izquierdo(izquierdo):
    with pytest.raises(LatticeTypeError):
        correr(izquierdo, 'S TEXTO "AB"')
