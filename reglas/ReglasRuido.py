import random

from core.errores import LatticeSyntaxError, LatticeTypeError
from core.utilidades import redondear_lattice

def revisarSintaxisRuido(sintactico, lado_izquierdo, operador):
    """Maneja las operaciones RUIDO y REDONDEAR"""
    
    if operador == "RUIDO":

        if sintactico.actual() is not None:

            tipo_derecho = sintactico.consumir("PALABRA").valor.upper()
            if tipo_derecho == "VECTOR":
                ruido = sintactico.parsear_vector()
                if isinstance(lado_izquierdo, tuple):
                    return (lado_izquierdo[0] + ruido[0], lado_izquierdo[1] + ruido[1])
                else:
                    raise LatticeTypeError("RUIDO con VECTOR requiere un VECTOR como operando izquierdo")
            elif tipo_derecho == "MATRIZ":
                ruido = sintactico.parsear_matriz()
                if isinstance(lado_izquierdo, list):
                    return [
                        [lado_izquierdo[0][0] + ruido[0][0], lado_izquierdo[0][1] + ruido[0][1]],
                        [lado_izquierdo[1][0] + ruido[1][0], lado_izquierdo[1][1] + ruido[1][1]]
                    ]
                else:
                    raise LatticeTypeError("RUIDO con MATRIZ requiere una MATRIZ como operando izquierdo")
            else:
                raise LatticeSyntaxError(f"Tipo de operando derecho no reconocido: {tipo_derecho}")
        else:
    
            if isinstance(lado_izquierdo, tuple):
                ruido_x = random.uniform(-0.5, 0.5)
                ruido_y = random.uniform(-0.5, 0.5)
                return (lado_izquierdo[0] + ruido_x, lado_izquierdo[1] + ruido_y)
            elif isinstance(lado_izquierdo, list):
                return [
                    [lado_izquierdo[0][0] + random.uniform(-0.5, 0.5), lado_izquierdo[0][1] + random.uniform(-0.5, 0.5)],
                    [lado_izquierdo[1][0] + random.uniform(-0.5, 0.5), lado_izquierdo[1][1] + random.uniform(-0.5, 0.5)]
                ]
            else:
                raise LatticeTypeError("RUIDO requiere un VECTOR o MATRIZ")
    
    elif operador == "REDONDEAR":

        if isinstance(lado_izquierdo, tuple):
            return (redondear_lattice(lado_izquierdo[0]), redondear_lattice(lado_izquierdo[1]))
        elif isinstance(lado_izquierdo, list):
            return [
                [redondear_lattice(lado_izquierdo[0][0]), redondear_lattice(lado_izquierdo[0][1])],
                [redondear_lattice(lado_izquierdo[1][0]), redondear_lattice(lado_izquierdo[1][1])]
            ]
        else:
            raise LatticeTypeError("REDONDEAR requiere un VECTOR o MATRIZ")