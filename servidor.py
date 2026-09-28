"""API y pagina web del interprete Lattice Encrypt.

Sirve dos cosas sobre el mismo puerto:

* la API de ejecucion (`/iniciar`, `/ejecutar`) usada por tests y por clientes
  externos, que no cambian de comportamiento respecto a la version previa;
* la interfaz web estatica de OneCompiler, montada en `web/`.

Los programas del usuario se guardan en `programas/` al lado de este archivo.
"""
import os
import re
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from core.LatticeLexico import Lexico
from core.LatticeSintactico import Sintactico
from core.errores import LatticeError
from core.interpreteArchivo import EXTENSION, ejecutar_programa

app = FastAPI(
    title="LatticeEncrypt",
    description="API para ejecutar programas del lenguaje LatticeEncrypt",
    version="1"
)

RAIZ = Path(__file__).resolve().parent
WEB_DIR = RAIZ / "web"
PROGRAMAS_DIR = RAIZ / "programas"

# Nombre de archivo de programa. Se limita a un conjunto reducido de caracteres
# porque el nombre va a parar a un archivo del disco: '..' o una barra permitirian
# salirse de programas/ escribiendo donde no debe.
NOMBRE_VALIDO = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")

# Techo de lineas por peticion. El interprete no tiene timeout (no hay forma de
# interrumpirlo a mitad), asi que este limite es lo que evita que una sola
# peticion bloquee el worker indefinidamente.
MAX_LINEAS = 2000


class CodigoRequest(BaseModel):
    codigo: str


class ProgramaRequest(BaseModel):
    nombre: str = Field(description="Nombre sin extension, ej. 'criptografia'")
    codigo: str = ""


class EjecutarRequest(BaseModel):
    codigo: str
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


@app.get("/")
def inicio():
    return {
        "lenguaje": "LatticeEncrypt",
        "version": "vLatticeEncrypt1",
        "estado": "En desarrollo"
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
    informe = ejecutar_programa(texto, mostrar_tokens=request.tokens)
    informe["duracion_ms"] = round((time.perf_counter() - inicio) * 1000, 2)
    informe["ok"] = informe["errores"] == 0
    return informe


# --- Archivos de programas -------------------------------------------------

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
