from core.errores import LatticeTypeError

def revisarSintaxisComparacion(sintactico, lado_izquierdo, operador):
    """Maneja IGUAL (Igualdad exacta de vectores o matrices, solo verificación/testing)"""

    # Parseamos el lado derecho (El vector que va después de la palabra IGUAL)
    lado_derecho = sintactico.parsear_operando()

    # Lógica de comparación
    if operador == "IGUAL":
        # Igualdad exacta por componentes. Solo verificación/testing
        # (p. ej. DESCIFRAR(CIFRAR(m)) IGUAL m). No comparar secretos:
        # la igualdad ingenua filtra información por tiempo de ejecución.
        if isinstance(lado_izquierdo, tuple) and isinstance(lado_derecho, tuple):
            return lado_izquierdo[0] == lado_derecho[0] and lado_izquierdo[1] == lado_derecho[1]
        elif isinstance(lado_izquierdo, str) and isinstance(lado_derecho, str):
            return lado_izquierdo == lado_derecho
        elif isinstance(lado_izquierdo, list) and isinstance(lado_derecho, list):
            return (lado_izquierdo[0][0] == lado_derecho[0][0]
                    and lado_izquierdo[0][1] == lado_derecho[0][1]
                    and lado_izquierdo[1][0] == lado_derecho[1][0]
                    and lado_izquierdo[1][1] == lado_derecho[1][1])
        else:
            raise LatticeTypeError("Igualdad IGUAL requiere: VECTOR IGUAL VECTOR, MATRIZ IGUAL MATRIZ o TEXTO IGUAL TEXTO")
