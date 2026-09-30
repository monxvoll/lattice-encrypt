# Despliegue de Lattice Encrypt en Render

Repositorio: https://github.com/monxvoll/lattice-encrypt

> **Sobre esta guía.** No pude leer el chat de ChatGPT (la página compartida no carga sin JavaScript), así que la armé revisando el repositorio completo: `README.md`, `Dockerfile`, `servidor.py`, `core/`, `reglas/`, `web/`, `Runner.py`, `requirements.txt` y `docker-compose.yml`. No queda ningún punto marcado como "verificar" sin comprobar: lo que se afirma aquí está aplicado en la rama y, cuando se dice que algo se probó, se probó de verdad.

---

## 0. Estado actual (rama `feature/deploy-render`)

Todo lo de las secciones 2, 3 y 4 está **aplicado y con pruebas** (`tests/test_despliegue.py`, 27 pruebas). Lo único que sigue siendo manual es el despliegue en Render (sección 5): eso se hace desde el panel y no se puede automatizar desde el repo.

| Sección | Qué | Estado |
|---|---|---|
| 2.1 | Puerto `$PORT` | Hecho y probado en contenedor |
| 2.2 | Persistencia de `programas/` | Hecho de otra forma: la ruta se lee de `PROGRAMAS_DIR` (ver nota) |
| 2.3 | Programas públicos y compartidos | Hecho: `MODO_DEMO=1` corta guardar y borrar; el editor esconde esos botones |
| 2.4 | Timeout de ejecución | Hecho: proceso aparte, se mata al vencer el plazo. Cuerpo en `core/ejecutor.py` |
| 2.5 | Límites de tamaño de entrada | Hecho: `MAX_CODIGO = 100_000` en los tres modelos; `nombre` con `max_length=64` |
| 2.6 | Versiones fijadas | Hecho: `fastapi==0.136.3`, `uvicorn[standard]==0.48.0` |
| 3 | Mejoras del Dockerfile | Hecho: `PYTHONUNBUFFERED`, `PYTHONDONTWRITEBYTECODE`, usuario `appuser`, sin `EXPOSE` |
| 3 | `.dockerignore` | Hecho |
| 4 | Frontend con rutas relativas | Verificado: ya usaba rutas relativas. No hace falta CORS |
| 5 | `render.yaml` | Hecho: creado y validado contra el esquema oficial |
| 5 | Despliegue en Render | **Pendiente, es manual** (sección 5) |

### Qué se comprobó de verdad

- **Build y arranque en Docker:** `docker build -t lattice-encrypt .` terminó bien y el contenedor arrancó con `PORT=10000`.
- **Las cuatro rutas del servicio,** medidas contra el contenedor corriendo:

  | Petición | Resultado |
  |---|---|
  | `GET /` | 200, JSON de estado con `modo_demo` |
  | `GET /editor` | 200, HTML del editor |
  | `GET /docs` | 200, Swagger de FastAPI |
  | `POST /ejecutar` | 200, informe de ejecución con la salida del programa |

- **El intérprete corre sin privilegios:** `docker exec lattice-test id` devuelve `uid=1000(appuser)`.
- **El `CMD` funciona sin `--app-dir`.** Se arrancó el mismo contenedor sobrescribiendo el entrypoint con `uvicorn servidor:app` y respondió igual. Los detalles están en 2.1.

### Decisiones que hubo que tomar

- **Persistencia: no se montó disco.** El plan gratuito de Render no admite Persistent Disk (ver sección 6), así que no había opción. Se implementó `PROGRAMAS_DIR` para que montar un disco sea solo cambiar la variable, pero para la demo gratuita se acepta que `programas/` se pierda en cada deploy. Con `MODO_DEMO=1` da igual: no se escribe nada.
- **El timeout va con `multiprocessing` con `spawn`.** No `fork`, porque en Linux el hijo heredaría los hilos del servidor. El cuerpo del hijo está en `core/ejecutor.py` y no en `servidor.py` por una razón medida: con `spawn` el hijo reimporta el módulo de la función que recibe, y si esa función viviera junto a FastAPI, **cada ejecución pagaba el import de FastAPI**. Medido en esta máquina: 1313 ms → 244 ms por ejecución. El plazo es `TIEMPO_LIMITE` (5 s por defecto); se comprobó que 2000 líneas (el máximo permitido) se ejecutan en 285 ms, así que el límite no corta nada legítimo.
- **En modo demo solo se corta la escritura.** `GET /api/programas` sigue abierto, para poder abrir programas que ya existieran. La web y la API sirven del mismo servicio, así que tampoco hace falta CORS.

### Lo que falta

1. **El despliegue en Render** (sección 5). Requiere una cuenta y que el repositorio esté en GitHub; no se puede automatizar desde el repo.
2. **Si algún día se monta el Persistent Disk**, ojo con los permisos: el montaje puede quedar con dueño `root` y `appuser` no podría escribir. Se arregla ejecutando el contenedor como root y haciendo `chown` de `/app/programas` al arrancar.

---

## 1. Cómo está el proyecto hoy

- App **FastAPI** (`servidor.py`) que sirve la API (`/iniciar`, `/ejecutar`, `/api/programas`) y una interfaz web estática (`/editor`, `/static`).
- **Dockerfile** basado en `python:3.13-slim`, instala `requirements.txt` (solo `fastapi` y `uvicorn`), copia `core/`, `reglas/`, `web/`, `Runner.py`, `servidor.py` y arranca `uvicorn` en el puerto **8000** fijo.
- Los programas del usuario se guardan en `programas/` (carpeta junto a `servidor.py`).

Render puede desplegarlo tal cual con el Dockerfile, pero había varios puntos que convenía corregir para que funcione bien y de forma segura. Todos están aplicados; lo que sigue es el detalle de cada punto.

---

## 2. Cambios aplicados

### 2.1 Usar el puerto que asigna Render (`$PORT`)

El `CMD` original tenía el puerto 8000 fijo. Render inyecta la variable `PORT` (10000 por defecto) y espera que el servicio escuche ahí. El `CMD` que quedó, idéntico al del `Dockerfile` de la sección 3:

```dockerfile
CMD ["sh", "-c", "uvicorn --app-dir /app servidor:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

`${PORT:-8000}` hace que siga funcionando en local (8000) y en Render (el que asigne). No se declara `EXPOSE`: es informativo y no cambia nada en un despliegue real.

**Sobre `--app-dir /app`:** se verificó que **no es necesario**. La CLI de uvicorn declara `--app-dir` con `default=""`, y `""` resuelve al directorio de trabajo, que en la imagen ya es `/app`. Se comprobó de las dos formas: arrancando el contenedor con el `CMD` tal cual, y arrancándolo con el entrypoint sobrescrito a `uvicorn servidor:app` sin el flag. En ambos casos respondió bien. Se deja escrito igual para que el arranque no dependa del `cwd` ni del comportamiento de la versión de uvicorn que se instale.

### 2.2 Persistencia de `programas/`

El sistema de archivos de Render es **efímero**: todo lo que se guarde en `programas/` se pierde en cada nuevo deploy, en cada reinicio y cuando el servicio se duerme. Opciones, y cuál quedó aplicada:

| Opción | Cuándo usarla | Estado aquí |
|---|---|---|
| Aceptar que sea efímero | Demo del curso: los programas guardados son solo de prueba. | **Aplicada** |
| **Persistent Disk** de Render montado en `/app/programas` | Quieres conservar los programas. | No usada: el plan gratuito no lo admite (sección 6) |
| Base de datos (p. ej. Postgres de Render) | Si quieres programas por usuario y más robustez. | No usada; implicaría cambiar `servidor.py` |

Para dejar la puerta abierta se añadió `PROGRAMAS_DIR`: si se monta un disco en `/app/programas`, basta con apuntar ahí la variable y no tocar código.

### 2.3 Los programas guardados son públicos y compartidos

Con el servicio en internet, **cualquier visitante** puede listar, leer, sobrescribir y **borrar** programas (`/api/programas`, `DELETE /api/programas/{nombre}`), porque no hay sesión ni usuarios y el almacenamiento es uno solo. Para una demo pública se aplicó la primera opción: **deshabilitar guardar y borrar con una variable de entorno**.

Con `MODO_DEMO=1`:

- `POST /api/programas` y `DELETE /api/programas/{nombre}` responden **403**.
- `GET /api/programas` y `GET /api/programas/{nombre}` siguen abiertos, para poder abrir lo que ya exista.
- `GET /` informa `modo_demo: true`, y el editor esconde los botones de guardar y borrar.

Las otras dos opciones que se considering (guardar en `localStorage` o proteger con un header `X-API-Key`) quedan fuera de esta versión.

### 2.4 Timeout de ejecución

El `servidor.py` reconoce que el intérprete **no tiene timeout**; solo limita a 2000 líneas (`MAX_LINEAS`). Como una sola línea puede traer un bucle infinito, una sola petición podía dejar el worker bloqueado indefinidamente, y en un servicio público eso es denegación de servicio.

El patrón aplicado es ejecutar el intérprete en un proceso aparte y matarlo al vencer el plazo. Vive repartido en dos archivos:

- `core/ejecutor.py`: el cuerpo del proceso hijo. Importa solo `core/`, nunca FastAPI, por el motivo medido que se explica en la sección 0.
- `servidor.py`, `ejecutar_con_timeout()`: arranca el proceso, espera el resultado con `cola.get(timeout=...)` y hace el `kill` en un `finally`.

El detalle que no está en el patrón obvio: **la cola vacía no siempre es timeout**. El hijo también puede haber muerto sin dejar nada (memoria agotada, fallo al arrancar), y en ese caso `cola.get()` lanza `queue.Empty` en el segundo intento y la excepción cruda se escaparía como un 500 sin explicación. La implementación distingue los dos casos mirando `proceso.is_alive()`:

- sigue vivo → **408**, "La ejecucion supero el tiempo limite de N s".
- murió sin resultado → **500**, "El interprete termino de forma inesperada (codigo de salida N) sin devolver resultado".

El plazo es `TIEMPO_LIMITE` (5 s por defecto), configurable por variable de entorno; si viene mal escrita se usa el valor por defecto en vez de impedir que el servicio arranque. El informe que devuelve el intérprete es serializable entre procesos (dicts, listas, strings y números), lo cual se verificó con las pruebas.

### 2.5 Límites de tamaño de entrada

Además de `MAX_LINEAS`, el tamaño del texto se limita en los modelos Pydantic, porque `MAX_LINEAS` solo acota las líneas: 2000 líneas de un par de megabytes cada una las pasa igual.

```python
MAX_CODIGO = 100_000

class CodigoRequest(BaseModel):
    codigo: str = Field(max_length=MAX_CODIGO)

class ProgramaRequest(BaseModel):
    nombre: str = Field(max_length=64, description="...")
    codigo: str = Field(default="", max_length=MAX_CODIGO)

class EjecutarRequest(BaseModel):
    codigo: str = Field(max_length=MAX_CODIGO)
    tokens: bool = Field(default=True, description="...")
```

De paso, el nombre del archivo se valida contra `^[A-Za-z0-9_\-]{1,64}$`: el nombre va a parar a un archivo del disco, y sin esa comprobación `..` o una barra permitirían escribir fuera de `programas/`.

### 2.6 Fijar versiones en `requirements.txt`

`requirements.txt` tenía `fastapi` y `uvicorn` sin versión, así que un build futuro podía traer una versión distinta y romper algo sin que cambiara el código. Quedaron fijadas a las que ya estaban instaladas y probadas:

```
fastapi==0.136.3
uvicorn[standard]==0.48.0
```

`core/` y `reglas/` no necesitan nada más: solo usan la librería estándar (`re`, `json`, `math`, `importlib`, `contextlib`, `io`, `os`, `random`, `pathlib`). Se verificó además que `core/LatticeSintactico.py` arma la ruta a `reglas/reglas.json` desde su propia ubicación (`os.path.dirname(__file__)/../reglas/reglas.json`) y que las reglas se cargan con `importlib.import_module("reglas.<Archivo>")`, así que la copia del `Dockerfile` funciona tal cual. **Ningún archivo lee `lattice.le` en tiempo de ejecución**: `.le` es solo la extensión de lo que guarda el usuario.

---

## 3. El Dockerfile final

Este es el contenido real del `Dockerfile`, sin abreviar:

```dockerfile
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core/ ./core/
COPY reglas/ ./reglas/
COPY web/ ./web/
COPY Runner.py servidor.py ./

RUN useradd --create-home appuser \
    && mkdir -p /app/programas \
    && chown -R appuser:appuser /app
USER appuser

CMD ["sh", "-c", "uvicorn --app-dir /app servidor:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

Notas:

- `PYTHONUNBUFFERED=1` hace que los logs aparezcan al instante en el panel de Render.
- El intérprete no corre como root: `appuser` no puede escribir fuera de `/app`, que es justo lo que se busca.
- **Si montas un Persistent Disk** en `/app/programas`, el montaje puede quedar con dueño `root`; si el usuario `appuser` no puede escribir, deja el contenedor como root o ajusta permisos al arrancar.
- El `.dockerignore` acompaña al `Dockerfile` para no copiar basura al contexto de build: `.git`, cachés de herramientas, `.venv/`, `tests/`, `docs/`, `docker-compose.yml`, `programas/` y los archivos sueltos del escritorio (`.docx`, `.jpeg`, `.env`).

---

## 4. Frontend (`web/`): revisado y verificado

- Las llamadas `fetch(...)` del editor usan **rutas relativas** (`/ejecutar`, `/api/programas`), no `http://localhost:8000/...`. Se revisaron los archivos de `web/` y no hay ninguna URL absoluta a `localhost`, así que funciona en Render sin cambios.
- Como la web y la API salen del mismo servicio, **no hace falta CORS**. Solo habría que agregarlo si algún día el frontend vive en otro dominio.
- En `web/app.js` se añadió la lectura de `modo_demo` de `GET /` para ocultar los botones de guardar y borrar, y en `web/estilos.css` la regla `.btn[hidden] { display: none; }` que hace que ocultarlos de verdad funcione (un `display` explícito gana sobre el atributo `hidden`).

---

## 5. Pasos del despliegue en Render

> A partir de aquí todo es manual y **no se ha ejecutado**: requiere una cuenta de Render y que el repositorio esté en GitHub.

1. **Aplica los cambios** de las secciones 2, 3 y 4 en una rama (`feature/deploy-render`), abre PR hacia `main` y fusiona (siguiendo el GitHub Flow del README).
2. **Prueba local con Docker** antes de subir (esto ya se hizo en esta máquina, con estos mismos comandos):
   ```bash
   docker build -t lattice-encrypt .
   docker run --rm -e PORT=10000 -p 10000:10000 lattice-encrypt
   ```
   Abre `http://localhost:10000/` y `http://localhost:10000/editor`.
3. En [render.com](https://render.com) crea cuenta y conecta tu GitHub (da acceso al repo `monxvoll/lattice-encrypt`).
4. Hay dos caminos, **A** o **B**. Elige uno.

### A. Crear el servicio a mano

1. **New → Web Service** y selecciona el repositorio.
2. Configura:
   - **Language:** Docker (detecta el `Dockerfile` en la raíz).
   - **Branch:** `main`.
   - **Region:** la más cercana a los usuarios. Render no tiene región en Colombia; las opciones son `oregon`, `ohio`, `frankfurt`, `singapore` y `virginia`, y por defecto usa `oregon`.
   - **Instance type:** Free para la demo (ver limitaciones en la sección 6) o uno de pago si necesitas disco persistente o que no se duerma.
   - **Health Check Path:** `/` (ya devuelve el JSON de estado).
3. **Variables de entorno:** `MODO_DEMO=1`. `PORT` y `TIEMPO_LIMITE` las deja Render con sus valores por defecto; no hacen falta. No subas secretos al repo.
4. Pulsa **Create Web Service** y espera a que el build termine ("Live").

### B. Crear el servicio desde `render.yaml` (recomendado)

`render.yaml` está en la raíz del repo, así que el servicio queda versionado y no hay que configurarlo a mano. Este es su contenido completo:

```yaml
# Infraestructura como codigo para Render.
#
# Con esto el servicio queda declarado en el repo: no hay que configurarlo a mano
# en el panel. En Render: New > Blueprint, apuntar a este repositorio.
#
# Claves contra la referencia oficial del esquema:
# https://render.com/docs/blueprint-spec
services:
  - type: web
    name: lattice-encrypt
    # El servicio se construye desde el Dockerfile de la raiz.
    runtime: docker
    # Plan gratuito: se duerme tras un rato de inactividad y no tiene disco.
    plan: free
    # La raiz ya devuelve el JSON de estado, asi que sirve de health check.
    healthCheckPath: /
    # Despliega en cada push a la rama del servicio. La forma actual de decirlo
    # es autoDeployTrigger; `autoDeploy: true` es su equivalente deprecado.
    autoDeployTrigger: commit
    envVars:
      # Demo publica: se puede ejecutar codigo pero no guardar ni borrar
      # programas, porque el almacenamiento es compartido entre visitantes.
      - key: MODO_DEMO
        value: "1"
      # Puerto y TIEMPO_LIMITE los deja Render; no hacen falta aqui. Si se
      # quisiera cambiar el margen del interprete:
      # - key: TIEMPO_LIMITE
      #   value: "10"
```

En Render: **New → Blueprint**, apunta al repositorio y Render crea el servicio con esa configuración. Para cambiar algo después se edita `render.yaml` y se vuelve a aplicar el Blueprint, no el panel.

Dos detalles del esquema, comprobados contra el
[Blueprint spec](https://render.com/docs/blueprint-spec) y su
[JSON Schema](https://render.com/schema/render.yaml.json) (el archivo se validó con `jsonschema` y da válido):

- `name` es **obligatorio** en cada servicio.
- `autoDeploy` sigue existiendo pero está **deprecado**; la clave vigente es `autoDeployTrigger`, que admite `off`, `commit` o `checksPass`. Aquí se usa `commit`, que es el equivalente actual de `autoDeploy: true`: redespliega en cada push a la rama del servicio.

Con el flujo por PRs del equipo, cada merge a `main` publicará una versión nueva. Si en algún momento se quiere desplegar a mano, se cambia a `autoDeployTrigger: off`.

### Probar el despliegue

Una vez creado (reemplaza la URL por la tuya):

```bash
curl https://TU-SERVICIO.onrender.com/
curl -X POST https://TU-SERVICIO.onrender.com/ejecutar \
  -H "Content-Type: application/json" \
  -d '{"codigo": "<una instrucción válida del lenguaje>", "tokens": false}'
```

Y abre `https://TU-SERVICIO.onrender.com/editor` y `/docs` (Swagger automático de FastAPI). Son las mismas cuatro rutas que se probaron en local contra el contenedor.

---

## 6. Limitaciones del plan gratuito

Confirmado en la [documentación de Render sobre instancias gratuitas](https://render.com/docs/free):

- El servicio se **duerme tras 15 minutos sin tráfico entrante** y la primera petición después tarda **cerca de un minuto** en despertar. Mientras está dormido no gasta horas de instancia.
- **No admite Persistent Disk.** Por eso en la sección 2.2 no se montó ninguno: no es una decisión de diseño, es que el plan no lo permite. Hay que subir de plan para tener disco.
- El filesystem es **efímero**: cada deploy, reinicio o siesta borra `programas/`.
- Recursos limitados: el plan `free` son **0.1 CPU y 512 MB de RAM**. Es otro motivo además del timeout para ejecutar el intérprete en un proceso aparte.
- **750 horas de instancia gratuita por mes** y por workspace; si se agotan, los servicios gratuitos quedan suspendidos hasta el mes siguiente.
- Sin escalado a varias instancias, sin cacheo en el edge, sin shell por SSH y sin one-off jobs.

Antes de la presentación, abre la URL un par de minutos antes para "despertar" el servicio.

---

## 7. Checklist final

- [x] `CMD` usa `${PORT}`
- [x] Versiones fijadas en `requirements.txt`
- [x] `.dockerignore` creado
- [x] Timeout de ejecución y límites de tamaño implementados
- [x] Guardar/borrar deshabilitado en público (`MODO_DEMO=1`)
- [x] `web/` sin URLs a `localhost`
- [x] Probado con `docker build` y `docker run -e PORT=10000`
- [x] Probados `/`, `/editor`, `/docs` y `/ejecutar` contra el contenedor
- [x] `render.yaml` creado y validado contra el esquema de Render
- [ ] PR abierto y mergeado a `main`
- [ ] Servicio creado en Render (Blueprint o a mano) con health check en `/`
- [ ] Probados `/`, `/editor`, `/docs` y `/ejecutar` en la URL de Render
