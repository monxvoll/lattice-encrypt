"""API y pagina web del interprete Lattice Encrypt.

Sirve dos cosas sobre el mismo puerto:

* la API de ejecucion (`/iniciar`, `/ejecutar`) usada por tests y por clientes
  externos, que no cambian de comportamiento respecto a la version previa;
* la interfaz web estatica de OneCompiler, montada en `web/`.

Los programas del usuario se guardan en `programas/` al lado de este archivo, o
en la ruta que indique la variable de entorno `PROGRAMAS_DIR`.

Variables de entorno que leen los valores de abajo:

* `PORT`          lo usa el CMD del Dockerfile para elegir el puerto.
* `MODO_DEMO`     con valor 1 el servicio se despliega como demo publica: se
                  pueden ejecutar programas pero no guardar ni borrar.
* `PROGRAMAS_DIR` donde viven los programas guardados (por defecto `programas/`).
* `TIEMPO_LIMITE` segundos que puede tomar una ejecucion antes de cortarse.
"""
import multiprocessing as mp
import os
import queue
import re
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from core.LatticeLexico import Lexico
from core.LatticeSintactico import Sintactico
from core.ejecutor import ejecutar as ejecutar_en_proceso
from core.errores import LatticeError
from core.interpreteArchivo import EXTENSION

app = FastAPI(
    title="LatticeEncrypt",
    description="API para ejecutar programas del lenguaje LatticeEncrypt",
    version="1"
)

RAIZ = Path(__file__).resolve().parent
WEB_DIR = RAIZ / "web"
# La ruta es configurable porque en un despliegue el sistema de archivos es
# efimero: todo lo guardado en programas/ se pierde en cada reinicio. Con
# PROGRAMAS_DIR se apunta a un volumen montado (un Persistent Disk de Render)
# sin tocar el codigo. En modo demo no se escribe nada, asi que da igual.
PROGRAMAS_DIR = Path(os.environ.get("PROGRAMAS_DIR") or (RAIZ / "programas"))

# Modo demo para un despliegue publico. Sin esto, cualquier visitante puede
# guardar, sobrescribir y borrar programas de los demas, porque el almacenamiento
# es compartido y no hay sesion ni usuarios. Con MODO_DEMO=1 se corta la
# escritura: el editor sigue sirviendo para ejecutar, que es lo que se quiere
# mostrar, pero no expone el almacenamiento.
MODO_DEMO = os.environ.get("MODO_DEMO", "").strip().lower() in {
    "1", "true", "yes", "si", "sí",
}

# Nombre de archivo de programa. Se limita a un conjunto reducido de caracteres
# porque el nombre va a parar a un archivo del disco: '..' o una barra permitirian
# salirse de programas/ escribiendo donde no debe.
NOMBRE_VALIDO = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")


def _segundos(valor, por_defecto):
    """Lee un numero del entorno sin caerse si viene mal escrito.

    Una variable mal puesta en el panel de Render no puede dejar el servicio sin
    arrancar: se usa el valor por defecto y el despliegue sigue en pie.
    """
    try:
        return float(valor)
    except (TypeError, ValueError):
        return por_defecto


# Techo de lineas por peticion.
MAX_LINEAS = 2000

# Techo de caracteres por peticion. MAX_LINEAS solo acota las lineas: 2000
# lineas de un par de megabytes cada una las pasa igual, asi que el tamano se
# limita aparte, y mas abajo se corta la ejecucion por tiempo.
MAX_CODIGO = 100_000

# Segundos que puede tomar una ejecucion. El interprete no se puede interrumpir
# a mitad, asi que el corte se hace desde fuera: se ejecuta en un proceso
# aparte y se le mata al pasar de este limite. Es la unica proteccion real
# contra un programa con un bucle infinito en un servicio publico.
TIEMPO_LIMITE = _segundos(os.environ.get("TIEMPO_LIMITE"), 5)


class CodigoRequest(BaseModel):
    codigo: str = Field(max_length=MAX_CODIGO)


class ProgramaRequest(BaseModel):
    nombre: str = Field(
        max_length=64,
        description="Nombre sin extension, ej. 'criptografia'",
    )
    codigo: str = Field(default="", max_length=MAX_CODIGO)


class EjecutarRequest(BaseModel):
    codigo: str = Field(max_length=MAX_CODIGO)
    tokens: bool = Field(
        default=True,
        description="Incluir la lista de tokens de cada linea en la respuesta",
    )


def _validar_nombre(nombre):
    """Devuelve el nombre si es seguro, o lanza HTTPException 400."""
    nombre = (nombre or "").strip()
    if not NOMBRE_VALIDO.match(nombre):
        raise HTTPException(
            status_code=400,
            detail="Nombre invalido: usa de 1 a 64 caracteres alfanumericos, "
                   "guion o guion bajo (sin espacios ni barras).",
        )
    return nombre


def _ruta_programa(nombre):
    return PROGRAMAS_DIR / f"{nombre}{EXTENSION}"


def _programa_existe(nombre):
    ruta = _ruta_programa(nombre)
    if not ruta.is_file():
        raise HTTPException(status_code=404, detail=f"El programa '{nombre}' no existe.")
    return ruta


# --- Ejecucion con tiempo limite -------------------------------------------

def ejecutar_con_timeout(texto, mostrar_tokens, segundos=TIEMPO_LIMITE):
    """Ejecuta el programa en un proceso aparte y lo corta si se pasa de tiempo.

    El interprete no se puede interrumpir a mitad de una instruccion, asi que
    MAX_LINEAS no alcanza: un bucle dentro de una sola linea puede dejar el
    worker ocupado indefinidamente. La unica forma de garantizar que eso no
    bloquea el servicio es correrlo fuera y matarlo al vencer el plazo.

    Se usa 'spawn' y no el metodo por defecto porque en Linux el metodo por
    defecto es 'fork': el hijo heredaria los hilos del servidor y su estado
    compartido. Con 'spawn' arranca limpio. El cuerpo del hijo esta en
    core.ejecutor para que ese arranque no tenga que importar FastAPI.
    """
    contexto = mp.get_context("spawn")
    cola = contexto.Queue()
    proceso = contexto.Process(
        target=ejecutar_en_proceso,
        args=(texto, mostrar_tokens, cola),
        daemon=True,
    )
    proceso.start()
    try:
        informe = None
        try:
            informe = cola.get(timeout=segundos)
        except (queue.Empty, EOFError, OSError):
            # La cola vacia no siempre significa timeout: el proceso tambien
            # puede haber muerto sin dejar nada (memoria agotada, un fallo al
            # arrancar). Se distingue por si sigue vivo.
            if proceso.is_alive():
                raise HTTPException(
                    status_code=408,
                    detail=(
                        f"La ejecucion supero el tiempo limite de {segundos:g} s. "
                        "El programa se detuvo."
                    ),
                ) from None
            # Murio: se da un margen corto por si el dato iba de camino, porque
            # el hilo alimentador de la cola entrega de forma asincrona.
            try:
                informe = cola.get(timeout=0.5)
            except (queue.Empty, EOFError, OSError):
                # Sin este filtro, el error crudo de la cola se escaparia y el
                # cliente recibiria un 500 sin explicacion.
                raise HTTPException(
                    status_code=500,
                    detail=(
                        "El interprete termino de forma inesperada (codigo de "
                        f"salida {proceso.exitcode}) sin devolver resultado."
                    ),
                ) from None
    finally:
        # Siempre: el proceso termina solo, pero hay que asegurarse. Si se mata
        # a mitad hay que cerrar la cola para no dejar el hilo alimentador
        # colgado esperando a un lector que ya no existe.
        if proceso.is_alive():
            proceso.kill()
        proceso.join(timeout=5)
        cola.close()

    if "_error" in informe:
        raise HTTPException(status_code=500, detail=informe["_error"])
    return informe


@app.get("/")
def inicio():
    return {
        "lenguaje": "LatticeEncrypt",
        "version": "vLatticeEncrypt1",
        "estado": "En desarrollo",
        # El editor lee esto para no ofrecer guardar y borrar cuando el
        # despliegue es una demo sin almacenamiento.
        "modo_demo": MODO_DEMO,
    }


@app.post("/iniciar")
def ejecutar_codigo(request: CodigoRequest):
    """Ejecuta una sola instruccion. Se mantiene para no romper clientes previos."""
    try:
        codigo = request.codigo.strip()
        if not codigo:
            return {"error": "No se ingreso codigo"}
        lexico = Lexico()
        tokens = lexico.tokenizar(codigo)
        analizador = Sintactico(tokens)
        resultado = analizador.analisisSintactico()
        return {
            "exito": True,
            "resultado": resultado,
            "tokens": [
                token.to_json()
                for token in tokens]
        }
    except LatticeError as error:
        # Error del lenguaje (sintaxis, tipo, valor o division): es culpa del
        # codigo enviado, no de la API, asi que no se marca como error interno.
        return {"error": str(error), "tipo": type(error).__name__}
    except Exception as error:
        return {"error": f"Error interno: {str(error)}"}


@app.post("/ejecutar")
def ejecutar_programa_web(request: EjecutarRequest):
    """Ejecuta un programa multi-linea y devuelve la consola y el detalle.

    A diferencia de `/iniciar` no se corta en el primer error: cada linea que
    falla se reporta y el script sigue, que es como se comporta el interprete
    de archivos.

    La ejecucion va en un proceso aparte con tiempo limite; si se pasa,
    la peticion responde 408 en vez de dejar el worker ocupado.
    """
    texto = request.codigo
    if not texto.strip():
        raise HTTPException(status_code=400, detail="No se ingreso codigo")
    if len(texto.splitlines()) > MAX_LINEAS:
        raise HTTPException(
            status_code=400,
            detail=f"El programa supera el limite de {MAX_LINEAS} lineas.",
        )

    inicio = time.perf_counter()
    informe = ejecutar_con_timeout(texto, mostrar_tokens=request.tokens)
    informe["duracion_ms"] = round((time.perf_counter() - inicio) * 1000, 2)
    informe["ok"] = informe["errores"] == 0
    return informe


# --- Archivos de programas -------------------------------------------------

def _rechazar_si_demo():
    """Impide escribir en el almacenamiento compartido cuando es demo."""
    if MODO_DEMO:
        raise HTTPException(
            status_code=403,
            detail=(
                "Este despliegue es una demo: se puede ejecutar codigo pero no "
                "guardar ni borrar programas."
            ),
        )


@app.get("/api/programas")
def listar_programas():
    """Nombres de los programas guardados, en orden alfabetico."""
    PROGRAMAS_DIR.mkdir(parents=True, exist_ok=True)
    nombres = sorted(p.stem for p in PROGRAMAS_DIR.glob(f"*{EXTENSION}") if p.is_file())
    return {"programas": nombres}


@app.get("/api/programas/{nombre}")
def leer_programa(nombre: str):
    _validar_nombre(nombre)
    ruta = _programa_existe(nombre)
    return {"nombre": nombre, "codigo": ruta.read_text(encoding="utf-8")}


@app.post("/api/programas")
def guardar_programa(request: ProgramaRequest):
    _rechazar_si_demo()
    nombre = _validar_nombre(request.nombre)
    PROGRAMAS_DIR.mkdir(parents=True, exist_ok=True)
    ruta = _ruta_programa(nombre)
    # Se escribe aparte y se renombra: si el proceso muere a mitad, el archivo
    # viejo queda intacto en vez de quedar truncado.
    temporal = ruta.with_suffix(ruta.suffix + ".tmp")
    temporal.write_text(request.codigo, encoding="utf-8")
    os.replace(temporal, ruta)
    return {"nombre": nombre, "guardado": True, "bytes": len(request.codigo.encode("utf-8"))}


@app.delete("/api/programas/{nombre}")
def borrar_programa(nombre: str):
    _rechazar_si_demo()
    _validar_nombre(nombre)
    ruta = _programa_existe(nombre)
    ruta.unlink()
    return {"nombre": nombre, "borrado": True}


# --- Pagina web ------------------------------------------------------------

if WEB_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

    @app.get("/editor")
    def pagina_editor():
        return FileResponse(WEB_DIR / "index.html")
