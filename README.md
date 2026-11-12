# Interprete Lattice Encrypt

Interprete diseñado para ejecutar operaciones matematicas orientadas a la criptografia basada en reticulos (Lattice Cryptography), especificamente el algoritmo LWE (Learning With Errors). El lenguaje permite realizar operaciones sobre matrices y vectores, inyeccion de ruido, redondeo, conversion entre texto y vectores, variables y cifrado post-cuantico real de texto (`KEYGEN`, `CIFRAR`, `DESCIFRAR`).

## Ejemplos del lenguaje

```
VECTOR(1,2) SUMA VECTOR(3,4)
MATRIZ(2,0,0,2) POR VECTOR(3,4)
VECTOR(1,2) PUNTO VECTOR(3,4)
VECTOR(1,2) RUIDO VECTOR(1,-1)
VECTOR(1.4, 2.6) REDONDEAR
VECTOR(5,7) MOD VECTOR(2,3)
VECTOR(1,2) IGUAL VECTOR(1,2)
VECTOR(0,0) TEXTO "AB"
VECTOR(65,66) CARACTERES
```

El archivo `lattice.le` contiene un programa de ejemplo.

## Variables

Cualquier resultado se puede guardar con `NOMBRE = expresion` y reutilizar en las lineas siguientes. Los nombres van en mayusculas y pueden llevar digitos y `_` (`CLAVES2`, `MI_CLAVE`); no pueden ser palabras del lenguaje (`VECTOR`, `SUMA`, `KEYGEN`...).

```
A = VECTOR(1,2)
B = A SUMA VECTOR(3,4)
B RESTA A
```

Las variables duran un programa del editor web, un archivo `.le` o una sesion de la consola.

## Cifrado post-cuantico

```
CLAVES = KEYGEN
CIFRADO = TEXTO "HOLA" CIFRAR CLAVES
MENSAJE = CIFRADO DESCIFRAR CLAVES

CLAVES2 = KEYGEN MLKEM
ORIGINAL = TEXTO "Hola, ñandú"
C2 = ORIGINAL CIFRAR CLAVES2
M2 = C2 DESCIFRAR CLAVES2
M2 IGUAL ORIGINAL
```

La primera parte usa el LWE propio (FrodoPKE-640) y `MENSAJE` vale `"HOLA"`. La segunda usa el estandar NIST ML-KEM-768 y la ultima linea devuelve `True`. El lenguaje no tiene comentarios: cada linea es una instruccion.

*   `KEYGEN` genera las claves al azar con un generador criptografico (`os.urandom`); el usuario nunca escribe la matriz. `KEYGEN` sin modo equivale a `KEYGEN LWE`.
*   `CIFRAR` acepta texto de cualquier longitud (UTF-8) y usa solo la clave publica; `DESCIFRAR` usa solo la privada.
*   Al imprimir se ve un resumen (`<CLAVES ML-KEM-768>`, `<CIFRADO LWE FrodoPKE-640, 2 bloques, 20.2 KB>`), nunca el material de clave.
*   Descifrar con otra clave, o un criptograma alterado (en ML-KEM), da un error.
*   El archivo `cifrado.le` tiene el flujo completo en los dos modos.

### Que seguridad ofrece (y que no)

*   **Modo `MLKEM`**: ML-KEM-768, el estandar FIPS 203 de NIST (nivel 3), implementado por OpenSSL a traves de la libreria `cryptography`, combinado con HKDF-SHA256 y AES-256-GCM. Es seguro tambien frente a criptogramas manipulados (IND-CCA2).
*   **Modo `LWE`**: FrodoPKE con los parametros de FrodoKEM-640 (n = 640, q = 2^15), unos 128 bits de seguridad post-cuantica segun el analisis publicado de FrodoKEM. Es la matematica LWE implementada por el propio proyecto (`core/cripto/frodo.py`). Su seguridad es IND-CPA: protege contra quien escucha, **no** contra quien altera criptogramas, y es codigo propio sin auditar.
*   **Ninguno de los dos modos** protege contra ataques de canal lateral por tiempo de ejecucion en Python. Es un proyecto academico: no lo uses para proteger secretos reales.

## Estructura del Proyecto

*   **core/**: nucleo del interprete.
    *   `LatticeLexico.py`: Analizador Lexico (`Lexico`). Lee el texto caracter por caracter y lo agrupa en Tokens (palabras reservadas, numeros y simbolos).
    *   `LatticeSintactico.py`: Analizador Sintactico (`Sintactico`). Comprueba que los tokens cumplan la gramatica y despacha cada operacion a su modulo de `reglas/`.
    *   `Token.py`: estructura `Token` (tipo y valor) que viaja del lexico al sintactico.
    *   `interpreteArchivo.py`: ejecuta una linea o un archivo `.le` completo.
    *   `ejecutor.py`: ejecuta codigo capturando la salida; lo usa el servidor.
    *   `errores.py` y `utilidades.py`: manejo de errores y funciones auxiliares.
    *   `entorno.py`: tabla de simbolos (variables).
    *   `cripto/`: `frodo.py` (FrodoPKE-640), `mlkem.py` (ML-KEM-768 + AES-GCM) y `valores.py` (tipos de claves y criptogramas).
*   **reglas/**: operaciones del lenguaje, una categoria por archivo (`ReglasAritmetica.py`, `ReglasComparacion.py`, `ReglasRuido.py`, `ReglasTexto.py`, `ReglasLattice.py`).
    *   `reglas.json`: configuracion del despachador dinamico. Define que funcion valida cada grupo de operaciones.
*   **Runner.py**: consola interactiva del interprete.
*   **servidor.py**: API REST (FastAPI) y editor web.
*   **web/**: pagina del editor (`index.html`, `app.js`, `estilos.css`).
*   **tests/**: pruebas automaticas con pytest.
*   **docs/**: diagramas de arquitectura, secuencia y automatas (Markdown/Mermaid).
*   **Dockerfile**, **docker-compose.yml**, **render.yaml**: contenedor y despliegue.

## Uso

### Consola interactiva

```
python Runner.py
>> VECTOR(1,2) SUMA VECTOR(3,4)
>> ejecutar lattice.le
>> salir
```

### Ejecutable de escritorio

El ejecutable se genera con PyInstaller a partir de `lattice-encrypt.spec`:

```
pip install pyinstaller
pyinstaller lattice-encrypt.spec
```

El resultado queda en `dist/lattice-encrypt.exe`.

### Servidor web (API + editor)

```
pip install -r requirements.txt
uvicorn servidor:app --reload
```

*   `GET /`: nombre, version y estado del servicio.
*   `POST /iniciar`: recibe `{"codigo": "..."}` y devuelve el resultado y los tokens.
*   `POST /ejecutar`: ejecuta un programa completo (lo usa el editor).
*   `GET/POST/DELETE /api/programas`: listar, guardar y borrar programas.
*   `GET /editor`: editor web.
*   `GET /docs`: documentacion interactiva de la API.

Variables de entorno:

| Variable | Descripcion | Por defecto |
|---|---|---|
| `MODO_DEMO` | Con `1` se puede ejecutar pero no guardar ni borrar programas | desactivado |
| `TIEMPO_LIMITE` | Segundos maximos por ejecucion | `5` |
| `PROGRAMAS_DIR` | Carpeta donde se guardan los programas | `programas/` |
| `PORT` | Puerto del contenedor (lo usa Render) | `8000` |

### Docker

```
docker compose up --build
```

El servicio queda en `http://localhost:8000` y el editor en `http://localhost:8000/editor`.

### Despliegue en Render

`render.yaml` define el servicio (Docker, `MODO_DEMO=1`, health check en `/`). Los pasos estan en `despliegue-render-lattice-encrypt.md`.

## Pruebas

```
pip install -r requirements-dev.txt
python -m pytest -q
```

## Metodologia de Trabajo en Equipo

El proyecto utiliza un patron de despacho dinamico a traves de `reglas/reglas.json` para facilitar la extension del lenguaje sin causar conflictos. Cada miembro del equipo debe seguir estrictamente este flujo de trabajo (GitHub Flow):

1. **Sincronizar código local**: Antes de empezar a programar, asegurarse de tener la última versión del código base.
   * `git checkout main`
   * `git pull origin main`
2. **Crear una rama aislada**: Crear una rama descriptiva para la tarea a realizar.
   * `git checkout -b feature/nombre-de-categoria`
3. **Identificar la función**: Revisar el archivo `reglas/reglas.json` para ver qué nombre de método tocó implementar (ej. `revisarSintaxisRuido`). No es necesario modificar el JSON.
4. **Desarrollar la lógica**: Abrir el archivo correspondiente a la categoría dentro de la carpeta `reglas/` (ej. `reglas/ReglasRuido.py`). Escribir la lógica matemática dentro de la función que ya está definida allí. **No es necesario modificar `LatticeSintactico.py` ni `reglas.json`.**
5. **Subir los cambios (Commit & Push)**: Guardar los cambios con mensajes descriptivos y subirlos a la rama remota.
   * `git commit -m "feat: agrega operaciones de ruido"`
   * `git push origin feature/nombre-de-categoria`
6. **Pull Request (PR)**: Ir a GitHub y abrir un Pull Request hacia `main`. Solicitar la revisión de al menos un compañero antes de fusionar el código.
