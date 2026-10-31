# Mas Barato Aquí! — contexto del proyecto

Proyecto de grado de Santiago Velásquez (Ingeniería de Software). Este archivo resume las decisiones ya tomadas en los documentos del proyecto. Las fuentes completas están en `docs/`:

- `docs/Proyecto_de_Grado_Mas_Barato_Aqui.docx`: planteamiento, objetivos, hipótesis, metodología y cronograma.
- `docs/Documento_de_Arquitectura_de_Software_Mas_Barato_Aqui.docx`: requerimientos, arquitectura, stack, modelo de datos, fórmula y pruebas. **Si algo de este archivo choca con ese documento, manda el documento y avisa a Santiago.**
- `docs/pantallas.md` y `docs/mockups/`: diseño de las pantallas P1 a P4 (móvil y escritorio).

## Qué es

Aplicación **web responsiva** (primero móvil) que:

1. Recibe una necesidad de compra en lenguaje coloquial ("busco un celular Samsung gama media por menos de 800 mil pesos").
2. La convierte en criterios estructurados con un modelo de lenguaje.
3. Busca el producto en datos **ya capturados** de varias tiendas.
4. Recomienda la opción de **menor costo total estimado** (precio + envío, considerando el tiempo de entrega).
5. Muestra la fuente y la fecha de captura de cada dato, y redirige a la tienda original para comprar.

**Fuera del alcance del MVP:** pagos dentro de la app, apps nativas, notificaciones push, cuentas de usuario, comparación de reseñas y cargos que solo aparecen en el checkout (impuestos dinámicos, descuentos por medio de pago).

## Principios que no se negocian

- **Determinismo donde importa:** el modelo de lenguaje SOLO interpreta la consulta. El costo total, el ordenamiento y la recomendación salen de código propio, reproducible y probado. Nunca dejar que el LLM decida el orden ni calcule precios.
- **Neutralidad:** el orden depende solo del costo. Ni la afiliación, ni la publicidad, ni la prioridad de integración de una tienda cambian el orden.
- **Trazabilidad:** todo dato mostrado conserva plataforma, URL de origen y fecha y hora de captura.
- **Extracción respetuosa:** APIs oficiales primero. Scraping solo respetando robots.txt, con límite de frecuencia, identificación del agente y sin contenido detrás de autenticación.
- **Modularidad:** un conector por tienda con la misma interfaz. Agregar una tienda = escribir un conector, sin tocar las demás capas (RNF-06).
- **Ante la duda, omitir:** si el emparejamiento de dos publicaciones es dudoso, se omite la oferta o se marca con baja confianza; nunca se mezcla sin avisar.
- **Seguridad:** claves en variables de entorno (`.env`, nunca en el repositorio); validar y limitar la longitud del texto antes de enviarlo al modelo; validar la salida del modelo contra el esquema y tratarla como dato, nunca ejecutarla; límite de consultas por sesión/IP. Datos personales mínimos (Ley 1581 de 2012).

## Tiendas (7)

| Prioridad | Tiendas | Nota |
|---|---|---|
| Núcleo del MVP, se integran primero | **Amazon, Mercado Libre, Falabella** | Mínimo exigido: 3 tiendas funcionando. Si una bloquea el acceso, se reemplaza por una de las otras cuatro. |
| Después, según acceso a datos | Éxito, Alkosto, Alkomprar, Homecenter | |

**Amazon** despacha desde EE. UU.: el precio viene en dólares y se convierte a pesos con la tasa de cambio del día de la captura (guardar la tasa usada). Su envío `E` incluye el envío internacional y el depósito estimado de impuestos de importación cuando Amazon los muestra antes del pago. Amazon limita la extracción automatizada: intentar su API para afiliados.

## Fórmula de costo (sección 7 del documento de arquitectura)

```
CT = P + E          # costo total estimado
CA = CT + w · D     # costo ajustado por tiempo de entrega
```

- `P` precio del producto (COP, entero), `E` envío (0 si es gratis para ese pedido), `D` días de entrega estimados, `w` valor en pesos por día de espera.
- Se ordena por `CA`; en empate gana el menor `CT`. La interfaz muestra siempre `CT`, `D` y `CA` por separado.
- `w = 0` = perfil "Menor costo total". Un `w` mayor = perfil "Entrega más rápida" (RF-11). Los valores de `w` **no están fijados**: se calibran con las pruebas de usuarios. Dejarlos configurables, sin inventar números.
- Ejemplo de prueba del documento: A (P 789.000, E 0, D 5) y B (P 769.000, E 25.000, D 2). Con w = 0 gana A (CT 789.000 vs 794.000). Con w = 10.000 gana B (CA 814.000 vs 839.000).

## Stack (sección 4)

| Componente | Decisión |
|---|---|
| Backend | Python 3.12 + FastAPI (Pydantic para validar) |
| Extracción | APIs oficiales; Requests + BeautifulSoup; Playwright solo si la página exige JavaScript |
| Base de datos | PostgreSQL (en Docker durante el desarrollo) |
| Capturas periódicas | APScheduler dentro de un proceso worker |
| Emparejamiento | Reglas (marca, modelo, atributos) + similitud de texto con RapidFuzz; embeddings solo como apoyo |
| Interpretación de consultas | Modelo de lenguaje por API con salida JSON validada con Pydantic; si no cumple, reintentar una vez o pedir aclaración |
| Frontend | React + Vite, responsivo, primero móvil |
| Gráficos | Recharts |
| Pruebas | pytest (unitarias e integración), Cypress (E2E de interfaz y API) |
| Despliegue | Docker; nube de bajo costo (proveedor por definir) |
| Versiones | Git + GitHub, ramas por incremento |

**Pendiente:** el proveedor del modelo de lenguaje y de la nube aún no se ha elegido. Implementar la interpretación detrás de una interfaz con un proveedor falso (*fake*) que responda con reglas simples, para que todo funcione y se pueda probar sin clave de API. El proveedor real se conecta después, por configuración.

Esquema de salida del intérprete:

```json
{
  "producto": "celular",
  "marca": "Samsung",
  "modelo": null,
  "atributos": {"gama": "media"},
  "precio_max_cop": 800000,
  "prioridad": "costo_total",
  "confianza": 0.0,
  "requiere_aclaracion": false
}
```

## Arquitectura (5 capas)

Interfaz web → API (FastAPI) → módulos (Historial · Costo total · Interpretación PLN) → base de datos PostgreSQL ← worker de captura programada (conectores por plataforma + normalización y emparejamiento). Servicios externos: usuario (navegador), modelo de lenguaje (API) y tiendas (API o extracción).

- La interfaz solo habla con la API. Solo el worker toca las tiendas. Las consultas del usuario se responden sobre datos ya almacenados, en segundos (RNF-04); **nunca** se hace scraping en el momento de la consulta.
- Producto fuera del catálogo → se informa al usuario, se registra como «sin cobertura» y se pone en cola para la siguiente captura (RF-13).
- Si una tienda falla, se registra el error y se responde con las demás (RNF-05).

## Modelo de datos (sección 6)

| Entidad | Atributos principales |
|---|---|
| Plataforma | id, nombre, tipo de acceso (API o extracción), url base, moneda, activa |
| Producto | id, nombre canónico, marca, modelo, categoría, atributos clave |
| Oferta | id, plataforma_id, producto_id, título original, url de origen, vendedor |
| Captura | id, oferta_id, fecha y hora, precio (COP), costo de envío (COP), días de entrega estimados, disponibilidad. **Nunca se sobrescribe**: cada fila es un punto del historial. Para Amazon, guardar también precio original en USD y tasa de cambio. |
| Consulta | id, texto original, criterios interpretados (JSON), confianza, fecha, tiempo de respuesta, tokens consumidos, cobertura (sí/no) |
| Recomendación | id, consulta_id, oferta_id, posición, costo total, componentes del cálculo |

Índices: `oferta_id + fecha` y `producto_id`. Sin datos personales de usuarios en el MVP.

## API inicial (nombres ajustables)

| Endpoint | Función |
|---|---|
| `POST /consultas` | Recibe el texto; devuelve criterios interpretados y recomendación |
| `GET /productos/{id}/ofertas` | Ofertas actuales por plataforma con costo total |
| `GET /productos/{id}/historial` | Serie de precios por plataforma |
| `GET /salud` | Estado del servicio y de la última captura por plataforma |

## Requerimientos

Funcionales (M = debe, S = debería). Construir primero todos los M.

- **M:** RF-01 consulta en texto libre · RF-02 criterios estructurados · RF-03 captura periódica de precio, envío, entrega y disponibilidad (Amazon, Mercado Libre y Falabella primero) · RF-04 normalización (moneda, unidades, variantes; USD→COP para Amazon) · RF-05 emparejar publicaciones del mismo producto · RF-06 calcular costo total y ordenar · RF-07 mostrar recomendación con explicación, fuente y fecha · RF-08 redirigir a la publicación original (centralizar en una sola función, para añadir afiliación después sin tocar el orden).
- **S:** RF-09 historial con gráfico · RF-10 indicar si el precio está cerca del mínimo histórico · RF-11 elegir criterio (menor costo / entrega más rápida) · RF-12 registrar métricas de uso y errores · RF-13 manejo de productos sin cobertura.

No funcionales (ISO/IEC 25010): RNF-01 ≥ 95 % de precios correctos (H3) · RNF-02 ≥ 80 % de consultas bien interpretadas (H2) · RNF-03 SUS ≥ 68 (H4) · RNF-04 respuesta en segundos · RNF-05 una tienda caída no tumba el sistema · RNF-06 una tienda = un conector · RNF-07 seguridad y Ley 1581 · RNF-08 navegadores modernos de móvil y escritorio.

Hipótesis que el sistema debe permitir medir: H1 tiempo de decisión ≥ 50 % menor que la comparación manual · H2 PLN ≥ 80 % · H3 precios ≥ 95 % · H4 SUS ≥ 68 · H5 en ≥ 80 % de las tareas el costo elegido con la app es ≤ al manual.

## Plan de desarrollo (Fase 3: 31 oct – 11 dic 2026)

| Incremento | Fechas | Entregable |
|---|---|---|
| 0. Base del proyecto | 31 oct – 2 nov | Monorepo, Docker Compose con PostgreSQL, migraciones del modelo de datos, `GET /salud`, frontend Vite vacío con la paleta |
| 1. Extracción de datos | 31 oct – 13 nov | Conectores Amazon, Mercado Libre y Falabella; worker con APScheduler; normalización; registro de errores |
| 2. Interpretación PLN | 7 – 20 nov | Intérprete con esquema validado + proveedor falso; conjunto de 50 consultas anotadas y script de evaluación (H2) |
| 3. Costo total y recomendación | 14 – 27 nov | Emparejamiento, motor CT/CA determinístico con pruebas, `POST /consultas` |
| 4. Historial de precios | 21 nov – 4 dic | Serie por oferta, mínimo histórico, `GET /productos/{id}/historial` |
| 5. Interfaz e integración | 28 nov – 11 dic | Pantallas P1–P4 según mockups; E2E con Cypress; MVP completo (entrega 3: 11 dic) |

Cada incremento cierra con código y pruebas en el repositorio (evidencia para la Entrega 2: el profesor pidió repositorio, capturas y comparar cronograma real vs planeado).

## Diseño de la interfaz

- Paleta: azul principal `#0B2D6B`, azul secundario `#2563EB`, amarillo acento `#F59E0B`, gris neutro `#E5E7EB`; fondo `#F4F7FC`; texto secundario `#4B5B7A`.
- Tipografía: Plus Jakarta Sans (Google Fonts).
- Textos de la interfaz en español de Colombia; precios en formato `$789.000`.
- Detalle de cada pantalla en `docs/pantallas.md`.

## Ambiente y forma de trabajo

- Equipo de Santiago: **Windows**, VS Code, Git, Python 3.12, Node.js LTS y Docker Desktop (WSL 2). Dar comandos para PowerShell.
- Estructura sugerida: `backend/` (FastAPI, worker, conectores, pruebas pytest), `frontend/` (React + Vite), `e2e/` o `frontend/cypress/`, `docker-compose.yml`, `.env.example`, `README.md` con los comandos para arrancar.
- Nombres del dominio en español, como en los documentos (`consultas`, `ofertas`, `captura`).
- Santiago trabaja en QA y automatización con Cypress: aprovechar eso en las pruebas.
- **Es su proyecto de grado y lo va a sustentar.** Al cerrar cada incremento, explicar qué se hizo, por qué y cómo probarlo. Preferir código claro sobre código ingenioso.
- Commits pequeños y descriptivos, una rama por incremento. Nunca subir `.env` ni claves.
- No inventar datos (precios, valores de `w`, cifras de costos): si falta un dato, dejarlo configurable o marcado como pendiente.
