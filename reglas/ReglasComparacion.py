from core.errores import LatticeSyntaxError, LatticeTypeError

def revisarSintaxisComparacion(sintactico, lado_izquierdo, operador):
    """Maneja IGUAL (Igualdad exacta de vectores o matrices, solo verificación/testing)"""

    # Parseamos el lado derecho (El vector que va después de la palabra IGUAL)
    tipo_derecho = sintactico.consumir("PALABRA").valor.upper()

    if tipo_derecho == "VECTOR":
        lado_derecho = sintactico.parsear_vector()
    elif tipo_derecho == "MATRIZ":
        lado_derecho = sintactico.parsear_matriz()
    else:
        raise LatticeSyntaxError(f"Tipo de operando derecho no reconocido: {tipo_derecho}")

    # Lógica de comparación
    if operador == "IGUAL":
        # Igualdad exacta por componentes. Solo verificación/testing
        # (p. ej. DESCIFRAR(CIFRAR(m)) IGUAL m). No comparar secretos:
        # la igualdad ingenua filtra información por tiempo de ejecución.
        if isinstance(lado_izquierdo, tuple) and isinstance(lado_derecho, tuple):
            return lado_izquierdo[0] == lado_derecho[0] and lado_izquierdo[1] == lado_derecho[1]
        elif isinstance(lado_izquierdo, list) and isinstance(lado_derecho, list):
            return (lado_izquierdo[0][0] == lado_derecho[0][0]
                    and lado_izquierdo[0][1] == lado_derecho[0][1]
                    and lado_izquierdo[1][0] == lado_derecho[1][0]
                    and lado_izquierdo[1][1] == lado_derecho[1][1])
        else:
            raise LatticeTypeError("Igualdad IGUAL requiere: VECTOR IGUAL VECTOR o MATRIZ IGUAL MATRIZ")
