from core.interpreteArchivo import ejecutar_archivo, ejecutar_linea

print("=== Intérprete Lattice Encrypt ===")
print("Escribe un comando o 'salir' para terminar).")
print("Ejemplos:")
print("  Leer un archivo -  ejecutar ..../file.le ")
print("  VECTOR(1,2) SUMA VECTOR(3,4)")
print("  MATRIZ(2,0,0,2) POR VECTOR(3,4)")
print("  VECTOR(1,2) PUNTO VECTOR(3,4)")
print("  VECTOR(1,2) RUIDO VECTOR(1,-1)")
print("  VECTOR(1,2) RUIDO")
print("  VECTOR(1.4, 2.6) REDONDEAR")
print("  VECTOR(3,4) RESTA VECTOR(1,2)")
print("  VECTOR(5,7) MOD VECTOR(2,3)")
print("  VECTOR(1,2) IGUAL VECTOR(1,2)")
print("  VECTOR(0,0) TEXTO \"AB\"")
print("  VECTOR(65,66) CARACTERES")
print("  MATRIZ(72,79,76,65) CARACTERES")

while True:
    try:
        texto = input("\n>> ")
        if texto.strip().lower() == "salir":
            break
        if not texto.strip():
            continue
        
        if texto.strip().startswith("ejecutar"):
            partes = texto.strip().split()
            if len(partes) > 1: # si hay una ruta
                ruta = partes[1] # agarra la ruta
                ejecutar_archivo(ruta)
            else:
                print("Error: Debes proporcionar la ruta del archivo (ej. ejecutar archivo.le)")
            continue

        ejecutar_linea(texto)

    except Exception as e:
        print(f"Error: {e}")
