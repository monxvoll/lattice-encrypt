import sys
import os

from core.LatticeLexico import Lexico
from core.LatticeSintactico import Sintactico


EXTENSION = ".le"

def ejecutar_linea(texto):
    texto = texto.strip()
    if not texto:
        return True
    try:
        analizadorLexico = Lexico()
        tokens = analizadorLexico.tokenizar(texto)
        print("Tokens:", tokens)
        analizador = Sintactico(tokens)
        resultado = analizador.analisisSintactico()
        print("Resultado:", resultado)
        return resultado
    except SyntaxError as error:
        print(f"Error de sintaxis: {error}")
        return True


def ejecutar_archivo(ruta):
    if not os.path.exists(ruta):
        print(f"Error: el archivo '{ruta}'")
        return False
    if not ruta.lower().endswith(EXTENSION):
        print(f"Error: el archivo debe tener la extension {EXTENSION}")
        return False
    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            lineas = archivo.readlines()
    except Exception as error:
        print(f"Error leyendo el archivo {error}")
        return False
    
    # Verificar si todas las líneas están vacías
    if not any(linea.strip() for linea in lineas):
        print("No hay nada")
        return False
        
    print(f"Ejecutando archivo: {ruta}")
    resultado = None
    
    for num, linea in enumerate(lineas, start=1):
        linea = linea.strip()
        if not linea:
            continue
            
        print(f"\n--- Línea {num}: {linea} ---")
        resultado = ejecutar_linea(linea)
        
    return resultado

