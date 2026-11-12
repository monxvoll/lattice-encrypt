import json
import os
import importlib

from core.entorno import Entorno
from core.errores import LatticeSyntaxError

# La configuracion de reglas se resuelve desde la ubicacion de este archivo y se
# lee una sola vez al importar el modulo. Antes se abria 'reglas/reglas.json'
# con una ruta relativa al directorio de trabajo, lo que rompia al arrancar el
# interprete o el servidor fuera de la raiz del proyecto y ademas releia el
# disco en cada instruccion.
_RAIZ_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_RUTA_REGLAS = os.path.join(_RAIZ_PROYECTO, 'reglas', 'reglas.json')

with open(_RUTA_REGLAS, 'r', encoding='utf-8') as _archivo_reglas:
    _REGLAS = json.load(_archivo_reglas)

# Nombres que no pueden usarse como variable: las palabras con las que se
# construyen operandos y todos los operadores declarados en reglas.json.
PALABRAS_RESERVADAS = frozenset(
    {"VECTOR", "MATRIZ", "TEXTO", "KEYGEN", "LWE", "MLKEM"}
    | {
        operador
        for grupo in _REGLAS
        for valores in grupo.values()
        if isinstance(valores, list)
        for operador in valores
    }
)


class Sintactico:
    """Syntax analyzer (parser) for the Lattice language."""

    # Constructor      
    def __init__(self, tokens, entorno=None):
       self.tokens = tokens
       self.pos = 0
       self.entorno = entorno if entorno is not None else Entorno()

    # Metodo que retorna el token actual    
    def actual(self):
       if self.pos < len(self.tokens):
             return self.tokens[self.pos]
       return None

    # Metodo que consume el token actual si es del tipo esperado 
    def consumir(self, tipo):
        token = self.actual()        

        if token is None:   
            raise LatticeSyntaxError("No hay token")

        if token.tipo != tipo:
            raise LatticeSyntaxError(f"Se esperaba {tipo} y llegó {token.tipo} ({token.valor})")

        self.pos = self.pos + 1
        return token   

    def parsear_numero(self):
        """Helper para parsear un número, permitiendo signos negativos"""
        token = self.actual()
        multiplicador = 1
        if token and token.tipo == "RESTA":
            self.consumir("RESTA")
            multiplicador = -1
            
        num_token = self.consumir("NUMERO")
        return float(num_token.valor) * multiplicador

    # --- HELPERS PARA PARSEAR ESTRUCTURAS ---
    def parsear_vector(self):
        """Parsea un vector 2D en formato: (n1, n2)"""
        self.consumir("IPAREN")
        n1 = self.parsear_numero()
        self.consumir("COMA")
        n2 = self.parsear_numero()
        self.consumir("DPAREN")
        return (n1, n2)

    def parsear_matriz(self):
        """Parsea una matriz 2x2 en formato: (m1, m2, m3, m4)"""
        self.consumir("IPAREN")
        m1 = self.parsear_numero()
        self.consumir("COMA")
        m2 = self.parsear_numero()
        self.consumir("COMA")
        m3 = self.parsear_numero()
        self.consumir("COMA")
        m4 = self.parsear_numero()
        self.consumir("DPAREN")
        return [
            [m1, m2],
            [m3, m4]
        ]

    def parsear_operando(self):
        """Lee un operando: VECTOR(...), MATRIZ(...) o el nombre de una variable.

        Devuelve el valor tal cual; cada regla valida si el tipo le sirve.
        """
        token = self.actual()
        if token is None:
            raise LatticeSyntaxError("Falta un operando")
        if token.tipo != "PALABRA":
            raise LatticeSyntaxError(f"Tipo de operando no reconocido: {token.valor}")
        nombre = self.consumir("PALABRA").valor.upper()
        if nombre == "VECTOR":
            return self.parsear_vector()
        if nombre == "MATRIZ":
            return self.parsear_matriz()
        if nombre in PALABRAS_RESERVADAS:
            raise LatticeSyntaxError(f"Tipo de operando no reconocido: {nombre}")
        return self.entorno.obtener(nombre)

    def _es_asignacion(self):
        return (
            len(self.tokens) >= 2
            and self.tokens[0].tipo == "PALABRA"
            and self.tokens[1].tipo == "IGUAL"
        )

    # --- DESPACHADOR CENTRAL ---
    def analisisSintactico(self):
        """Evalua una instruccion, con asignacion opcional: [NOMBRE =] expresion."""
        nombre = None
        if self._es_asignacion():
            nombre = self.consumir("PALABRA").valor
            self.consumir("IGUAL")
            if nombre in PALABRAS_RESERVADAS:
                raise LatticeSyntaxError(
                    f"'{nombre}' es una palabra reservada y no puede usarse como variable"
                )
            if self.actual() is None:
                raise LatticeSyntaxError("Falta la expresion despues de '='")

        valor = self._expresion()

        sobrante = self.actual()
        if sobrante is not None:
            raise LatticeSyntaxError(f"Sobra texto al final de la instruccion: {sobrante.valor}")

        if nombre is not None:
            self.entorno.definir(nombre, valor)
        return valor

    def _expresion(self):
        # 1. Leer el archivo de reglas JSON (ya cargado en el import del modulo)
        reglas = _REGLAS

        # 2. Leer el primer operando (Lado Izquierdo). TEXTO "..." al inicio
        # produce un mensaje (str) de cualquier longitud.
        token = self.actual()
        if token is not None and token.tipo == "PALABRA" and token.valor == "KEYGEN":
            return self._keygen()
        siguiente = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
        if (token is not None and token.tipo == "PALABRA" and token.valor == "TEXTO"
                and siguiente is not None and siguiente.tipo == "CADENA"):
            self.consumir("PALABRA")
            lado_izquierdo = self.consumir("CADENA").valor
        else:
            lado_izquierdo = self.parsear_operando()

        # Si ya no hay mas tokens, retornamos el operando solo
        if self.actual() is None:
            return lado_izquierdo

        # 3. Leer el operador (ej. SUMA, POR, PUNTO)
        operador = self.consumir("PALABRA").valor.upper()
        if operador == "KEYGEN":
            raise LatticeSyntaxError("KEYGEN no lleva operandos: usa NOMBRE = KEYGEN [LWE|MLKEM]")

        # 4. Despachador: Buscar en el JSON a qué grupo pertenece el operador
        archivo_a_importar = None
        metodo_a_llamar = None
        
        for grupo in reglas:
            for key, valores_permitidos in grupo.items():
                if isinstance(valores_permitidos, list) and operador in valores_permitidos:
                    archivo_a_importar = grupo["Archivo"]
                    metodo_a_llamar = grupo["EjecutarRegla"]
                    break
            if metodo_a_llamar:
                break

        if not metodo_a_llamar or not archivo_a_importar:
            raise LatticeSyntaxError(f"Operador no soportado o no definido en reglas.json: {operador}")

        # 5. Ejecutar la función dinámicamente importando el archivo desde la carpeta 'reglas'.
        # La llamada queda fuera del try: un AttributeError o ModuleNotFoundError
        # que ocurra DENTRO de la regla no debe reportarse como "falta el archivo".
        try:
            modulo = importlib.import_module(f"reglas.{archivo_a_importar}")
        except ModuleNotFoundError:
            raise ModuleNotFoundError(f"No se encontró el archivo reglas/{archivo_a_importar}.py definido en el JSON.")
        funcion = getattr(modulo, metodo_a_llamar, None)
        if funcion is None:
            raise AttributeError(f"El archivo reglas/{archivo_a_importar}.py no contiene la función {metodo_a_llamar}.")
        # Pasamos `self` como primer argumento para que el archivo externo pueda usar consumir() y parsear()
        return funcion(self, lado_izquierdo, operador)

    def _keygen(self):
        """KEYGEN [LWE | MLKEM]: genera un par de claves (LWE por defecto)."""
        self.consumir("PALABRA")
        modo = "LWE"
        token = self.actual()
        if token is not None and token.tipo == "PALABRA" and token.valor in ("LWE", "MLKEM"):
            modo = self.consumir("PALABRA").valor
        # Import diferido: el cifrado (numpy, cryptography) solo se carga si se usa.
        from reglas.ReglasLattice import generar_claves
        return generar_claves(modo)
