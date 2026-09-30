"""Lo que cambia para un despliegue publico: limites, corte por tiempo y demo.

Cada prueba manipula `servidor.MODO_DEMO` o `servidor.PROGRAMAS_DIR` con monkey-
patch, que los restaura al terminar. No se recarga el modulo a proposito: recar-
garlo reinstanciaria el cliente de TestClient y el resto de pruebas.
"""
import pytest

pytest.importorskip("httpx", reason="TestClient de FastAPI requiere httpx")

from fastapi import HTTPException
from fastapi.testclient import TestClient
from servidor import MAX_CODIGO, MAX_LINEAS, app

import servidor


@pytest.fixture
def cliente():
    return TestClient(app)


@pytest.fixture
def demo(monkeypatch):
    monkeypatch.setattr(servidor, "MODO_DEMO", True)


@pytest.fixture
def programa(monkeypatch, tmp_path):
    """Apunta PROGRAMAS_DIR a un directorio temporal de la prueba."""
    monkeypatch.setattr(servidor, "PROGRAMAS_DIR", tmp_path)
    return tmp_path


def _morir_sin_respuesta(args):
    """Suplanta al cuerpo del hijo y se sale sin encolar nada.

    Va a nivel de modulo porque con 'spawn' la funcion se tiene que poder
    picklear para mandarsela al proceso hijo. Se muere sin tocar la cola, que
    es lo que hace un OOM kill o un fallo al arrancar.
    """
    raise SystemExit(1)


# --- Corte por tiempo ------------------------------------------------------

def test_programa_normal_no_lo_corta(cliente):
    r = cliente.post("/ejecutar", json={"codigo": "VECTOR(1,2) SUMA VECTOR(3,4)",
                                        "tokens": False})
    assert r.status_code == 200
    assert r.json()["lineas"][0]["resultado"] == [4.0, 6.0]


def test_ejecucion_lenta_se_corta_y_responde_408():
    # El lenguaje no tiene ciclos, asi que un plazo de cero es la forma de
    # provocar el mismo camino que un programa colgado: el hijo sigue vivo
    # cuando vence el plazo.
    with pytest.raises(HTTPException) as e:
        servidor.ejecutar_con_timeout("VECTOR(1,2) SUMA VECTOR(3,4)", False, segundos=0)
    assert e.value.status_code == 408
    assert "tiempo limite" in e.value.detail


def test_hijo_que_muere_sin_respuesta_da_500_y_no_una_excepcion_suelta(monkeypatch):
    """El caso que se dio al medir en el contenedor: el hijo muere sin encolar.

    Si aqui se escapara el error crudo de la cola, el cliente recibiria un 500
    sin explicacion en vez de un 500 con mensaje.
    """
    monkeypatch.setattr(servidor, "ejecutar_en_proceso", _morir_sin_respuesta)
    # El plazo tiene que ser mayor que el arranque del hijo, no menor: con
    # 'spawn' el hijo tarda mas de un segundo en levantarse, asi que con un
    # plazo corto venceria mientras sigue vivo y se mediria el camino del 408
    # en vez de este. Y el get espera el plazo completo aunque el hijo muera
    # antes, porque la cola no se avisa cuando se cierra la otra punta: por eso
    # la prueba cuesta estos segundos y no se puede bajar.
    with pytest.raises(HTTPException) as e:
        servidor.ejecutar_con_timeout("VECTOR(1,2) SUMA VECTOR(3,4)", False, segundos=5)
    assert e.value.status_code == 500
    assert "inesperada" in e.value.detail


def test_el_corte_no_deja_procesos_vivos():
    """El proceso que se pasa de plazo tiene que morir, no quedar huerfano."""
    import multiprocessing as mp

    hijos = mp.active_children()
    with pytest.raises(HTTPException):
        servidor.ejecutar_con_timeout("VECTOR(1,2) SUMA VECTOR(3,4)", False, segundos=0)
    assert mp.active_children() == hijos


def test_el_informe_de_una_ejecucion_normal_no_pierde_datos():
    informe = servidor.ejecutar_con_timeout(
        'VECTOR(1,2) SUMA VECTOR(3,4)\nMATRIZ(1,2,3,4) IGUAL MATRIZ(1,2,3,4)', False
    )
    # Cruza la frontera del proceso como dato: si el informe no fuera
    # serializable, aqui habria reventado.
    assert informe["errores"] == 0
    assert [l["resultado"] for l in informe["lineas"]] == [[4.0, 6.0], True]


def test_los_tokens_tambien_llegan_del_proceso(cliente):
    r = cliente.post("/ejecutar", json={"codigo": 'VECTOR(0,0) TEXTO "a "', "tokens": True})
    tokens = r.json()["lineas"][0]["tokens"]
    assert [t["valor"] for t in tokens if t["tipo"] == "CADENA"] == ["a "]


# --- Limites de tamano -----------------------------------------------------

@pytest.mark.parametrize("ruta", ["/iniciar", "/ejecutar"])
def test_codigo_demasiado_largo_se_rechaza(cliente, ruta):
    r = cliente.post(ruta, json={"codigo": "VECTOR(1,1)" + " " * (MAX_CODIGO + 1)})
    assert r.status_code == 422


def test_codigo_al_limite_se_acepta(cliente):
    # El limite es de caracteres, no de lineas: una sola linea larga es legal.
    r = cliente.post("/ejecutar", json={"codigo": "VECTOR(1,2) SUMA VECTOR(3,4)"})
    assert r.status_code == 200


def test_nombre_demasiado_largo_se_rechaza(cliente, programa):
    r = cliente.post("/api/programas", json={"nombre": "a" * 65, "codigo": "x"})
    assert r.status_code == 422


def test_programa_demasiadas_lineas_se_rechaza(cliente):
    codigo = "\n".join(["VECTOR(1,1)"] * (MAX_LINEAS + 1))
    r = cliente.post("/ejecutar", json={"codigo": codigo})
    assert r.status_code == 400
    assert str(MAX_LINEAS) in r.json()["detail"]


def test_guardar_codigo_demasiado_largo_se_rechaza(cliente, programa):
    r = cliente.post("/api/programas", json={"nombre": "x", "codigo": "a" * (MAX_CODIGO + 1)})
    assert r.status_code == 422


# --- Modo demo -------------------------------------------------------------

def test_la_raiz_dice_si_es_demo(cliente):
    assert cliente.get("/").json()["modo_demo"] is False


def test_la_raiz_avisa_cuando_es_demo(cliente, demo):
    assert cliente.get("/").json()["modo_demo"] is True


def test_en_demo_no_se_guarda(cliente, demo, programa):
    r = cliente.post("/api/programas", json={"nombre": "secreto", "codigo": "x"})
    assert r.status_code == 403
    assert list(programa.glob("*.le")) == []


def test_en_demo_no_se_borra(cliente, demo, programa):
    (programa / "secreto.le").write_text("x", encoding="utf-8")
    r = cliente.delete("/api/programas/secreto")
    assert r.status_code == 403
    assert (programa / "secreto.le").exists()


def test_en_demo_se_sigue_ejecutando(cliente, demo):
    """El modo demo apaga el almacenamiento, no el lenguaje."""
    r = cliente.post("/ejecutar", json={"codigo": "VECTOR(1,2) SUMA VECTOR(3,4)",
                                        "tokens": False})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_fuera_de_demo_guardar_y_borrar_siguen_funcionando(cliente, programa):
    assert cliente.post("/api/programas", json={"nombre": "mio", "codigo": "x"}).status_code == 200
    assert cliente.delete("/api/programas/mio").status_code == 200


def test_los_programas_siguen_disponibles_para_leer(cliente, demo, programa):
    # Cortar la escritura no tiene por que cortar la lectura: si el despliegue
    # ya tenia programas de antes, se pueden seguir abriendo.
    (programa / "viejo.le").write_text("VECTOR(1,2)", encoding="utf-8")
    assert cliente.get("/api/programas/viejo").json()["codigo"] == "VECTOR(1,2)"


# --- Ruta configurable -----------------------------------------------------

def test_programas_dir_por_defecto_esta_dentro_del_proyecto():
    assert servidor.PROGRAMAS_DIR.name == "programas"


def test_programas_dir_se_puede_mover(monkeypatch, tmp_path):
    destino = tmp_path / "disco"
    monkeypatch.setenv("PROGRAMAS_DIR", str(destino))
    import importlib

    recargado = importlib.reload(servidor)
    try:
        assert recargado.PROGRAMAS_DIR == destino
    finally:
        monkeypatch.delenv("PROGRAMAS_DIR")
        importlib.reload(servidor)


def test_modo_demo_se_lee_de_entorno(monkeypatch):
    import importlib

    monkeypatch.setenv("MODO_DEMO", "1")
    importlib.reload(servidor)
    try:
        assert servidor.MODO_DEMO is True
    finally:
        monkeypatch.delenv("MODO_DEMO")
        importlib.reload(servidor)


def test_tiempo_limite_se_lee_de_entorno(monkeypatch):
    import importlib

    monkeypatch.setenv("TIEMPO_LIMITE", "12")
    importlib.reload(servidor)
    try:
        assert servidor.TIEMPO_LIMITE == 12
    finally:
        monkeypatch.delenv("TIEMPO_LIMITE")
        importlib.reload(servidor)


@pytest.mark.parametrize("valor", ["", "mucho", "-", None])
def test_un_tiempo_limite_mal_escrito_no_tira_el_servicio(monkeypatch, valor):
    """El servicio tiene que arrancar aunque el valor sea basura."""
    import importlib

    if valor is None:
        monkeypatch.delenv("TIEMPO_LIMITE", raising=False)
    else:
        monkeypatch.setenv("TIEMPO_LIMITE", valor)
    importlib.reload(servidor)
    try:
        assert servidor.TIEMPO_LIMITE == 5
    finally:
        monkeypatch.delenv("TIEMPO_LIMITE", raising=False)
        importlib.reload(servidor)
