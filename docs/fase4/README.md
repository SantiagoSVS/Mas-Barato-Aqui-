# Fase 4: pruebas, validación y documentación

Materiales para validar las hipótesis del proyecto. Los textos están listos para copiar a Word
o imprimir. Lo marcado **[PENDIENTE]** lo decide Santiago (o el director) antes de usarlo.

| Hipótesis | Qué se mide | Material | Análisis |
|---|---|---|---|
| H1 | Tiempo de decisión con la app vs. manual | [Protocolo](protocolo_pruebas_usuarios.md) | `python -m app.herramientas.analizar_pruebas_usuarios` |
| H2 | Exactitud del intérprete (≥ 80 %) | `backend/evaluacion/consultas_anotadas.json` | `python -m app.herramientas.evaluar_interprete` (con Claude) |
| H3 | Precios correctos (≥ 95 %) | [Auditoría de precios](auditoria_precios.md) | `python -m app.herramientas.auditoria_precios` |
| H4 | Usabilidad (SUS ≥ 68) | [Cuestionario SUS](cuestionario_sus.md) | `python -m app.herramientas.analizar_pruebas_usuarios` |
| H5 | Costo elegido con la app ≤ manual (≥ 80 % de las tareas) | [Protocolo](protocolo_pruebas_usuarios.md) | `python -m app.herramientas.analizar_pruebas_usuarios` |

Instrumentos de las pruebas con usuarios: [consentimiento informado](consentimiento_informado.md),
[cuestionario previo](cuestionario_previo.md), [protocolo con las tareas y la hoja de
registro](protocolo_pruebas_usuarios.md), [cuestionario SUS](cuestionario_sus.md) y [guía de
observación](guia_observacion.md).

## Orden de trabajo

1. **Ya:** dejar la captura programada (`scripts\programar_captura.ps1`) para que el historial crezca.
2. **Ya (sin costo):** auditoría de precios H3, en dos o más rondas en días distintos.
3. **Tras el pago de la API de Anthropic:** medir H2 con Claude y activar Claude en la app
   (`INTERPRETE_PROVEEDOR=anthropic`).
4. **Antes de las pruebas con usuarios:** revisar el catálogo para las tareas, hacer una prueba
   piloto con una persona y ajustar el protocolo si algo no se entiende.
5. **Pruebas con usuarios** (15 a 20 participantes × 3 tareas): llenar
   `backend/evaluacion/usuarios/registro_tareas.csv` y `sus.csv`, y correr el análisis.
6. Informe final: resultados frente a H1 a H5, limitaciones y viabilidad comercial.

## Lista de chequeo antes de cada sesión con un participante

- [ ] Docker, la API y la interfaz encendidas; `GET /salud` con las tres tiendas en verde.
- [ ] Captura de las últimas 12 horas (los precios de la app y de las tiendas deben ser del mismo día).
- [ ] Intérprete con Claude activo.
- [ ] Navegador en ventana privada para la parte manual (sin sesiones iniciadas en las tiendas).
- [ ] Cronómetro, hoja de registro impresa y código del participante asignado (P01, P02…).
