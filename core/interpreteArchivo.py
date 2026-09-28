import contextlib
import io
import os

from core.LatticeLexico import Lexico
from core.LatticeSintactico import Sintactico
from core.errores import LatticeError


EXTENSION = ".le"

# Cuantas lineas de cada linea ejecutada se guardan como historial. Sin tope
# un programa largo devuelve un JSON enorme; con tope se pierde contexto.
MAX_TOKENS_POR_LINEA = 400

# ``ejecutar_linea`` imprime con print(). La API necesita recuperar ese texto
# en vez de que se mezcle con el log del servidor, asi que se sustituye
# ``sys.stdout`` por un buffer. Es una operacion sobre el proceso y por eso no
# es segura entre hilos: el endpoint de ejecucion la corre en el hilo de
# peticiones por defecto, siempre uno a la vez. Si alguna vez se usa el
# ThreadPoolExecutor, hay que mover esto a un lock.
_buffer = io.StringIO()


def _serializar(valor):
    """Convierte un resultado del interprete en algo que viaje por JSON."""
    if isinstance(valor, (list, tuple)):
        return [_serializar(v) for v in valor]
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, (int, float, str)) or valor is None:
        return valor
    return repr(valor)


def ejecutar_linea(texto):
    """Interpreta una instruccion y devuelve su resultado.

    Si la instruccion no es valida se propaga una excepcion de core.errores
    (subclase de LatticeError) en lugar de devolver un valor centinela:
    devolver True ante un error seria indistinguible de una respuesta real
    True de IGUAL. Quien llama decide como informar del error.

    El ``print`` de diagnostico se mantiene para el REPL de Runner.py, que es
    donde se lee a mano. Quien quiera solo el valor llama a ``evaluar``.
    """
    texto = texto.strip()
    if not texto:
        return None
    analizadorLexico = Lexico()
    tokens = analizadorLexico.tokenizar(texto)
    print("Tokens:", tokens)
    analizador = Sintactico(tokens)
    resultado = analizador.analisisSintactico()
    print("Resultado:", resultado)
    return resultado


def evaluar(texto, mostrar_tokens=True):
    """Como ``ejecutar_linea`` pero devuelve ``(resultado, tokens)``.

    A diferencia de ``ejecutar_linea`` no imprime nada: quien llama decide si
    quiere el diagnostico en la consola. Por eso el ``mostrar_tokens`` solo
    controla si se Imprimen los tokens, que si se hace al interpretarlos, y no
    si se devuelven (eso lo decide el endpoint).
    """
    texto = texto.strip()
    if not texto:
        return None, []
    tokens = Lexico().tokenizar(texto)
    if mostrar_tokens:
        print("Tokens:", tokens)
    resultado = Sintactico(tokens).analisisSintactico()
    return resultado, tokens


def ejecutar_programa(texto, mostrar_tokens=True):
    """Interpreta un programa completo linea por linea y lo devuelve estructurado.

    Un error no detiene el script, igual que en ``ejecutar_archivo``: se anota
    en la linea que fallo y se sigue. Asi una sola instruccion mal escrita no
    oculta el resultado de las demas.

    Devuelve ``consola``, que es lo que el interprete imprima por stdout, mas
    ``lineas`` con el detalle de cada instruccion ejecutada.
    """
    _buffer.seek(0)
    _buffer.truncate(0)

    with contextlib.redirect_stdout(_buffer):
        lineas = []
        for numero, linea in enumerate(texto.splitlines(), start=1):
            if not linea.strip():
                continue
            registro = {"linea": numero, "codigo": linea.strip(), "ok": True}
            try:
                resultado, tokens = evaluar(linea, mostrar_tokens=mostrar_tokens)
                registro["resultado"] = _serializar(resultado)
                if mostrar_tokens:
                    registro["tokens"] = [t.to_json() for t in tokens[:MAX_TOKENS_POR_LINEA]]
                    registro["tokens_recortados"] = len(tokens) > MAX_TOKENS_POR_LINEA
            except LatticeError as error:
                registro["ok"] = False
                registro["error"] = str(error)
                registro["tipo"] = type(error).__name__
            except Exception as error:  # noqa: BLE001 - bug real, no error del lenguaje
                registro["ok"] = False
                registro["error"] = f"Error interno: {error}"
                registro["tipo"] = type(error).__name__
            lineas.append(registro)

        consola = _buffer.getvalue()

    return {
        "consola": consola,
        "lineas": lineas,
        "errores": sum(1 for l in lineas if not l["ok"]),
    }


def ejecutar_archivo(ruta):
    """Interpreta un archivo .le linea por linea.

    Un error en una linea no detiene el script: se informa y se sigue con la
    siguiente. Devuelve el resultado de la ultima linea ejecutada con exito,
    o None si ninguna lo fue.
    """
    if not os.path.exists(ruta):
        print(f"Error: el archivo '{ruta}'")
        return None
    if not ruta.lower().endswith(EXTENSION):
        print(f"Error: el archivo debe tener la extension {EXTENSION}")
        return None
    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            lineas = archivo.readlines()
    except (OSError, UnicodeDecodeError) as error:
        print(f"Error leyendo el archivo {error}")
        return None

    # Verificar si todas las líneas están vacías
    if not any(linea.strip() for linea in lineas):
        print("No hay nada")
        return None

    print(f"Ejecutando archivo: {ruta}")
    resultado = None
    errores = 0

    for num, linea in enumerate(lineas, start=1):
        linea = linea.strip()
        if not linea:
            continue

        print(f"\n--- Línea {num}: {linea} ---")
        try:
            resultado = ejecutar_linea(linea)
        except LatticeError as error:
            errores += 1
            print(f"Error en la línea {num}: {error}")

    if errores:
        print(f"\nEl archivo terminó con {errores} error(es).")

    return resultado
