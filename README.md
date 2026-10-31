# Mas Barato Aquí!

Aplicación web que recibe una necesidad de compra en lenguaje coloquial y recomienda dónde sale
más barato un producto entre tiendas que venden en Colombia, sumando precio y envío y
considerando el tiempo de entrega. Proyecto de grado de Ingeniería de Software.

El contexto completo del proyecto está en [`CLAUDE.md`](CLAUDE.md) y en [`docs/`](docs/).

## Estructura

```
backend/              API (FastAPI), worker, modelos, migraciones y pruebas (pytest)
  app/                código de la API
    extraccion/       conectores por tienda, cliente HTTP respetuoso, normalización, TRM
    worker/           worker de captura programada (APScheduler)
  catalogo.toml       términos que el worker busca en cada tienda
  migraciones/        migraciones de la base de datos (Alembic)
  pruebas/            pruebas unitarias y de integración
frontend/             interfaz web (React + Vite)
docker/               scripts de arranque de PostgreSQL
docker-compose.yml    PostgreSQL para desarrollo
.env.example          plantilla de variables de entorno
```

## Requisitos

- Docker Desktop (con WSL 2)
- Python 3.12
- Node.js LTS
- Git

## Puesta en marcha (PowerShell)

Todos los comandos se ejecutan desde la raíz del proyecto, salvo donde se indica.

### 1. Variables de entorno (solo la primera vez)

```powershell
Copy-Item .env.example .env
```

Abre `.env` y cambia `cambia_esta_clave` por una clave propia, en las tres líneas donde aparece.
El archivo `.env` no se sube al repositorio.

### 2. Base de datos

```powershell
docker compose up -d --wait
```

Crea dos bases: `mas_barato_aqui` (desarrollo) y `mas_barato_aqui_test` (pruebas).

### 3. Backend

```powershell
cd backend
py -3.12 -m venv .venv                       # solo la primera vez
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt          # solo la primera vez o si cambian las dependencias
alembic upgrade head                         # aplica las migraciones
uvicorn app.main:app --reload
```

- API: <http://localhost:8000/salud>
- Documentación interactiva: <http://localhost:8000/docs>

Si PowerShell no deja activar el entorno, ejecuta una vez
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

### 4. Worker de captura (en otra terminal)

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m app.worker --una-vez               # una sola pasada, para probar
python -m app.worker                         # captura ahora y luego cada CAPTURA_INTERVALO_HORAS
```

El worker es el único proceso que consulta las tiendas. Recorre las plataformas activas que
tienen conector, busca cada término de `catalogo.toml` y guarda una captura por oferta. El
resultado de cada pasada (exitosa, parcial o fallida, con sus errores) se ve en `GET /salud`.

### 5. Frontend (en otra terminal)

```powershell
cd frontend
npm install                                  # solo la primera vez
npm run dev
```

Abre <http://localhost:5173>. Debe decir "Servicio funcionando". Las llamadas a `/api/...` se
reenvían al backend del puerto 8000.

## Pruebas

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest
```

Necesitan la base de datos encendida. Usan la base `mas_barato_aqui_test`: recrean sus tablas
con las migraciones al empezar y deshacen los datos de cada prueba al terminar. No usan
internet: las tiendas y la TRM se reemplazan por dobles de prueba y respuestas guardadas.

En GitHub, cada Pull Request corre las mismas pruebas automáticamente
(`.github/workflows/pruebas.yml`).

## Agregar una tienda

1. Escribe su conector en `backend/app/extraccion/`: una clase que hereda de `Conector` e
   implementa `buscar(termino)` y `actualizar(url)`, devolviendo `OfertaCapturada`.
2. Regístralo en `backend/app/extraccion/registro.py`.
3. Registra la plataforma en la tabla `plataforma` con el mismo nombre.

Nada más cambia (RNF-06).

## Comandos útiles

| Qué | Comando |
|---|---|
| Apagar la base de datos | `docker compose down` |
| Borrar la base de datos y empezar de cero | `docker compose down -v` |
| Crear una migración tras cambiar `app/modelos.py` | `alembic revision --autogenerate -m "descripción"` (en `backend/`) |
| Ver la última migración aplicada | `alembic current` (en `backend/`) |

## Plan de desarrollo

| Incremento | Fechas | Estado |
|---|---|---|
| 0. Base del proyecto | 31 oct – 2 nov 2026 | Terminado (31 oct) |
| 1. Extracción de datos | 31 oct – 13 nov | En curso: falta el acceso a las tiendas |
| 2. Interpretación PLN | 7 – 20 nov | Pendiente |
| 3. Costo total y recomendación | 14 – 27 nov | Pendiente |
| 4. Historial de precios | 21 nov – 4 dic | Pendiente |
| 5. Interfaz e integración | 28 nov – 11 dic | Pendiente |
