def revisarSintaxisTexto(sintactico, lado_izquierdo, operador):
    """Maneja las operaciones TEXTO y CARACTERES"""
    
    if operador == "TEXTO":
        # Sintaxis esperada: VECTOR(0,0) TEXTO "AB" o MATRIZ(0,0,0,0) TEXTO "HOLA"
        comilla = sintactico.actual()
        if not comilla or comilla.tipo not in ["COMILLA", "APOSTROFE"]:
            raise SyntaxError("Se esperaba una cadena de texto entre comillas")
        
        tipo_comilla = comilla.tipo
        sintactico.consumir(tipo_comilla)
        
        texto = ""
        # Leer todo hasta la comilla de cierre
        while sintactico.actual() and sintactico.actual().tipo != tipo_comilla:
            texto += str(sintactico.consumir(sintactico.actual().tipo).valor)
            
        sintactico.consumir(tipo_comilla)
        
        if len(texto) == 2:
            return (float(ord(texto[0])), float(ord(texto[1])))
        elif len(texto) == 4:
            return [
                [float(ord(texto[0])), float(ord(texto[1]))],
                [float(ord(texto[2])), float(ord(texto[3]))]
            ]
        else:
            raise ValueError(f"El texto debe tener 2 caracteres para VECTOR o 4 para MATRIZ. Texto recibido: {texto}")
            
    elif operador == "CARACTERES":
        if isinstance(lado_izquierdo, tuple):
            return chr(int(round(lado_izquierdo[0]))) + chr(int(round(lado_izquierdo[1])))
        elif isinstance(lado_izquierdo, list):
            return chr(int(round(lado_izquierdo[0][0]))) + chr(int(round(lado_izquierdo[0][1]))) + chr(int(round(lado_izquierdo[1][0]))) + chr(int(round(lado_izquierdo[1][1])))
        else:
            raise TypeError("CARACTERES requiere un VECTOR o MATRIZ")
