# Resultados de H2: exactitud del intérprete

**Medición del 4 de noviembre de 2026**, con las 50 consultas anotadas de
`backend/evaluacion/consultas_anotadas.json` y una sola pasada por modelo. Las anotaciones no se
cambiaron para medir. El detalle de cada consulta está en `backend/evaluacion/resultados/`.

**Hipótesis:** al menos el 80 % de las consultas se interpreta correctamente.

| Medida | Claude Haiku 5.5 | Claude Opus 5.5 |
|---|---|---|
| Correctas en los campos relevantes | **41 de 50 (82 %)** | **40 de 50 (80 %)** |
| Intervalo de confianza 95 % (Wilson) | 69,2 % a 90,2 % | 67,0 % a 88,8 % |
| Meta H2 (≥ 80 %) | Se cumple | Se cumple |
| Medida estricta (todos los campos y atributos idénticos) | 10 (20 %) | 7 (14 %) |
| Atributos (solo valores; se reportan aparte) | 22 de 50 | 20 de 50 |
| Tokens por consulta (entrada / salida) | 969 / 150 | 969 / 115 |
| Costo de las 50 consultas | US$0,009 | US$0,31 |
| Costo por consulta | US$0,00017 | US$0,0062 |

Costo calculado con la fórmula de la sección 10 del documento de arquitectura y las tarifas
publicadas a octubre de 2026: Haiku US$0,10 / US$0,50 y Opus US$4 / US$20 por millón de tokens.

**Decisión (4 de noviembre de 2026):** la aplicación usa Claude Haiku 5.5.

## Cómo leerlo

- **La meta se cumple, sin margen.** El punto medio llega al 80 %, pero con 50 consultas el
  intervalo baja hasta cerca del 67 %. Es evidencia exploratoria, no una prueba definitiva.
- **Los dos modelos empatan.** Una consulta de diferencia entre 50 no es una diferencia real, y
  Haiku cuesta unas 36 veces menos.
- **Precio máximo y prioridad acertaron 50 de 50 en los dos modelos.** Son los campos que más
  afectan el costo y el orden. Marca, modelo y aclaración quedaron entre 48 y 50.
- **El punto débil es `producto`** (44 y 43 de 50). Casi todos los errores son de generalización:
  "iPhone" se interpreta como "celular" y "Lego" como "set de construcción".
- **Los atributos son la medida más baja.** Por la convención definida, no cuentan para H2, porque
  los modelos los nombran o los dividen de formas distintas. Debe decirse al presentar el 80 %.

## Reproducir

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
$env:INTERPRETE_MODELO = "claude-haiku-5-5"
python -m app.herramientas.evaluar_interprete --detalle
```

Esto consume créditos de la API.
