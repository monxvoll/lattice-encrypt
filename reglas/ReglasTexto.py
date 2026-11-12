from core.errores import LatticeSyntaxError, LatticeTypeError, LatticeValueError
from core.utilidades import redondear_lattice

def _caracter(valor):
    """chr() con error del lenguaje para codigos fuera del rango Unicode."""
    codigo = redondear_lattice(valor)
    if not 0 <= codigo <= 0x10FFFF:
        raise LatticeValueError(f"El codigo {codigo} no es un caracter Unicode valido")
    return chr(codigo)


def revisarSintaxisTexto(sintactico, lado_izquierdo, operador):
    """Maneja las operaciones TEXTO y CARACTERES"""
    
    if operador == "TEXTO":
        # Sintaxis esperada: VECTOR(0,0) TEXTO "AB" o MATRIZ(0,0,0,0) TEXTO "HOLA"
        if not isinstance(lado_izquierdo, (tuple, list)):
            raise LatticeTypeError('TEXTO como operador requiere un VECTOR o MATRIZ: VECTOR(0,0) TEXTO "AB"')
        # El lexer ya entrega el contenido entre comillas como un único token
        # CADENA, con los espacios y las minúsculas intactos.
        cadena = sintactico.actual()
        if not cadena or cadena.tipo != "CADENA":
            raise LatticeSyntaxError("Se esperaba una cadena de texto entre comillas")

        sintactico.consumir("CADENA")
        texto = cadena.valor

        if len(texto) == 2:
            return (float(ord(texto[0])), float(ord(texto[1])))
        elif len(texto) == 4:
            return [
                [float(ord(texto[0])), float(ord(texto[1]))],
                [float(ord(texto[2])), float(ord(texto[3]))]
            ]
        else:
            raise LatticeValueError(f"El texto debe tener 2 caracteres para VECTOR o 4 para MATRIZ. Texto recibido: {texto}")
            
    elif operador == "CARACTERES":
        if isinstance(lado_izquierdo, tuple):
            return _caracter((lado_izquierdo[0])) + _caracter((lado_izquierdo[1]))
        elif isinstance(lado_izquierdo, list):
            return (_caracter((lado_izquierdo[0][0]))
                    + _caracter((lado_izquierdo[0][1]))
                    + _caracter((lado_izquierdo[1][0]))
                    + _caracter((lado_izquierdo[1][1])))
        else:
            raise LatticeTypeError("CARACTERES requiere un VECTOR o MATRIZ")
