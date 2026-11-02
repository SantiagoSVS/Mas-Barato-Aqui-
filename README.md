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
    interpretacion/   intérprete de consultas: esquema, validación, proveedores, evaluación H2
    worker/           worker de captura programada (APScheduler)
  catalogo.toml       productos que el worker captura y sus identificadores por tienda
  evaluacion/         consultas anotadas para medir la exactitud del intérprete (H2)
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
tienen conector, pide las ofertas de cada producto de `catalogo.toml` y guarda una captura por
oferta, vinculada a su producto. El resultado de cada pasada (exitosa, parcial o fallida, con
sus errores) se ve en `GET /salud`.

### Catálogo de productos

`backend/catalogo.toml` define qué productos se capturan y sus identificadores en cada tienda:

```toml
[[producto]]
nombre = "Samsung Galaxy Tab A11 128 GB"
categoria = "tecnologia"
marca = "Samsung"
[producto.ids]
mercadolibre = ["MCO56570140"]
```

Para Mercado Libre, el identificador es el `/p/MCO…` de la página del producto. Antes de
agregarlo, verifica que tenga vendedores:

```powershell
python -m app.herramientas.buscar_mercadolibre --id MCO56570140
```

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

## Interpretación de consultas

El intérprete convierte una consulta en lenguaje coloquial en criterios estructurados
(sección 5.3). Para verlo funcionar:

```powershell
python -m app.herramientas.interpretar "busco un celular Samsung gama media por menos de 800 mil"
```

- **Seguridad:** la consulta se limpia y se limita a 300 caracteres antes de llegar al modelo.
  La respuesta se valida contra el esquema y se trata como dato, nunca se ejecuta.
- **Si la respuesta no cumple el esquema,** se reintenta una vez; si vuelve a fallar, se pide
  aclaración al usuario. También se pide aclaración, por reglas propias, cuando no hay producto
  o la confianza es menor que `INTERPRETE_CONFIANZA_MINIMA`.
- **Proveedores** (`INTERPRETE_PROVEEDOR`):
  - `anthropic`: Claude, el proveedor real elegido el 1 de noviembre de 2026. Necesita
    `ANTHROPIC_API_KEY` en `.env`. El modelo se elige con `INTERPRETE_MODELO` (por defecto
    `claude-opus-5-5`; `claude-haiku-5-5` es mucho más barato) y se usa con esfuerzo bajo,
    porque extraer criterios es una tarea simple.
  - `falso` (por defecto): reglas simples, sin clave de API ni costo. Sirve para desarrollar y
    probar; entiende pocas palabras (en las 50 consultas anotadas acierta 0 de 50).

### Medir H2 (exactitud de la interpretación)

```powershell
python -m app.herramientas.evaluar_interprete --detalle
python -m app.herramientas.evaluar_interprete --csv resultados_h2.csv
```

Lee `backend/evaluacion/consultas_anotadas.json`, compara cada interpretación con su anotación
y reporta el porcentaje de consultas correctas en todos sus campos, con su intervalo de confianza
del 95 % (Wilson), y los aciertos por campo. Las reglas de comparación están en
`app/interpretacion/evaluacion.py`. El formato está en `evaluacion/consultas_ejemplo.json`.

Las 50 consultas deben recogerse de personas reales y anotarse a mano **sin mirar lo que
responde el intérprete**; de lo contrario, el resultado de H2 quedaría sesgado.

## Tiendas integradas

| Tienda | Acceso | Configuración en `.env` |
|---|---|---|
| Mercado Libre | API oficial (token de aplicación) | `MERCADOLIBRE_CLIENT_ID` y `MERCADOLIBRE_CLIENT_SECRET`, de la app creada en developers.mercadolibre.com.co |
| Falabella | Extracción de la página de producto (robots.txt la permite) | Ninguna |
| Homecenter | Extracción de la página de producto (robots.txt la permite; prohíbe la búsqueda) | Ninguna |
| Amazon | No se integra por ahora (ver abajo) | — |

Si a una tienda le faltan credenciales, el worker la omite y lo avisa en el log.

**Amazon** sigue en los documentos del proyecto, pero no se integra mientras sea un proyecto de
grado y no un negocio: su acceso (API para afiliados) es complejo. La conversión de dólares a
pesos con la TRM ya está lista por si se integra más adelante.

**Mercado Libre:** por cada identificador del catálogo toma las publicaciones nuevas del
producto (`/products/{id}/items`) y cotiza el envío y la fecha de entrega hacia la ciudad
`MERCADOLIBRE_CIUDAD_DESTINO` (`/items/{id}/shipping_options`). Si no logra cotizar el envío,
lo deja como desconocido, nunca como gratis. No busca por texto: con token de aplicación,
`/sites/MCO/search` responde 403 y `/products/search` casi no encuentra productos con vendedores.

**Falabella:** lee la página de cada producto del catálogo (el JSON de `__NEXT_DATA__`) y
toma el menor precio vigente, sin precios tachados ni el precio con tarjeta CMR. El envío y
los días de entrega quedan como desconocidos: Falabella los calcula en el navegador según la
ubicación del comprador. En su lugar, la plataforma guarda el aviso de envío gratis que publica
la página (`nota_envio`, visible en `GET /salud`).

Como exige el documento de arquitectura, la tienda se registró inactiva y se activó (migración
`activa_falabella`) después de revisar sus términos y condiciones, el 1 de noviembre de 2026.

**Homecenter:** reemplaza a Amazon como tercera tienda. Lee la página de cada producto del
catálogo (`productProps` de `__NEXT_DATA__`) y toma el menor precio vigente (INTERNET frente a
NORMAL), sin el precio con tarjeta CMR. Nunca usa la búsqueda, porque su `robots.txt` la
prohíbe. El envío y los días quedan como desconocidos, con un aviso en `nota_envio`. Se
registró inactiva y se activó (migración `activa_homecenter`) después de revisar sus términos,
el 1 de noviembre de 2026.

`robots.txt` se interpreta con Protego, que entiende los comodines `*` y `$` de la RFC 9309
(`urllib.robotparser` de Python no los entiende).

## Agregar una tienda

1. Escribe su conector en `backend/app/extraccion/conectores/`: una clase que hereda de
   `Conector` e implementa `buscar(producto)` y `actualizar(url)`, devolviendo `OfertaCapturada`.
   Define `clave_catalogo`, el nombre de la tienda en `[producto.ids]` del catálogo.
2. Agrega su fábrica en `backend/app/extraccion/registro.py`.
3. Registra la plataforma con una migración de datos (como `registra_mercado_libre`), con el
   mismo nombre que `nombre_plataforma`.

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
| 1. Extracción de datos | 31 oct – 13 nov | Terminado (1 nov): Mercado Libre, Falabella y Homecenter |
| 2. Interpretación PLN | 7 – 20 nov | En curso: falta medir H2 con el proveedor real |
| 3. Costo total y recomendación | 14 – 27 nov | Pendiente |
| 4. Historial de precios | 21 nov – 4 dic | Pendiente |
| 5. Interfaz e integración | 28 nov – 11 dic | Pendiente |
