def revisarSintaxisAritmetica(sintactico, lado_izquierdo, operador):
    """Maneja RESTA (Resta de vectores) y MOD (Módulo por componentes)"""

    # Parseamos el lado derecho (El vector que va después de la palabra RESTA/MOD)
    tipo_derecho = sintactico.consumir("PALABRA").valor.upper()

    if tipo_derecho == "VECTOR":
        lado_derecho = sintactico.parsear_vector()
    elif tipo_derecho == "MATRIZ":
        lado_derecho = sintactico.parsear_matriz()
    else:
        raise SyntaxError(f"Tipo de operando derecho no reconocido: {tipo_derecho}")

    # Lógica de cálculo matemático
    if operador == "RESTA":
        # Resta de vectores (2D). Fundamental en LWE: el descifrado es b - <a, s>.
        if isinstance(lado_izquierdo, tuple) and isinstance(lado_derecho, tuple):
            return (lado_izquierdo[0] - lado_derecho[0], lado_izquierdo[1] - lado_derecho[1])
        else:
            raise TypeError("Resta RESTA requiere: VECTOR RESTA VECTOR")

    elif operador == "MOD":
        # Módulo por componentes. Base aritmética de LWE: b = A·s + e (mod q).
        if isinstance(lado_izquierdo, tuple) and isinstance(lado_derecho, tuple):
            if lado_derecho[0] == 0 or lado_derecho[1] == 0:
                raise ZeroDivisionError("Módulo MOD requiere divisores distintos de cero")
            return (lado_izquierdo[0] % lado_derecho[0], lado_izquierdo[1] % lado_derecho[1])
        else:
            raise TypeError("Módulo MOD requiere: VECTOR MOD VECTOR")
