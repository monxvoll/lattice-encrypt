import os

from core.LatticeLexico import Lexico
from core.LatticeSintactico import Sintactico
from core.errores import LatticeError


EXTENSION = ".le"

def ejecutar_linea(texto):
    """Interpreta una instruccion y devuelve su resultado.

    Si la instruccion no es valida se propaga una excepcion de core.errores
    (subclase de LatticeError) en lugar de devolver un valor centinela:
    devolver True ante un error seria indistinguible de una respuesta real
    True de IGUAL. Quien llama decide como informar del error.
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
