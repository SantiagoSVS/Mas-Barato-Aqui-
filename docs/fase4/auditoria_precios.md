# Auditoría de precisión de los precios (H3)

**Meta:** al menos 95 % de los precios capturados coincide con el publicado en la tienda, sobre
al menos 100 verificaciones, muestreadas al azar y estratificadas por plataforma y categoría.

## Unidad de la muestra

La **oferta**: una publicación concreta de un producto del catálogo en una tienda, con su última
captura. El catálogo ya tiene 50 productos (5 de noviembre), con más de 100 ofertas, así que las 100
verificaciones caben en una ronda. Se harán dos en días distintos, cada una con una muestra nueva.

**Cuándo:** Santiago decidió dejar pasar más días, para que el historial tenga más capturas y
las rondas caigan en momentos distintos (fechas tentativas: 18 y 25 de noviembre). Cada ronda
sigue comparando la última captura con la página ese mismo día, para no contar como error un
precio que simplemente cambió después de capturarlo.

## Procedimiento de cada ronda

1. Correr una pasada de captura (la tarea programada o `python -m app.worker --una-vez`).
2. Generar la planilla, justo después:

   ```powershell
   cd backend
   .\.venv\Scripts\Activate.ps1
   python -m app.herramientas.auditoria_precios muestra --semilla 1
   ```

   Crea `backend/evaluacion/auditoria_h3_<fecha>.csv`. Usa una semilla distinta en cada ronda y
   anótala: con la misma semilla y los mismos datos se obtiene la misma muestra.
3. **El mismo día**, abrir cada URL en una ventana privada (sin iniciar sesión) y llenar:

   | Columna | Qué va |
   |---|---|
   | verificado_en | Fecha y hora de la verificación (2026-11-03T10:15) |
   | disponible | `si`, o `no` si la publicación ya no existe, está pausada o agotada |
   | precio_publicado_cop | Precio que muestra la página, en pesos |
   | envio_publicado_cop | Envío a Medellín antes de pagar; 0 si es gratis; vacío si la página no lo muestra |
   | observaciones | Lo que explique una diferencia (precio rebajado, otra variante, etc.) |

   En Mercado Libre, elegir Medellín como ubicación para ver el envío. La captura cotiza con la
   cuenta de desarrollador; si el envío difiere por eso, anotarlo: es justo lo que esta auditoría
   debe revelar (sección 7 del documento de arquitectura).
4. Calcular el resultado con todas las rondas:

   ```powershell
   python -m app.herramientas.auditoria_precios resultado evaluacion\auditoria_h3_20261103.csv evaluacion\auditoria_h3_20261110.csv
   ```

## Criterios (fijados antes de auditar)

- **Precio correcto:** el publicado es exactamente igual al capturado.
- **Envío correcto:** igual al capturado, o desconocido en la captura y no visible en la página.
- Las ofertas no disponibles se excluyen del porcentaje y se reportan aparte.
- **H3 se decide con el precio.** También se reportan el envío y «precio y envío» juntos, el
  desglose por tienda y el intervalo de confianza de Wilson.
- Las planillas llenas se suben al repositorio como evidencia.
