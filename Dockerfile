FROM python:3.13-slim

# PYTHONUNBUFFERED=1 hace que los prints aparezcan al instante en el log del
# servicio en vez de quedarse en el buffer hasta el fin del proceso.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core/ ./core/
COPY reglas/ ./reglas/
COPY web/ ./web/
COPY Runner.py servidor.py ./

# El interprete no corre como root: se crea un usuario sin privilegios y se le
# cede /app entero, incluida la carpeta donde se guardan los programas.
RUN useradd --create-home appuser \
    && mkdir -p /app/programas \
    && chown -R appuser:appuser /app
USER appuser

# Render inyecta PORT (10000 por defecto) y espera ahi a que escuche el
# servicio; el 8000 es solo el valor por defecto para correr en local. No se
# declara EXPOSE porque es informativo y no cambia nada en un despliegue real.
#
# --app-dir no es necesario: el default de la CLI de uvicorn es "" y eso
# resuelve al directorio de trabajo, que aqui ya es /app. Se deja escrito para
# que no dependa del cwd ni del comportamiento de la version de uvicorn que se
# instale.
CMD ["sh", "-c", "uvicorn --app-dir /app servidor:app --host 0.0.0.0 --port ${PORT:-8000}"]
