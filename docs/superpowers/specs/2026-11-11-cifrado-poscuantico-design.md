# Diseño: cifrado post-cuántico en Lattice Encrypt (KEYGEN / CIFRAR / DESCIFRAR)

Fecha: 2026-11-11 · Rama: `feature/cifrado-poscuantico` (sale de `feature/deploy-render`)

## 1. Intención

Lattice Encrypt promete cifrado resistente a computadoras cuánticas basado en retículos (LWE). Hoy `KEYGEN`, `CIFRAR` y `DESCIFRAR` se tokenizan y despachan, pero `reglas/ReglasLattice.py` está vacío.

El equipo quiere que el cifrado **sea seguro de verdad**, no una demostración con números de juguete, y que el profesor vea **las dos cosas**:

1. **El lenguaje hace la matemática él mismo**: un esquema LWE propio, implementado en el proyecto, con parámetros de tamaño real.
2. **El estándar oficial post-cuántico**: ML-KEM (FIPS 203 de NIST, antes Kyber), usado a través de una librería.

## 2. Cómo se ve en el lenguaje (acordado con el equipo)

```
CLAVES = KEYGEN                      # LWE propio (por defecto)
CIFRADO = TEXTO "HOLA" CIFRAR CLAVES
MENSAJE = CIFRADO DESCIFRAR CLAVES   # -> "HOLA"

CLAVES2 = KEYGEN MLKEM               # mismo flujo, con el estándar NIST
C2 = TEXTO "Hola mundo, ñandú" CIFRAR CLAVES2
M2 = C2 DESCIFRAR CLAVES2
```

- `CIFRAR` usa solo la parte pública de la clave; `DESCIFRAR` solo la privada.
- Al imprimir no se vuelcan claves ni criptogramas (son miles de números). Se muestra un resumen como `<CLAVES LWE FrodoPKE-640>` o `<CIFRADO ML-KEM-768, 1.1 KB>`.

## 3. Metas, no-metas y anti-metas

**Metas**
- Variables (asignación `NOMBRE = expresión`) que viven durante un programa, un archivo `.le` o una sesión del REPL.
- `KEYGEN [LWE | MLKEM]`, `CIFRAR` y `DESCIFRAR` para texto de cualquier longitud (UTF-8: tildes y `ñ` incluidas).
- Modo LWE con parámetros publicados y analizados por la comunidad (los de FrodoKEM-640, nivel 1 de NIST).
- Modo ML-KEM-768 (nivel 3 de NIST) + AES-256-GCM, que es como se usa en la práctica.
- Aleatoriedad criptográfica (`os.urandom` / `secrets`), nunca `random`.
- Funciona en consola (`Runner.py`), en archivos `.le`, en el editor web/API (dentro del `TIEMPO_LIMITE` de 5 s) y en Docker/Render.

**No-metas (por ahora)**
- Exportar o importar claves y criptogramas (a archivo, hex, base64) para intercambiarlos entre programas. Las claves viven en memoria durante la ejecución.
- Firmas digitales (ML-DSA), intercambio entre personas o un protocolo de red.
- Protección contra ataques de canal lateral (tiempos de ejecución): un intérprete en Python no puede garantizarla. Se documenta como limitación.
- Cambiar las operaciones 2D existentes (`SUMA`, `POR`, `RUIDO`, etc.). Siguen siendo la parte "didáctica" que muestra la matemática con números pequeños.

**Anti-metas (si pasa esto, fallamos aunque "funcione")**
- Que el usuario escriba la matriz de la clave a mano (`MATRIZ(3,1,2,4) KEYGEN ...`) y eso se presente como seguro.
- Usar `random` o `numpy.random` para claves, secretos o ruido.
- Que `KEYGEN MLKEM` caiga en silencio a otro algoritmo si la librería no soporta ML-KEM: debe fallar con un error claro.
- Que descifrar con la clave equivocada en modo ML-KEM devuelva basura en vez de un error.
- Afirmar en la documentación más seguridad de la que hay (ver §6).

## 4. Restricciones

- Python 3.12 en local y 3.13 en Docker (`python:3.13-slim`).
- El servidor corta cada ejecución a los 5 s (`TIEMPO_LIMITE`) en un proceso hijo creado con `spawn`. `KEYGEN` + `CIFRAR` + `DESCIFRAR` de un texto corto deben tardar bastante menos de 1 s.
- Arquitectura existente: despachador dinámico por `reglas/reglas.json` → `reglas/ReglasLattice.py::revisarSintaxisLattice(sintactico, lado_izquierdo, operador)`. Los errores del lenguaje son subclases de `LatticeError` (`core/errores.py`).
- Los 75 tests actuales deben seguir pasando.
- Nuevas dependencias (versiones fijadas en `requirements.txt`):
  - `numpy` (aritmética matricial del modo LWE).
  - `cryptography==50.0.2`: trae ML-KEM-768 nativo (`cryptography.hazmat.primitives.asymmetric.mlkem`), además de AES-GCM y HKDF. **Verificado** en Windows / Python 3.12 en un entorno aislado: genera, encapsula y desencapsula bien. Existen ruedas `manylinux_2_28_x86_64` de `cryptography` 50.0.2 y de `numpy` para Python 3.13, así que el build de Docker debería instalarlas; falta comprobar ML-KEM dentro del contenedor. La versión 46.0.5 que hay instalada en local no sirve.

## 5. Decisiones de diseño

### 5.1 Gramática (cambios sobre CONTEXTO_PROYECTO.md §5)

```ebnf
Linea         ::= [ Identificador "=" ] Instruccion
Instruccion   ::= Generacion | Operacion | Operando
Generacion    ::= "KEYGEN" [ "LWE" | "MLKEM" ]
Operando      ::= VectorLiteral | MatrizLiteral | Identificador | Mensaje
Mensaje       ::= "TEXTO" CadenaLiteral          (* solo como operando inicial *)
OperacionLattice ::= Operando "CIFRAR" Identificador
                   | Operando "DESCIFRAR" Identificador
Identificador ::= Mayuscula { Mayuscula | Digito | "_" }   (* no puede ser palabra reservada *)
```

- `TEXTO` mantiene su uso actual como operador (`VECTOR(0,0) TEXTO "AB"`). Cuando aparece **al inicio** de la instrucción seguido de una cadena, produce un mensaje (`str`) de cualquier longitud.
- El `=` ya se tokeniza como `IGUAL` de tipo símbolo, distinto de la palabra `IGUAL` (tipo `PALABRA`). La asignación se reconoce como `PALABRA` seguida de un token de tipo `IGUAL`.
- **Léxico**: hoy una palabra son solo letras, así que `CLAVES2` se parte en `CLAVES` + `2`. Se amplía para que, tras la primera letra, admita letras, dígitos y `_`. La validación de mayúsculas se mantiene.
- **Palabras reservadas** (no válidas como nombre de variable): `VECTOR`, `MATRIZ`, `TEXTO`, `KEYGEN`, `LWE`, `MLKEM`, `CIFRAR`, `DESCIFRAR` y todos los operadores de `reglas.json`.

### 5.2 Variables / tabla de símbolos
- Nueva clase `Entorno` (`core/entorno.py`) con `definir`, `obtener` y `existe`. `Sintactico` la recibe opcionalmente en el constructor.
- Duración del entorno:
  - REPL de `Runner.py`: toda la sesión.
  - `ejecutar_archivo`: un archivo.
  - `ejecutar_programa` (editor web / `POST /ejecutar`): un programa.
  - `POST /iniciar` y `evaluar` sueltos: entorno nuevo por llamada.
- Una variable no definida lanza un nuevo `LatticeNameError(LatticeError, NameError)`.
- **Centralizar el operando derecho**: hoy cada `reglas/*.py` repite `if tipo == "VECTOR" ... elif "MATRIZ"`. Se crea `Sintactico.parsear_operando()` (VECTOR / MATRIZ / variable) y las reglas existentes pasan a usarlo. Así las variables funcionan en todas las operaciones (`A = VECTOR(1,2)` y luego `A SUMA A`).
- Una línea con asignación imprime el valor asignado igual que hoy (`Resultado: ...`).

### 5.3 Modo LWE propio: FrodoPKE-640
Se implementa el esquema de cifrado de clave pública **FrodoPKE** (la parte PKE de FrodoKEM) con los parámetros de **FrodoKEM-640**:

- n = 640, q = 2^15, n̄ = m̄ = 8, B = 2 bits por entrada → 128 bits (16 bytes) por bloque.
- Distribución de error χ: la tabla CDF de FrodoKEM-640 (σ ≈ 2.8). El implementador debe copiarla de la especificación oficial de FrodoKEM y citar la fuente en el código.
- Algoritmo:
  - **KeyGen**: A ∈ Z_q^{n×n} uniforme; S, E ∈ χ^{n×n̄}; B = A·S + E. Clave pública (A, B), privada S. A puede guardarse entera (≈800 KB) o derivarse de una semilla con SHAKE-128 como en Frodo; lo decide el implementador.
  - **Enc(μ)**: S', E' ∈ χ^{m̄×n}; E'' ∈ χ^{m̄×n̄}; B' = S'·A + E'; V = S'·B + E''; C = V + Codificar(μ).
  - **Dec**: M = C − B'·S; μ = Decodificar(M), redondeando cada entrada al múltiplo más cercano de q/2^B.
- Texto de longitud arbitraria: UTF-8 → relleno con la longitud → bloques de 16 bytes, cada uno cifrado con aleatoriedad nueva.
- Aritmética con `numpy` (enteros, módulo q); el muestreo de χ, con bytes de `os.urandom`.

**Por qué Frodo y no un Regev "de libro":** es LWE puro con matrices (encaja con la temática del lenguaje), sus parámetros están publicados y analizados (fue finalista alterno en la competencia de NIST y está en proceso ISO), y con `numpy` corre en milisegundos.

### 5.4 Modo ML-KEM-768
- `KEYGEN MLKEM`: `MLKEM768PrivateKey.generate()`.
- `CIFRAR`: `encapsulate()` → secreto compartido → HKDF-SHA256 → clave AES-256 → AES-GCM con nonce aleatorio de 12 bytes. El criptograma guarda (ct_kem, nonce, ct_aes).
- `DESCIFRAR`: `decapsulate()` → mismo HKDF → AES-GCM. Si la clave es otra o el criptograma fue alterado, `InvalidTag` se traduce a `LatticeValueError("No se pudo descifrar: clave incorrecta o criptograma alterado")`.
- Si la librería instalada no tiene ML-KEM: `LatticeError` claro, sin caer a otro algoritmo.

### 5.5 Tipos de valor
- Nuevas clases en `reglas/ReglasLattice.py` (o en un módulo `core/cripto/`, a criterio del implementador): `ParClaves(modo, publica, privada)` y `Cifrado(modo, datos)`.
- Las dos tienen un `__repr__` resumido. `_serializar` en `interpreteArchivo.py` ya usa `repr` para lo desconocido, así que la API devuelve el resumen y nunca la clave.
- Combinaciones inválidas lanzan `LatticeTypeError` con un mensaje claro:
  - `CIFRAR` con algo que no es texto.
  - `DESCIFRAR` con algo que no es un `Cifrado`.
  - Mezclar modos (criptograma LWE con claves ML-KEM).
  - Usar como clave algo que no es `ParClaves`.

## 6. Qué seguridad se puede afirmar (y qué no)

Esto va así en el README y en la documentación:

- **Modo ML-KEM**: estándar FIPS 203, nivel 3 de NIST, implementado por OpenSSL a través de `cryptography`. Con AES-GCM es seguro también contra criptogramas manipulados (IND-CCA2).
- **Modo LWE (FrodoPKE-640)**: parámetros con unos 128 bits de seguridad post-cuántica según el análisis publicado de FrodoKEM. Es un PKE con seguridad IND-CPA: protege contra quien escucha, **no** contra quien altera criptogramas, porque no tiene la transformación Fujisaki-Okamoto de FrodoKEM. Además es código propio, sin auditar.
- **Ninguno de los dos modos** protege contra ataques de tiempo en Python. Uso académico, no para proteger secretos reales.

## 7. Pruebas mínimas
- Ida y vuelta en ambos modos: ASCII, UTF-8 (`ñ`, tildes), texto vacío, texto de más de 16 bytes (varios bloques).
- Cifrar dos veces el mismo texto da criptogramas distintos (aleatoriedad).
- Clave equivocada:
  - ML-KEM: `LatticeValueError`.
  - LWE: el texto no se recupera; no debe colgarse ni lanzar un error interno de Python.
- ML-KEM: un criptograma alterado se detecta.
- Mezcla de modos y tipos inválidos: `LatticeTypeError`.
- Variables: asignar y reutilizar, variable no definida (`LatticeNameError`), nombre reservado, nombre con dígitos (`CLAVES2`), variables en operaciones existentes (`A SUMA A`).
- Parámetros: n = 640, q = 2^15 y la tabla χ coinciden con la especificación.
- API: `POST /ejecutar` con el programa completo de §2 responde bien dentro del límite de tiempo. El resumen de la clave aparece en la respuesta y la clave no.
- Los 75 tests existentes siguen pasando.

## 8. Entregables además del código
- `requirements.txt` con `numpy` y `cryptography==50.0.2`; build de Docker verificado (`docker compose up --build`) con un `KEYGEN MLKEM` funcionando dentro del contenedor.
- Ejemplo `.le` con el flujo de §2 (en `lattice.le` o en un archivo nuevo).
- Documentación al día:
  - README: sintaxis nueva y la sección de seguridad de §6.
  - `CONTEXTO_PROYECTO.md` §5 (gramática) y §6 (tabla de operaciones).
  - Los "pendiente" de `LatticeEncrypt_Documentacion.tex`.
- Regenerar `dist/lattice-encrypt.exe` (el `.spec` debe incluir las nuevas dependencias) y verificar que el ejecutable cifra y descifra.

## 9. Decisiones tomadas tras la revisión (criterio de Claude; el equipo puede corregirlas)

1. **`KEYGEN` es prefijo, no operador infijo.** Se quita de `OperacionesLattice` en `reglas.json` (que queda con `CIFRAR` y `DESCIFRAR`), y el parser lo reconoce como primer token de la instrucción. `MATRIZ(...) KEYGEN ...` da `LatticeSyntaxError` con un mensaje que indica usar `NOMBRE = KEYGEN`. Ningún test actual usa `KEYGEN`.
2. **Clave equivocada en modo LWE.** Si al descifrar el relleno o el UTF-8 no son válidos, se lanza `LatticeValueError("No se pudo descifrar: clave incorrecta o criptograma dañado")`. Si por azar son válidos, se devuelve el texto obtenido. El modo LWE ya es solo IND-CPA (§6), así que este error no empeora su seguridad, y el comportamiento queda igual que en ML-KEM. Los tests verifican que el resultado nunca es el texto original y que no salta un error interno de Python.
3. **Valores `str`** (los de `TEXTO "..."`, `DESCIFRAR` y `CARACTERES`):
   - Se pueden asignar, imprimir y usar como operando izquierdo de `CIFRAR`.
   - `IGUAL` entre dos textos compara cadenas, para verificar `M IGUAL ORIGINAL`.
   - Cualquier otra operación con un `str` da `LatticeTypeError`. `parsear_operando()` devuelve el valor tal cual y cada regla valida los tipos.
4. **Tabla χ de Frodo:** se transcribe de la especificación oficial de FrodoKEM o de su implementación de referencia, citando la fuente. Los tests comparan la tabla con esos valores. Además hay una prueba estadística: con unas 100 000 muestras, la media ≈ 0 y la varianza ≈ σ² = 2.8² con tolerancia. Así una tabla mal copiada no pasa solo con las pruebas de ida y vuelta. No se exigen vectores KAT oficiales, porque son del KEM completo y no del PKE.
5. **Si `cryptography` 50.0.2 falla en Docker:** se busca la versión mínima que soporte ML-KEM en Linux y se fija esa. No se bloquea la funcionalidad y no se cambia de algoritmo.
6. **Asignaciones:**
   - Se pueden reasignar variables.
   - `B = A` copia el valor; los valores se tratan como inmutables.
   - `X = X SUMA VECTOR(1,1)` es válido.
   - Una línea suelta `TEXTO "x"` imprime la cadena.
7. **ML-KEM no parte en bloques:** un único mensaje AES-GCM por `CIFRAR`.

## 10. Lo que queda a criterio del implementador
- Guardar la matriz A entera o derivarla de una semilla (SHAKE-128).
- Estructura interna de los módulos (`ReglasLattice.py` solo, o un paquete `core/cripto/`).
- Formato exacto del relleno de bloques LWE y del texto de los `__repr__`.
