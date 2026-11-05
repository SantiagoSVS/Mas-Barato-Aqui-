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
    costo/            motor de costo total CT/CA y recomendación (sección 7)
    consultas/        búsqueda en el catálogo y resolución de consultas (POST /consultas)
    historial/        historial de precios y mínimo histórico (GET /productos/{id}/historial)
    worker/           worker de captura programada (APScheduler)
    validacion/       análisis de la Fase 4: SUS, pruebas con usuarios (H1, H5) y auditoría (H3)
  catalogo.toml       productos que el worker captura y sus identificadores por tienda
  evaluacion/         consultas anotadas (H2), plantillas de las pruebas con usuarios y auditorías (H3)
  migraciones/        migraciones de la base de datos (Alembic)
  pruebas/            pruebas unitarias y de integración
frontend/             interfaz web (React + Vite)
  src/paginas/        pantallas P1 a P4 y el estado sin cobertura
  cypress/            pruebas de extremo a extremo (Cypress) con respuestas guardadas
scripts/              captura programada en Windows (tarea de las 8:00 y las 20:00)
docs/fase4/          protocolo, consentimiento, cuestionarios y auditoría de la Fase 4
.github/workflows/   CI: alembic check + pytest, y build + Cypress en cada PR
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

Para que el historial crezca sin dejar una terminal abierta, registra la captura programada
(una sola vez, sin permisos de administrador). Corre a las 8:00 y a las 20:00, y si el equipo
estaba apagado, apenas se encienda; abre Docker Desktop si hace falta y deja el registro en
`logs/captura_diaria.log`:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\programar_captura.ps1          # registrar
powershell -ExecutionPolicy Bypass -File scripts\programar_captura.ps1 -Quitar  # eliminar
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

Abre <http://localhost:5173>. Las llamadas a `/api/...` se reenvían al backend del puerto 8000,
así que la API debe estar corriendo (paso 3).

La interfaz sigue los mockups (`docs/mockups`), primero móvil:

| Ruta | Pantalla |
|---|---|
| `/` | P1 Búsqueda |
| `/criterios` | P2 Interpretación y aclaración (permite corregir los criterios) |
| `/resultados` | P3 Resultados: recomendada, alternativas (tabla en escritorio) y ofertas con envío por confirmar |
| `/productos/{id}/historial` | P4 Historial con gráfico (Recharts) |
| `/sin-cobertura` | Producto fuera del catálogo (RF-13) |

## Pruebas

### Interfaz (Cypress)

```powershell
cd frontend
npm run dev          # en una terminal
npm run e2e          # en otra: corre las pruebas sin abrir el navegador
npm run e2e:abrir    # o ábrelas en el panel interactivo de Cypress
```

Las pruebas simulan la API con respuestas reales guardadas en `frontend/cypress/fixtures`, así
no dependen de los precios del día ni de que el backend esté encendido.

### Backend (pytest)

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

## Consultas y costo total

```powershell
# Con la API corriendo (uvicorn app.main:app --reload)
Invoke-RestMethod -Method Post -Uri http://localhost:8000/consultas -ContentType "application/json" -Body '{"texto": "freidora de aire oster que no pase de 250 mil"}'
```

Flujo de `POST /consultas`: interpreta el texto → si requiere aclaración, devuelve los criterios
sin buscar → busca el producto en el catálogo (marca igual y similitud de texto con RapidFuzz)
→ si no está, responde `sin_cobertura` y queda registrado (esas consultas son la lista para
ampliar el catálogo, RF-13) → calcula CT y CA de las ofertas vigentes y las ordena → guarda la
consulta y las recomendaciones (RF-12). `GET /productos/{id}/ofertas?prioridad=...` devuelve el
mismo ranking para un producto, por ejemplo al cambiar de criterio en P3.

Motor de costo (`app/costo/motor.py`), determinístico y sin modelo de lenguaje:

- `CT = P + E` y `CA = CT + w · D`. Se ordena por CA; en empate, menor CT, menos días y, por
  último, el id de la oferta para que el orden sea reproducible. La tienda nunca influye.
- `w = 0` para "Menor costo total". Para "Entrega más rápida" se usa `PESO_DIA_ESPERA_COP`, que
  no está fijado; mientras falte, se ordena por costo total y la respuesta lo avisa.
- Ofertas con envío desconocido (Falabella, Homecenter) van en `sin_costo_completo`: se muestran
  con su precio y el aviso de envío de la tienda, pero no se mezclan con las demás ni pueden ser
  la recomendada.

## Historial de precios

`GET /productos/{id}/historial?periodo=1M|3M|6M` (pantalla P4, RF-09 y RF-10):

- **Series:** una por tienda, con el menor precio del producto cada día (hora de Colombia),
  sin envío. Solo cuentan capturas disponibles de tiendas activas.
- **Resumen:** precio actual y mínimo del periodo por tienda.
- **Indicador "cerca de su mínimo":** para la tienda de la oferta recomendada, si el precio
  actual no supera el mínimo en más de `HISTORIAL_UMBRAL_CERCANIA` (valor inicial 5 %).
- **Sin exagerar:** si el historial empieza después del inicio del periodo (`datos_desde`), el
  mensaje dice "desde el 1 de noviembre" en lugar de "de 3 meses".

El historial crece solo: cada pasada del worker agrega capturas y nunca sobrescribe las anteriores.

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
    `claude-haiku-5-5`, elegido tras medir H2; `claude-opus-5-5` rindió igual y cuesta unas 36 veces más) y se usa con esfuerzo bajo,
    porque extraer criterios es una tarea simple.
  - `falso` (por defecto): reglas simples, sin clave de API ni costo. Sirve para desarrollar y
    probar; entiende pocas palabras (en las 50 consultas anotadas acierta 0 de 50).

### Medir H2 (exactitud de la interpretación)

```powershell
python -m app.herramientas.evaluar_interprete --detalle
python -m app.herramientas.evaluar_interprete --csv resultados_h2.csv
```

Lee `backend/evaluacion/consultas_anotadas.json` (las 50 consultas anotadas por Santiago) y
compara cada interpretación con su anotación. Convención de H2 (2 de noviembre de 2026):

- **Campos relevantes:** producto, marca, modelo, precio máximo, prioridad y si requiere
  aclaración, que son los que usan la búsqueda y la recomendación. Una consulta es correcta si
  coinciden todos.
- **Producto y modelo:** equivalentes si las palabras de uno contienen las del otro, sin
  importar mayúsculas, tildes ni plural ("monitor" = "monitor gamer"). **Marca:** el mismo texto.
- **Atributos:** no entran en H2, porque sus claves dependen de cómo redacta quien anota. Se
  reportan aparte, comparando solo sus valores. También se reporta la medida estricta (todo
  idéntico) para transparencia.

Reporta la exactitud con su intervalo de confianza del 95 % (Wilson) y los aciertos por campo.
Las reglas están en `app/interpretacion/evaluacion.py`; el formato, en
`evaluacion/consultas_ejemplo.json` (ejemplos que no cuentan para H2).

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
| 2. Interpretación PLN | 7 – 20 nov | Terminado (2 nov); H2 con Claude en la Fase 4 |
| 3. Costo total y recomendación | 14 – 27 nov | Terminado (2 nov) |
| 4. Historial de precios | 21 nov – 4 dic | Terminado (2 nov) |
| 5. Interfaz e integración | 28 nov – 11 dic | Terminado (2 nov): P1–P4, estados y 18 pruebas E2E |

El MVP de la Fase 3 está completo. Los materiales y el análisis de la Fase 4 están en
[`docs/fase4/`](docs/fase4/README.md). Queda para la Fase 4: medir H2 con Claude (necesita
`ANTHROPIC_API_KEY`), la auditoría de precios de H3, dejar el worker capturando a diario,
ampliar el catálogo, las pruebas con usuarios (H1, H4, H5) con la calibración de `w`, y elegir
el proveedor de la nube.
