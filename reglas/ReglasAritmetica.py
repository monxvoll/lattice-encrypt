from core.errores import LatticeTypeError, LatticeDivisionError

def revisarSintaxisAritmetica(sintactico, lado_izquierdo, operador):
    """Maneja RESTA (Resta de vectores) y MOD (Módulo por componentes)"""

    # Parseamos el lado derecho (El vector que va después de la palabra RESTA/MOD)
    lado_derecho = sintactico.parsear_operando()

    # Lógica de cálculo matemático
    if operador == "RESTA":
        # Resta de vectores (2D). Fundamental en LWE: el descifrado es b - <a, s>.
        if isinstance(lado_izquierdo, tuple) and isinstance(lado_derecho, tuple):
            return (lado_izquierdo[0] - lado_derecho[0], lado_izquierdo[1] - lado_derecho[1])
        else:
            raise LatticeTypeError("Resta RESTA requiere: VECTOR RESTA VECTOR")

    elif operador == "MOD":
        # Módulo por componentes. Base aritmética de LWE: b = A·s + e (mod q).
        if isinstance(lado_izquierdo, tuple) and isinstance(lado_derecho, tuple):
            if lado_derecho[0] == 0 or lado_derecho[1] == 0:
                raise LatticeDivisionError("Módulo MOD requiere divisores distintos de cero")
            return (lado_izquierdo[0] % lado_derecho[0], lado_izquierdo[1] % lado_derecho[1])
        else:
            raise LatticeTypeError("Módulo MOD requiere: VECTOR MOD VECTOR")
