# Imagen de producción: un solo servicio que sirve la API (en /api) y la interfaz ya compilada.
# El worker no va aquí: se ejecuta aparte y solo necesita acceso a la misma base de datos.

# 1. Compila la interfaz. CYPRESS_INSTALL_BINARY=0: las pruebas E2E no corren en esta imagen.
FROM node:24-alpine AS interfaz
ENV CYPRESS_INSTALL_BINARY=0
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# 2. Imagen final: Python, el backend y los archivos compilados
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY --from=interfaz /app/frontend/dist /app/frontend/dist

# Sin privilegios de administrador dentro del contenedor
RUN useradd --create-home app
USER app

# Render indica el puerto en $PORT. --proxy-headers: la IP real llega en X-Forwarded-For.
CMD ["sh", "-c", "exec uvicorn --factory app.produccion:crear_sitio --host 0.0.0.0 --port ${PORT:-10000} --proxy-headers --forwarded-allow-ips='*'"]
