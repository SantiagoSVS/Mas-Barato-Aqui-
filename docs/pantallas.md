# Pantallas del MVP (P1 a P4)

Diseño mobile-first y responsivo. Los mockups de referencia están en `docs/mockups/` como archivos HTML: sirven para leer la estructura, los textos y los estilos (colores, tamaños, espaciados), no para abrirlos tal cual (dependen de un script del editor de diseño que no está incluido). Los precios de los mockups son datos de ejemplo.

| Archivo | Pantalla |
|---|---|
| `movil-P1-busqueda.html` / `escritorio-P1-busqueda.html` | P1 Búsqueda |
| `movil-P2-interpretacion.html` / `escritorio-P2-interpretacion.html` | P2 Interpretación y aclaración |
| `movil-P3-resultados.html` / `escritorio-P3-resultados.html` | P3 Resultados |
| `movil-P4-historial.html` / `escritorio-P4-historial.html` | P4 Historial del producto |
| `movil-estados.html` | Estados: carga, sin cobertura, tienda sin respuesta, emparejamiento dudoso |

## Flujo

1. El usuario escribe lo que busca (P1).
2. El sistema muestra cómo interpretó la consulta y pregunta si falta algo (P2).
3. Ve la recomendada y las alternativas ordenadas por costo (P3).
4. Abre el historial si quiere saber si es buen momento para comprar (P4).
5. Pulsa "Ir a la tienda" y termina la compra en la tienda original.

## P1 · Búsqueda (RF-01)

- Encabezado con el logo (carrito azul) y "Mas Barato **Aquí!**".
- Título "¿Qué quieres comprar?" y subtítulo "Escríbelo con tus palabras. Te mostramos dónde sale más barato, sumando el envío."
- Caja de texto (máx. 300 caracteres, contador visible) y botón "Buscar".
- Ejemplos de búsqueda que rellenan la caja al pulsarlos.
- Bloque "Así funciona" en 3 pasos: describe, confirma, compra.
- Lista de tiendas: Amazon, Mercado Libre y Falabella destacadas; luego Éxito, Alkosto, Alkomprar y Homecenter. "No necesitas cuenta."
- Estado de carga mientras se interpreta la consulta.
- Escritorio: dos columnas (búsqueda a la izquierda; "Así funciona" y tiendas a la derecha) + pie de página.

## P2 · Interpretación y aclaración (RF-02)

- Muestra la consulta original entre comillas.
- Lista de criterios interpretados, cada uno con botón "Editar": Producto, Marca, Atributos, Precio máximo, Prioridad.
- Si `requiere_aclaracion` es verdadero o la confianza es baja: tarjeta amarilla "Una pregunta para afinar" con opciones en botones (ej.: "¿Qué almacenamiento necesitas? 128 GB / 256 GB / Me da igual").
- Botón principal "Ver resultados"; enlace "Escribir otra búsqueda".
- Escritorio: indicador de pasos en el encabezado (Búsqueda → Confirmar criterios → Resultados).

## P3 · Resultados (RF-06, RF-07, RF-08, RF-11)

- Resumen de la búsqueda y "7 tiendas consultadas · N con resultados".
- Selector de criterio: "Menor costo total" (w = 0) / "Entrega más rápida" (w > 0). Con w > 0 se muestra también el costo ajustado (CA).
- Tarjeta "Recomendada · menor costo total" (borde y franja amarilla): producto, tienda, costo total grande, desglose Precio / Envío / Entrega, frase "Por qué es la recomendada" (ej.: "es $5.000 más barata que la siguiente opción al sumar el envío"), fuente y fecha de captura, botones "Ir a la tienda" y "Ver historial".
- Alternativas ordenadas por costo, cada una con tienda, precio + envío, días, costo total y fecha de captura. Amazon lleva la etiqueta "desde EE. UU." y su envío dice "envío e imp.".
- Si el costo total supera el presupuesto: aviso "supera tu presupuesto con envío".
- Tiendas sin el producto: "Homecenter no tiene este producto".
- Aviso fijo: "Costo estimado: no incluye impuestos, descuentos por medio de pago ni promociones que la tienda aplica al pagar."
- Escritorio: la recomendada ocupa todo el ancho; las alternativas van en una tabla (Tienda, Precio, Envío, Entrega, Costo total, Capturado, Ir a la tienda) con scroll horizontal en pantallas pequeñas.

Datos de ejemplo usados en los mockups (consulta "celular Samsung gama media por menos de 800 mil"):

| # | Tienda | Precio | Envío | Días | CT |
|---|---|---|---|---|---|
| 1 | Mercado Libre | 789.000 | 0 | 5 | 789.000 |
| 2 | Falabella | 769.000 | 25.000 | 2 | 794.000 |
| 3 | Amazon (EE. UU.) | 735.000 | 62.000 (envío + imp.) | 9 | 797.000 |
| 4 | Alkosto | 799.000 | 0 | 3 | 799.000 |
| 5 | Éxito | 799.900 | 0 | 3 | 799.900 |
| 6 | Alkomprar | 789.900 | 15.000 | 4 | 804.900 |
| — | Homecenter | sin el producto | | | |

## P4 · Historial del producto (RF-09, RF-10)

- Indicador verde "Cerca de su mínimo histórico" con el detalle (ej.: "En Mercado Libre está a $10.000 del mínimo de 3 meses").
- Selector de periodo 1M / 3M / 6M.
- Gráfico de líneas (Recharts), una línea por tienda: por defecto Mercado Libre, Falabella y Amazon; botón para añadir las demás. Línea punteada con el mínimo histórico de la tienda recomendada. Las líneas se distinguen también por estilo (sólida/punteada), no solo por color.
- Tabla: precio actual y mínimo de 3 meses por tienda.
- Nota: "Precio del producto sin envío. Amazon convertido de dólares a pesos con la tasa del día de cada captura." + fecha de la última captura.
- Botón "Ir a la tienda recomendada".

## Estados (móvil, aplican igual en escritorio)

- **Cargando:** "Entendiendo tu búsqueda…" con esqueleto.
- **Sin cobertura (RF-13):** "Aún no tenemos este producto… Lo agregamos a la lista para la próxima actualización de precios." + botón "Probar otra búsqueda".
- **Tienda sin respuesta (RNF-05):** aviso amarillo "Éxito no respondió en la última actualización. Comparamos con las demás…".
- **Emparejamiento dudoso:** "Ocultamos N ofertas porque no estamos seguros de que sean el mismo producto."

## Pie de página (escritorio)

Fondo azul oscuro. Marca + "Compara · Encuentra · Ahorra" + frase de neutralidad; columnas Producto (Buscar, Cómo funciona, Tiendas, Preguntas frecuentes), Legal (Términos y condiciones, Política de privacidad, Tratamiento de datos — Ley 1581 de 2012, Cómo calculamos los precios), Síguenos (Instagram, TikTok, LinkedIn) y Contacto ([CORREO DE CONTACTO], pendiente). Línea final: "© 2026 Mas Barato Aquí! · Medellín, Colombia" y el aviso de costos estimados.

## Accesibilidad

Botones y enlaces reales (no `div` con clic), objetivos táctiles de al menos 44 px, `aria-label` en botones de solo ícono, contraste de texto mínimo 4.5:1.
