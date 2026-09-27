from fastapi import FastAPI
from pydantic import BaseModel
from core.LatticeLexico import Lexico
from core.LatticeSintactico import Sintactico
from core.errores import LatticeError

app = FastAPI(
    title="LatticeEncrypt",
    description="API para ejecutar programas del lenguaje LatticeEncrypt",
    version="1"
)

class CodigoRequest(BaseModel):
    codigo: str

@app.get("/")
def inicio():
    return {
        "lenguaje": "LatticeEncrypt",
        "version": "vLatticeEncrypt1",
        "estado": "En desarrollo"
    }

@app.post("/iniciar")
def ejecutar_codigo(request: CodigoRequest):
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
