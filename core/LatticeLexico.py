import re
from core.Token import Token
from core.errores import LatticeSyntaxError

ESCAPES = {
    "n": "\n",
    "t": "\t",
    "r": "\r",
    "\\": "\\",
    '"': '"',
    "'": "'",
}

class Lexico:
    def __init__(self):
        # Diccionario de símbolos matemáticos y puntuación
        self.simbolos = {
            "+": "SUMA",
            "-": "RESTA",
            "=": "IGUAL",
            "*": "POR",
            "(": "IPAREN",
            ")": "DPAREN",
            "[": "ICORCH",
            "]": "DCORCH",
            "{": "ILLAVE",
            "}": "DLLAVE",
            ".": "PUNTO",
            ",": "COMA",
            ":": "DOSPUNTOS",
            ";": "PUNTILLO",
            "\"": "COMILLA",
            "'": "APOSTROFE",
            "!": "EXCLAMACION",
            "%": "PORCENTAJE",
            "/": "DIVISION",
            "<": "MENOR",
            ">": "MAYOR"
        }

        # Diccionario de palabras reservadas
        self.palabras_reservadas = {
            "M": "MATRIZ",
            "MM": "MATRIZ_PRIVADA",
            "V": "VECTOR",
            "RUIDO": "RUIDO",
            "TEXTO": "TEXTO",
            "CARACTERES": "CARACTERES",
            "KEYGEN": "KEYGEN",
            "CIFRAR": "CIFRAR",
            "DESCIFRAR": "DESCIFRAR",
            "R": "RUIDO",
            "C": "CIFRADO",
            "def": "DEFINIR",
            "return": "RETORNAR",
            "for": "PARA",
            "in": "EN",
            "range": "RANGO",
            "len": "LONGITUD",
            "while": "MIENTRAS",
            "if": "SI",
            "else": "SINO",
            "append": "AGREGAR",
            "round": "REDONDEAR",
            "ord": "ORDINAL",
            "chr": "CARACTER",
            "int": "ENTERO",
            "random": "ALEATORIO",
            "randint": "ENTERO_ALEATORIO"
        }

    def tokenizar(self, texto):
        tokens = []
        i = 0
        n = len(texto)
        
        while i < n:
            char = texto[i]

            # Ignorar espacios en blanco
            if char.isspace():
                i += 1
                continue

            # Leer cadenas literales. Van antes que las letras y los símbolos
            # porque su contenido es opaco al resto del analizador: dentro de
            # las comillas los espacios se conservan, las minúsculas son
            # válidas y los paréntesis no son delimitadores. Sin este modo,
            # 'TEXTO "Hola mundo"' fallaba al aplicar sobre la palabra 'Hola'
            # la validación de mayúsculas de las instrucciones.
            if char in ('"', "'"):
                comilla = char
                i += 1
                buffer = []
                while i < n and texto[i] != comilla:
                    if texto[i] == "\\" and i + 1 < n:
                        buffer.append(ESCAPES.get(texto[i + 1], "\\" + texto[i + 1]))
                        i += 2
                        continue
                    buffer.append(texto[i])
                    i += 1

                if i >= n:
                    raise LatticeSyntaxError(
                        f"Cadena sin cerrar: falta la comilla de cierre {comilla}."
                    )

                i += 1  # consumir la comilla de cierre
                tokens.append(Token("CADENA", "".join(buffer)))
                continue

            # Leer Letras (Palabras Reservadas)
            if char.isalpha():
                inicio = i
                # avanza mientras encuentra letras
                while i < n and texto[i].isalpha():
                    i += 1
                palabra = texto[inicio:i]  
                
                # Validacion estricta de mayusculas
                if not palabra.isupper():
                    raise LatticeSyntaxError(f"Error Léxico: La palabra '{palabra}' no es válida. Todas las instrucciones deben estar en MAYÚSCULAS.")
                    
                tokens.append(Token("PALABRA", palabra))
                continue
                
            # Leer números enteros y decimales    
            if char.isdigit():
                inicio = i 
                while i < n and (texto[i].isdigit() or texto[i] == "."):
                    i += 1
                numero = texto[inicio:i]
                tokens.append(Token("NUMERO", numero))
                continue

            # Leer Símbolos
            if char in self.simbolos:
                tokens.append(Token(self.simbolos[char], char))
                i += 1
                continue

            raise LatticeSyntaxError(f"Carácter inesperado: {char} en la posición {i}")
            
        return tokens

