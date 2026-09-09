import json
import importlib

class Sintactico:
    """Syntax analyzer (parser) for the Lattice language."""

    # Constructor      
    def __init__(self, tokens):
       self.tokens = tokens
       self.pos = 0

    # Metodo que retorna el token actual    
    def actual(self):
       if self.pos < len(self.tokens):
             return self.tokens[self.pos]
       return None

    # Metodo que consume el token actual si es del tipo esperado 
    def consumir(self, tipo):
        token = self.actual()        

        if token is None:   
            raise SyntaxError("No hay token")

        if token.tipo != tipo:
            raise SyntaxError(f"Se esperaba {tipo} y llegó {token.tipo} ({token.valor})")

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

    # --- DESPACHADOR CENTRAL ---
    def analisisSintactico(self):
        # 1. Leer el archivo de reglas JSON
        with open('reglas/reglas.json', 'r') as file:
            reglas = json.load(file)

        # 2. Leer el primer operando (Lado Izquierdo)
        tipo_operando = self.consumir("PALABRA").valor.upper()
        
        if tipo_operando == "VECTOR":
            lado_izquierdo = self.parsear_vector()
        elif tipo_operando == "MATRIZ":
            lado_izquierdo = self.parsear_matriz()
        else:
            raise SyntaxError(f"Tipo de operando inicial no reconocido: {tipo_operando}")

        # Si ya no hay mas tokens, retornamos el operando solo
        if self.actual() is None:
            return lado_izquierdo

        # 3. Leer el operador (ej. SUMA, POR, PUNTO)
        operador = self.consumir("PALABRA").valor.upper()

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
            raise SyntaxError(f"Operador no soportado o no definido en reglas.json: {operador}")

        # 5. Ejecutar la función dinámicamente importando el archivo desde la carpeta 'reglas'
        try:
            modulo = importlib.import_module(f"reglas.{archivo_a_importar}")
            funcion = getattr(modulo, metodo_a_llamar)
            # Pasamos `self` como primer argumento para que el archivo externo pueda usar consumir() y parsear()
            return funcion(self, lado_izquierdo, operador)
        except ModuleNotFoundError:
            raise ModuleNotFoundError(f"No se encontró el archivo reglas/{archivo_a_importar}.py definido en el JSON.")
        except AttributeError:
            raise AttributeError(f"El archivo reglas/{archivo_a_importar}.py no contiene la función {metodo_a_llamar}.")
