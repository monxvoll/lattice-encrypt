"""Cobertura de la API FastAPI: los mismos 6 bugs, por el tercer punto de entrada."""
import pytest

pytest.importorskip("httpx", reason="TestClient de FastAPI requiere httpx")

from fastapi.testclient import TestClient
from servidor import app

client = TestClient(app)


def api(linea):
    return client.post("/iniciar", json={"codigo": linea}).json()


def test_raiz_sigue_respondiendo():
    assert client.get("/").json()["lenguaje"] == "LatticeEncrypt"


def test_api_operacion_basica():
    r = api("VECTOR(1,2) SUMA VECTOR(3,4)")
    assert r["exito"] is True
    assert r["resultado"] == [4.0, 6.0]


def test_api_texto_minusculas():
    assert api('VECTOR(0,0) TEXTO "ab"')["resultado"] == [97.0, 98.0]


def test_api_texto_conserva_espacios():
    assert api('VECTOR(0,0) TEXTO "A "')["resultado"] == [65.0, 32.0]


def test_api_token_cadena_en_el_json():
    tokens = api('VECTOR(0,0) TEXTO "a "')["tokens"]
    cadena = [t for t in tokens if t["tipo"] == "CADENA"]
    assert [t["valor"] for t in cadena] == ["a "]


def test_api_error_del_lenguaje_no_es_error_interno():
    r = api("VECTOR(5,7) MOD VECTOR(0,3)")
    assert r["tipo"] == "LatticeDivisionError"
    assert not r["error"].startswith("Error interno")


def test_api_error_de_tipo_no_es_error_interno():
    assert api("VECTOR(1,2) PUNTO MATRIZ(1,2,3,4)")["tipo"] == "LatticeTypeError"


def test_api_matriz_igual_matriz():
    assert api("MATRIZ(1,2,3,4) IGUAL MATRIZ(1,2,3,4)")["resultado"] is True


def test_api_redondeo_corregido():
    assert api("VECTOR(4.5,2.5) REDONDEAR")["resultado"] == [5, 3]


def test_api_texto_fuera_de_dominio():
    assert api('VECTOR(0,0) TEXTO "abc"')["tipo"] == "LatticeValueError"


def test_api_codigo_vacio():
    assert client.post("/iniciar", json={"codigo": "  "}).json() == {
        "error": "No se ingreso codigo"
    }
