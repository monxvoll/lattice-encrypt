from core.errores import LatticeTypeError

def revisarSintaxisBase(sintactico, lado_izquierdo, operador):
    """Maneja SUMA, POR (Multiplicación Matriz*Vector) y PUNTO (Producto Punto)"""
    
    # Parseamos el lado derecho (El vector o matriz que va después de la palabra SUMA/POR/PUNTO)
    lado_derecho = sintactico.parsear_operando()

    # Lógica de cálculo matemático
    if operador == "SUMA":
        # Suma de vectores (2D)
        if isinstance(lado_izquierdo, tuple) and isinstance(lado_derecho, tuple):
            return (lado_izquierdo[0] + lado_derecho[0], lado_izquierdo[1] + lado_derecho[1])
        raise LatticeTypeError("Suma SUMA requiere: VECTOR SUMA VECTOR")
        
    elif operador == "POR":
        # Multiplicación Matriz 2x2 por Vector 2x1
        if isinstance(lado_izquierdo, list) and isinstance(lado_derecho, tuple):
            r1 = lado_izquierdo[0][0] * lado_derecho[0] + lado_izquierdo[0][1] * lado_derecho[1]
            r2 = lado_izquierdo[1][0] * lado_derecho[0] + lado_izquierdo[1][1] * lado_derecho[1]
            return (r1, r2)
        else:
            raise LatticeTypeError("Multiplicación POR requiere: MATRIZ POR VECTOR")

    elif operador == "PUNTO":
        # Producto Punto de dos Vectores
        if isinstance(lado_izquierdo, tuple) and isinstance(lado_derecho, tuple):
            return lado_izquierdo[0] * lado_derecho[0] + lado_izquierdo[1] * lado_derecho[1]
        else:
            raise LatticeTypeError("Producto PUNTO requiere: VECTOR PUNTO VECTOR")
