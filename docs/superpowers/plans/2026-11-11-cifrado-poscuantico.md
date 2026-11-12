# Cifrado post-cuántico (KEYGEN / CIFRAR / DESCIFRAR) — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir variables al lenguaje y hacer que `KEYGEN [LWE|MLKEM]`, `CIFRAR` y `DESCIFRAR` cifren texto de forma segura: FrodoPKE-640 implementado en el proyecto, y ML-KEM-768 + AES-256-GCM con la librería `cryptography`.

**Architecture:** Una tabla de símbolos (`core/entorno.py`) viaja dentro de `Sintactico`. `Sintactico.parsear_operando()` centraliza la lectura de operandos (literal, variable, texto) para todas las reglas. La criptografía vive en `core/cripto/`: `frodo.py` y `mlkem.py`, módulos puros sin conocer el lenguaje, y `valores.py` con los tipos `ParClaves` y `Cifrado`. `reglas/ReglasLattice.py` conecta esos módulos con el despachador.

**Tech Stack:** Python 3.12 (local) / 3.13 (Docker), numpy, cryptography 50.0.2, pytest, FastAPI.

**Spec:** `docs/superpowers/specs/2026-11-11-cifrado-poscuantico-design.md` (leerla antes de empezar; §9 tiene decisiones que este plan da por hechas).

## Global Constraints

- Rama `feature/cifrado-poscuantico`. Los 75 tests existentes deben seguir pasando tras cada tarea: `python -m pytest -q`.
- Dependencias fijadas en `requirements.txt`: `numpy==2.4.2` y `cryptography==50.0.2`. La 46.x no tiene ML-KEM. En local: `pip install -r requirements-dev.txt`.
- Aleatoriedad de claves, secretos, ruido y nonces: solo `os.urandom` o `secrets`. Nunca `random` ni `numpy.random`.
- Parámetros LWE: FrodoKEM-640, n=640, q=2^15, n̄=m̄=8, B=2 bits/entrada, 16 bytes por bloque.
- ML-KEM: `MLKEM768PrivateKey`, HKDF-SHA256 de 32 bytes con `info=b"LatticeEncrypt ML-KEM-768 AES-256-GCM"`, AES-GCM con nonce de 12 bytes de `os.urandom`.
- Errores del lenguaje: siempre subclases de `LatticeError` (`core/errores.py`). Una excepción de Python sin envolver es un bug.
- Mensajes, nombres y comentarios en español, como el resto del código.
- `KEYGEN MLKEM` nunca cae en silencio a otro algoritmo.
- Un `KEYGEN` + `CIFRAR` + `DESCIFRAR` de texto corto debe tardar < 1 s (el servidor corta a los 5 s).

## Review Focus

1. **Un texto o una clave usados en una operación de vectores** (`M SUMA VECTOR(1,2)` con `M` de tipo `str`) deben dar `LatticeTypeError`, no un error interno de Python. Hoy `SUMA` no valida tipos, y con dos matrices concatena listas. Test en la Tarea 2.
2. **Tokens sobrantes al final de la línea** (`CLAVES = KEYGEN MLKEM X`, `VECTOR(1,2) REDONDEAR VECTOR(1,1)`) deben dar `LatticeSyntaxError`, no ignorarse en silencio. Test en la Tarea 2.
3. **Asignación sin expresión o a una palabra reservada** (`A =`, `SUMA = VECTOR(1,2)`, `VECTOR = ...`) debe dar `LatticeSyntaxError` claro. Test en la Tarea 2.
4. **Criptograma de un programa usado con claves de otro tipo** (LWE contra ML-KEM, o pasar un `Cifrado` como clave) debe dar `LatticeTypeError`, nunca un `AttributeError`. Test en la Tarea 5.
5. **La API nunca devuelve material de clave**: la respuesta de `POST /ejecutar` contiene el resumen `<CLAVES ...>` y no arrays ni bytes. Test en la Tarea 5.

---

### Task 1: Error de nombre, tabla de símbolos e identificadores en el léxico

**Files:**
- Modify: `core/errores.py` (añadir clase)
- Create: `core/entorno.py`
- Modify: `core/LatticeLexico.py:42-55` (bloque "Leer Letras")
- Test: `tests/test_variables.py` (nuevo)

**Interfaces:**
- Produces:
  - `class LatticeNameError(LatticeError, NameError)`.
  - `class Entorno` con `definir(nombre: str, valor) -> None`, `obtener(nombre: str)` (lanza `LatticeNameError(f"Variable no definida: {nombre}")`) y `existe(nombre: str) -> bool`.
  - El léxico emite `Token("PALABRA", "CLAVES2")` para identificadores `[A-Z][A-Z0-9_]*`.

- [ ] **Step 1: Write the failing tests** en `tests/test_variables.py`:

```python
from core.entorno import Entorno
from core.errores import LatticeNameError, LatticeError
from core.LatticeLexico import Lexico

def test_entorno_definir_y_obtener():
    e = Entorno(); e.definir("A", (1.0, 2.0))
    assert e.existe("A") and e.obtener("A") == (1.0, 2.0)

def test_variable_no_definida():
    with pytest.raises(LatticeNameError, match="Variable no definida: X"):
        Entorno().obtener("X")
    assert issubclass(LatticeNameError, LatticeError)

def test_identificador_con_digitos_y_guion_bajo():
    tipos = [(t.tipo, t.valor) for t in Lexico().tokenizar("CLAVES_2 = KEYGEN")]
    assert tipos == [("PALABRA", "CLAVES_2"), ("IGUAL", "="), ("PALABRA", "KEYGEN")]

def test_minusculas_en_identificador_siguen_prohibidas():
    with pytest.raises(LatticeError):
        Lexico().tokenizar("Claves = KEYGEN")
```

- [ ] **Step 2:** `python -m pytest tests/test_variables.py -v` → FAIL (`ModuleNotFoundError: core.entorno`).
- [ ] **Step 3:** Implementar `LatticeNameError`, `Entorno` (un dict interno) y el cambio de léxico. Tras la primera letra, el bucle admite `isalpha() or isdigit() or == "_"`. La validación de mayúsculas se mantiene (`palabra.isupper()`).
- [ ] **Step 4:** `python -m pytest -q` → todo PASS (incluye los 75 existentes).
- [ ] **Step 5:** Commit `feat: agrega tabla de simbolos e identificadores con digitos`.

---

### Task 2: Parser con variables, asignación, `TEXTO` como operando y reglas centralizadas

**Files:**
- Modify: `core/LatticeSintactico.py` (constructor, nuevo `parsear_operando`, `analisisSintactico`)
- Modify: `reglas/ReglasBase.py`, `reglas/ReglasAritmetica.py`, `reglas/ReglasComparacion.py`, `reglas/ReglasRuido.py` (reemplazar el bloque `if tipo_derecho == "VECTOR" ... elif "MATRIZ"` por `sintactico.parsear_operando()`)
- Test: `tests/test_variables.py`

**Interfaces:**
- Consumes: `Entorno`, `LatticeNameError` (Task 1).
- Produces:
  - `Sintactico(tokens, entorno: Entorno | None = None)`. Con `None` crea un `Entorno()` propio.
  - `Sintactico.parsear_operando()` devuelve tupla, lista o el valor de la variable. Si la palabra no es `VECTOR`, `MATRIZ` ni una variable definida → `LatticeNameError` cuando es un identificador válido no definido; `LatticeSyntaxError("Tipo de operando no reconocido: X")` cuando el token no es `PALABRA`.
  - Constante de módulo `PALABRAS_RESERVADAS: frozenset[str]` = `{"VECTOR","MATRIZ","TEXTO","KEYGEN","LWE","MLKEM"}` ∪ todos los operadores listados en `reglas.json`.
  - `analisisSintactico()` devuelve el valor de la instrucción (también en una asignación).

Orden de `analisisSintactico()`:
1. Si los dos primeros tokens son `PALABRA` + token de tipo `IGUAL` (el símbolo `=`): es una asignación. El nombre no puede estar en `PALABRAS_RESERVADAS`; si lo está → `LatticeSyntaxError(f"'{nombre}' es una palabra reservada y no puede usarse como variable")`. Si después del `=` no hay nada → `LatticeSyntaxError("Falta la expresion despues de '='")`.
2. Evaluar la expresión:
   - Si el primer token es `PALABRA "TEXTO"` seguido de `CADENA`, el operando izquierdo es ese `str`.
   - En otro caso, `parsear_operando()`.
   - Luego se aplica el operador por el despachador, como hoy.
   - `KEYGEN` lo añade la Task 5; no tocarlo aquí.
3. Si quedan tokens sin consumir → `LatticeSyntaxError(f"Sobra texto al final de la instruccion: {token.valor}")`.
4. Si era asignación, `entorno.definir(nombre, valor)` y devolver `valor`.

Cambios en las reglas:
- `ReglasBase` `SUMA`: exigir `tuple` + `tuple`, si no `LatticeTypeError("Suma SUMA requiere: VECTOR SUMA VECTOR")`.
- `ReglasComparacion` `IGUAL`: añadir `str == str`.
- `ReglasRuido` `RUIDO`: con operando a la derecha usa `parsear_operando()` y valida tipos igual que hoy.

- [ ] **Step 1: Write the failing tests** (añadir a `tests/test_variables.py`). Helper:

```python
def correr(*lineas):
    e = Entorno(); r = None
    for l in lineas:
        r = Sintactico(Lexico().tokenizar(l), e).analisisSintactico()
    return r, e
```

Tests y asserts:
- `test_asignacion_y_reuso`: `correr("A = VECTOR(1,2)", "A SUMA A")[0] == (2.0, 4.0)`.
- `test_variable_como_operando_derecho`: `correr("A = VECTOR(3,4)", "VECTOR(1,2) RESTA A")[0] == (-2.0, -2.0)`.
- `test_reasignacion_y_copia`: `correr("A = VECTOR(1,1)", "B = A", "A = A SUMA VECTOR(1,1)")`; luego `e.obtener("B") == (1.0, 1.0)` y `e.obtener("A") == (2.0, 2.0)`.
- `test_texto_como_operando`: `correr('M = TEXTO "Hola ñ"')[0] == "Hola ñ"`.
- `test_igual_entre_textos`: `correr('A = TEXTO "x"', 'B = TEXTO "x"', 'A IGUAL B')[0] is True`.
- `test_texto_en_operacion_vectorial_es_error_de_tipo`: `correr('M = TEXTO "AB"', "M SUMA VECTOR(1,2)")` lanza `LatticeTypeError`.
- `test_suma_de_matrices_es_error_de_tipo`: `"MATRIZ(1,2,3,4) SUMA MATRIZ(1,2,3,4)"` lanza `LatticeTypeError`.
- `test_variable_no_definida_en_expresion`: `"X SUMA VECTOR(1,2)"` lanza `LatticeNameError`.
- `test_nombre_reservado` (parametrizado con `"SUMA = VECTOR(1,2)"`, `"VECTOR = VECTOR(1,2)"`, `"KEYGEN = VECTOR(1,2)"`): lanza `LatticeSyntaxError`, con `match="palabra reservada"`.
- `test_asignacion_sin_expresion`: `"A ="` lanza `LatticeSyntaxError`.
- `test_tokens_sobrantes` (parametrizado con `"VECTOR(1,2) REDONDEAR VECTOR(1,1)"`, `"VECTOR(1,2) SUMA VECTOR(1,1) VECTOR(2,2)"`): lanza `LatticeSyntaxError`, con `match="Sobra"`.
- `test_vector_literal_sigue_igual`: `"VECTOR(0,0) TEXTO \"AB\""` da `(65.0, 66.0)`. Es el uso existente de `TEXTO` como operador.

- [ ] **Step 2:** `python -m pytest tests/test_variables.py -v` → los nuevos FAIL.
- [ ] **Step 3:** Implementar en `core/LatticeSintactico.py` y en las cuatro reglas.
- [ ] **Step 4:** `python -m pytest -q` → todo PASS. Si un test existente falla por el chequeo de tokens sobrantes o el tipo de `SUMA`, comprobar que el test describía un comportamiento erróneo antes de cambiarlo y anotarlo en el commit.
- [ ] **Step 5:** Commit `feat: variables, asignacion y operandos centralizados en el parser`.

---

### Task 3: El entorno dura un programa, un archivo o una sesión de consola

**Files:**
- Modify: `core/interpreteArchivo.py` (`ejecutar_linea`, `evaluar`, `ejecutar_programa`, `ejecutar_archivo`)
- Modify: `Runner.py`
- Test: `tests/test_variables.py`

**Interfaces:**
- Consumes: `Sintactico(tokens, entorno)` (Task 2).
- Produces:
  - `ejecutar_linea(texto, entorno: Entorno | None = None)`.
  - `evaluar(texto, mostrar_tokens=True, entorno: Entorno | None = None)`.
  - `ejecutar_programa(texto, mostrar_tokens=True)` crea un `Entorno()` y lo comparte entre sus líneas.
  - `ejecutar_archivo(ruta, entorno: Entorno | None = None)` crea uno nuevo si recibe `None`.
  - `Runner.py` crea un `Entorno()` al arrancar, lo pasa a cada `ejecutar_linea` y le da a cada `ejecutar archivo.le` uno nuevo.

- [ ] **Step 1: Failing tests:**
  - `test_programa_comparte_variables`: `ejecutar_programa("A = VECTOR(1,2)\nA SUMA A")["lineas"][1]["resultado"] == [2.0, 4.0]`, y `errores == 0`.
  - `test_programas_no_comparten_variables`: tras el anterior, `ejecutar_programa("A SUMA A")["errores"] == 1`, con `tipo == "LatticeNameError"`.
  - `test_archivo_comparte_variables(tmp_path)`: escribir `A = VECTOR(1,2)\nA SUMA A` en `p.le`; `ejecutar_archivo(str(p)) == (2.0, 4.0)`.
  - `test_runner_recuerda_variables`: `subprocess.run([sys.executable, "Runner.py"], input="A = VECTOR(1,2)\nA SUMA A\nsalir\n", capture_output=True, text=True, cwd=RAIZ, timeout=30)`; en `stdout` aparece `"(2.0, 4.0)"`.
- [ ] **Step 2:** Ejecutar → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** `python -m pytest -q` → todo PASS.
- [ ] **Step 5:** Commit `feat: las variables viven por programa, archivo o sesion`.

---

### Task 4: Primitivas criptográficas — FrodoPKE-640 y ML-KEM-768

**Files:**
- Create: `core/cripto/__init__.py` (vacío), `core/cripto/frodo.py`, `core/cripto/mlkem.py`
- Modify: `requirements.txt` (añadir `numpy==2.4.2`, `cryptography==50.0.2`, con el mismo estilo de comentario)
- Test: `tests/test_frodo.py`, `tests/test_mlkem.py`

**Interfaces:**
- Produces, en `core/cripto/frodo.py`:
  - Constantes `N = 640`, `Q = 2**15`, `NBAR = 8`, `B = 2`, `BYTES_BLOQUE = 16` y `TABLA_CDF: tuple[int, ...]`.
  - `muestrear_error(filas: int, cols: int) -> np.ndarray` (int64).
  - `generar_claves() -> tuple[tuple[np.ndarray, np.ndarray], np.ndarray]`, que devuelve `((A, B), S)`.
  - `cifrar_bloque(publica, bloque: bytes) -> tuple[np.ndarray, np.ndarray]`, que devuelve `(C1 m̄×n, C2 m̄×n̄)`.
  - `descifrar_bloque(privada, c1, c2) -> bytes`.
  - `cifrar_texto(publica, texto: str) -> list[tuple[np.ndarray, np.ndarray]]`.
  - `descifrar_texto(privada, bloques) -> str`.
- Produces, en `core/cripto/mlkem.py`:
  - `disponible() -> bool`.
  - `generar_claves() -> tuple[MLKEM768PublicKey, MLKEM768PrivateKey]`. Lanza `LatticeError("ML-KEM no esta disponible en esta instalacion de cryptography (se requiere 50.0.2)")` si no hay soporte.
  - `cifrar_texto(publica, texto: str) -> tuple[bytes, bytes, bytes]`, que devuelve `(ct_kem, nonce, ct_aes)`.
  - `descifrar_texto(privada, datos) -> str`.
- Errores de descifrado, en ambos módulos: `LatticeValueError("No se pudo descifrar: clave incorrecta o criptograma alterado")`.

Detalles que el código debe respetar:
- **TABLA_CDF**: valores de FrodoKEM-640. Candidata: `(4643, 13363, 20579, 25843, 29227, 31145, 32103, 32525, 32689, 32745, 32762, 32766, 32767)`.
  - Verificar contra la especificación oficial de FrodoKEM o contra `CDF_TABLE` de la implementación de referencia (PQClean `frodokem640shake/params.h` o el repo `microsoft/PQCrypto-LWEKE`) antes de escribirla.
  - Poner la URL de la fuente en un comentario.
- **Muestreo χ** (algoritmo de Frodo), por cada muestra:
  - `r` = 16 bits de `os.urandom`; `signo = r & 1`; `p = r >> 1`.
  - `e = sum(p > T[i] for i in range(len(T)-1))`.
  - Resultado: `-e` si `signo` vale 1, `e` si vale 0.
  - Vectorizar con numpy sobre un buffer de `os.urandom(2*filas*cols)`.
- **A** uniforme en Z_q: `np.frombuffer(os.urandom(2*N*N), "<u2") & (Q-1)`.
- **Codificación**: los 128 bits del bloque se parten en 64 valores de 2 bits, en orden de bits menos significativo primero, y forman una matriz 8×8. El valor `k` se codifica como `k * Q // 4`. La decodificación es `round(x * 4 / Q) % 4` con `x` en [0, Q).
- **Formato de texto** (LWE): `len(utf8).to_bytes(4, "big") + utf8`, rellenado con ceros hasta un múltiplo de 16.
  - Al descifrar, se lanza el error si la longitud declarada excede los bytes disponibles, si el relleno no es todo ceros o si el UTF-8 es inválido.
- **ML-KEM**:
  - `ss, ct = publica.encapsulate()`.
  - `clave = HKDF(SHA256(), 32, salt=None, info=...).derive(ss)`.
  - `AESGCM(clave).encrypt(nonce, utf8, None)`.
  - En `descifrar_texto`, `InvalidTag` y `ValueError` (de un `decapsulate` con longitud mala) se traducen al `LatticeValueError`.

- [ ] **Step 1:** `pip install -r requirements-dev.txt` tras editar `requirements.txt`. Comprobar con `python -c "from cryptography.hazmat.primitives.asymmetric import mlkem"`.
- [ ] **Step 2: Failing tests** en `tests/test_frodo.py`:
  - `test_parametros`: `N == 640 and Q == 2**15 and NBAR == 8 and B == 2`, y `TABLA_CDF == (<valores verificados>)`.
  - `test_distribucion_error`: `x = muestrear_error(400, 250)`; `abs(x.mean()) < 0.05`; `abs(x.var() - 2.8**2) < 0.35`; `np.abs(x).max() <= 12`.
  - `test_bloque_ida_y_vuelta`: para 20 bloques de `os.urandom(16)`, descifrar devuelve el original.
  - `test_texto_ida_y_vuelta` (parametrizado con `""`, `"HOLA"`, `"Hola mundo, ñandú y acción"`, `"x"*100`): se recupera igual.
  - `test_cifrado_aleatorio`: dos `cifrar_texto` del mismo texto dan `C2` distintos.
  - `test_clave_incorrecta`: descifrar con la `S` de otro `generar_claves()` lanza `LatticeValueError` o devuelve un texto distinto, nunca el original (repetir 5 veces).
  - `test_rapidez`: `generar_claves` + cifrar + descifrar `"HOLA"` en < 1 s (`time.perf_counter`).
- [ ] **Step 2b: Failing tests** en `tests/test_mlkem.py`:
  - `test_ida_y_vuelta` con `"Hola ñ"` y con `""`.
  - `test_cifrado_aleatorio`: los `ct_kem` difieren.
  - `test_clave_incorrecta`: lanza `LatticeValueError`.
  - `test_criptograma_alterado`: invertir un bit de `ct_aes` → `LatticeValueError`.
  - `test_kem_alterado`: invertir un bit de `ct_kem` → `LatticeValueError`.
- [ ] **Step 3:** Ejecutar ambos → FAIL.
- [ ] **Step 4:** Implementar los dos módulos.
- [ ] **Step 5:** `python -m pytest -q` → todo PASS.
- [ ] **Step 6:** Commit `feat: primitivas FrodoPKE-640 y ML-KEM-768 con AES-GCM`.

---

### Task 5: KEYGEN, CIFRAR y DESCIFRAR en el lenguaje

**Files:**
- Create: `core/cripto/valores.py`
- Modify: `reglas/ReglasLattice.py`, `reglas/reglas.json` (quitar `KEYGEN` del grupo 4 y ajustar su `_comentario`), `core/LatticeSintactico.py` (`KEYGEN` prefijo y error de `KEYGEN` infijo)
- Create: `cifrado.le` (ejemplo con el flujo de la spec §2)
- Test: `tests/test_cifrado.py`

**Interfaces:**
- Consumes: `frodo.*`, `mlkem.*` (Task 4); `parsear_operando`, `PALABRAS_RESERVADAS` (Task 2).
- Produces:
  - `@dataclass(frozen=True, eq=False) class ParClaves: modo: str; publica: object; privada: object`. `modo` vale `"LWE"` o `"ML-KEM"`.
  - `@dataclass(frozen=True, eq=False) class Cifrado: modo: str; datos: object; tamano: int` (`tamano` en bytes).
  - `__repr__`:
    - `ParClaves`: `<CLAVES LWE FrodoPKE-640>` / `<CLAVES ML-KEM-768>`.
    - `Cifrado` LWE: `<CIFRADO LWE FrodoPKE-640, {k} bloque(s), {kb:.1f} KB>`.
    - `Cifrado` ML-KEM: `<CIFRADO ML-KEM-768, {kb:.1f} KB>`.
  - `reglas.ReglasLattice.generar_claves(modo: str) -> ParClaves`, con `modo` = `"LWE"` o `"MLKEM"`.
  - `revisarSintaxisLattice(sintactico, lado_izquierdo, operador)` para `CIFRAR` y `DESCIFRAR`. El operando derecho se obtiene con `parsear_operando()`.

Reglas de tipo (todas `LatticeTypeError`):
- `CIFRAR`: el izquierdo debe ser `str` (`"CIFRAR requiere un texto: TEXTO \"...\" CIFRAR CLAVES"`) y el derecho un `ParClaves`.
- `DESCIFRAR`: el izquierdo debe ser `Cifrado`, el derecho `ParClaves`, y los modos deben coincidir (`"El criptograma es LWE pero las claves son ML-KEM-768"`).
- Uso de las partes de la clave: `CIFRAR` usa solo `.publica` y `DESCIFRAR` solo `.privada`.

En el parser:
- Si el primer token de la expresión es `PALABRA "KEYGEN"`, se consume y, opcionalmente, `LWE` o `MLKEM` (por defecto `LWE`). Luego se llama a `generar_claves`.
- `KEYGEN` después de un operando → `LatticeSyntaxError("KEYGEN no lleva operandos: usa NOMBRE = KEYGEN [LWE|MLKEM]")`.

- [ ] **Step 1: Failing tests** en `tests/test_cifrado.py`. Usar `ejecutar_programa` y el helper `correr` (copiarlo o moverlo a `conftest.py`):
  - `test_flujo_lwe`: `correr("C = KEYGEN", 'X = TEXTO "Hola ñ" CIFRAR C', "X DESCIFRAR C")[0] == "Hola ñ"`.
  - `test_flujo_mlkem`: lo mismo con `KEYGEN MLKEM`.
  - `test_keygen_lwe_explicito`: `repr(correr("C = KEYGEN LWE")[0]) == "<CLAVES LWE FrodoPKE-640>"`.
  - `test_repr_cifrado`: con LWE y `"HOLA"`, `repr` empieza por `"<CIFRADO LWE FrodoPKE-640, 1 bloque"`.
  - `test_verificar_con_igual`: `correr("C = KEYGEN MLKEM", 'O = TEXTO "abc"', "X = O CIFRAR C", "M = X DESCIFRAR C", "M IGUAL O")[0] is True`.
  - `test_mezcla_de_modos`: un criptograma LWE descifrado con claves ML-KEM lanza `LatticeTypeError`, con `match="LWE"`.
  - `test_tipos_invalidos` (parametrizado):
    - `VECTOR(1,2) CIFRAR C`;
    - `TEXTO "a" CIFRAR VECTOR(1,2)`;
    - `C DESCIFRAR C`;
    - con `X` cifrado: `X CIFRAR X`.
    - Todos lanzan `LatticeTypeError`.
  - `test_clave_ajena_mlkem`: descifrar con otro `KEYGEN MLKEM` lanza `LatticeValueError`.
  - `test_keygen_infijo`: `"MATRIZ(3,1,2,4) KEYGEN VECTOR(1,2)"` lanza `LatticeSyntaxError`, con `match="NOMBRE = KEYGEN"`.
  - `test_keygen_con_sobrante`: `"C = KEYGEN MLKEM X"` lanza `LatticeSyntaxError`.
  - `test_api_programa_completo` (con el `cliente` de `tests/test_api.py`): hacer `POST /ejecutar` con el contenido de `cifrado.le`. Comprobar:
    - `errores == 0`;
    - la última línea tiene el texto original;
    - alguna línea tiene `resultado == "<CLAVES ML-KEM-768>"`;
    - `"privada"` no aparece en `r.text`.
- [ ] **Step 2:** Ejecutar → FAIL.
- [ ] **Step 3:** Implementar `valores.py`, `ReglasLattice.py`, `reglas.json` y el parser. Escribir `cifrado.le` con los dos flujos de la spec §2 y una línea `M IGUAL O` de verificación por modo.
- [ ] **Step 4:** `python -m pytest -q` → todo PASS. `python Runner.py`, luego `ejecutar cifrado.le` → la salida muestra los textos recuperados.
- [ ] **Step 5:** Commit `feat: KEYGEN, CIFRAR y DESCIFRAR con LWE propio y ML-KEM`.

---

### Task 6: Empaquetado — Docker y ejecutable

**Files:**
- Modify: `lattice-encrypt.spec` (en `hiddenimports`, añadir `core.cripto.frodo`, `core.cripto.mlkem` y `core.cripto.valores`; en `datas`, añadir `('cifrado.le', '.')`)
- Modify (solo si hace falta): `requirements.txt`, por la regla de la spec §9.5

- [ ] **Step 1:** `docker compose up --build -d`.
  - Luego, `curl -s -X POST localhost:8000/ejecutar -H "Content-Type: application/json" -d '{"codigo":"C = KEYGEN MLKEM\nX = TEXTO \"hola\" CIFRAR C\nX DESCIFRAR C"}'`.
  - Esperado: `"errores":0` y `"hola"` en la última línea. Después, `docker compose down`.
  - Si Docker no está disponible en la máquina, decirlo explícitamente en el informe; no darlo por verificado.
- [ ] **Step 2:** `pyinstaller lattice-encrypt.spec --noconfirm`.
  - Luego, `printf 'ejecutar cifrado.le\nsalir\n' | dist/lattice-encrypt.exe`. Ejecutarlo desde un directorio que contenga `cifrado.le`, o pasar una ruta absoluta.
  - Esperado: los textos originales recuperados y sin errores.
- [ ] **Step 3:** Commit `build: empaqueta numpy y cryptography en Docker y en el ejecutable`. Solo se versionan archivos fuente: `build/` y `dist/` no entran.

---

### Task 7: Documentación

**Files:**
- Modify: `README.md`
  - Sección "Cifrado post-cuántico" con la sintaxis de la spec §2 y el texto de seguridad de la spec §6, casi literal.
  - Quitar la frase "aún no implementadas".
- Modify: `CONTEXTO_PROYECTO.md`
  - §5: la gramática de la spec §5.1.
  - §6: sustituir las filas "En diseño" de KEYGEN, CIFRAR y DESCIFRAR por filas reales, y añadir las filas de asignación y variables.
- Modify: `LatticeEncrypt_Documentacion.tex`
  - Sustituir las menciones de `ReglasLattice` "pendiente" (líneas ~118, 544, 592, 775, 798 y 827) por la descripción implementada.
  - Añadir una subsección con FrodoPKE-640 (KeyGen, Enc y Dec de la spec §5.3), ML-KEM-768 y las limitaciones de la §6.
  - El `.tex` no está versionado: editarlo sin hacer `git add`.

- [ ] **Step 1:** Escribir los cambios.
- [ ] **Step 2:** Verificar que todos los ejemplos de código del README se ejecutan. Pegarlos en un `.le` temporal en el scratchpad y correr `ejecutar`; debe dar `errores == 0`.
- [ ] **Step 3:** Si hay `pdflatex`, compilar el `.tex`; si no, decirlo.
- [ ] **Step 4:** Commit `docs: documenta el cifrado poscuantico y la gramatica de variables`. Solo entra `README.md`: `CONTEXTO_PROYECTO.md` y el `.tex` no están versionados, se editan sin `git add`.
