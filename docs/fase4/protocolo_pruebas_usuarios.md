# Protocolo de las pruebas con usuarios (H1, H4 y H5)

## Objetivo

Comparar la decisión de compra con «Mas Barato Aquí!» frente a la comparación manual entre
tiendas, en tiempo (H1) y en costo total de la opción elegida (H5), y medir la usabilidad
percibida (H4, SUS).

## Diseño

- **Intra-sujeto:** cada participante resuelve las mismas 3 tareas en las dos condiciones:
  con la aplicación y de forma manual (navegando las tiendas por su cuenta).
- **Contrabalanceo:** los participantes impares (P01, P03…) empiezan con la aplicación; los
  pares, con la comparación manual. Dentro de cada condición, el orden de las tareas rota:

  | Participante | Orden de las tareas |
  |---|---|
  | P01, P04, P07… | T1 → T2 → T3 |
  | P02, P05, P08… | T2 → T3 → T1 |
  | P03, P06, P09… | T3 → T1 → T2 |

- **Participantes:** 15 a 20 adultos que compran en línea con frecuencia en Colombia, por
  conveniencia. Resultados exploratorios, no generalizables.
- **Tiendas:** las tres del MVP (Mercado Libre, Falabella y Homecenter), en las dos condiciones,
  para que la comparación sea justa.
- **Limitación conocida:** en la segunda condición el participante ya conoce el producto y quizá
  recuerde precios. El contrabalanceo reparte ese efecto entre las dos condiciones; se reporta
  como limitación.

## Tareas

Cada tarea se entrega en una tarjeta impresa. El participante escribe la búsqueda con sus
propias palabras; no se le dicta la frase.

| Tarea | Categoría | Tarjeta |
|---|---|---|
| T1 | Tecnología | «Quieres comprar un reloj inteligente **Xiaomi Redmi Watch 6 Active**. Encuentra dónde te sale más barato en total, sumando el envío a Medellín.» |
| T2 | Hogar | «Quieres comprar una freidora de aire **Oster DiamondForce de 4 litros, manual**. Encuentra dónde te sale más barata en total, sumando el envío a Medellín.» |
| T3 | Belleza | «Quieres comprar el protector solar **ISDIN Fusion Water Magic SPF 50 de 50 ml**. Encuentra dónde te sale más barato en total, sumando el envío a Medellín.» |

Tareas de reserva (si un producto se agota o deja de estar en una tienda): audífonos Xiaomi
Redmi Buds 8 Lite (tecnología) y freidora de aire Imusa Easy Fry Max 5 litros (hogar). Si el
catálogo se amplía antes de las pruebas, las tareas se pueden cambiar, siempre que el producto
esté en al menos dos tiendas. **[PENDIENTE: confirmar las tareas el día anterior a la primera sesión.]**

## Procedimiento (por participante, unos 40 minutos)

1. **Bienvenida (3 min).** Explicar el objetivo: se evalúa la aplicación, no a la persona.
   Leer y firmar el [consentimiento informado](consentimiento_informado.md). Asignar el código.
2. **Cuestionario previo (3 min).** [Cuestionario previo](cuestionario_previo.md).
3. **Condición 1 (3 tareas).** Según el contrabalanceo.
4. **Condición 2 (3 tareas).**
5. **SUS (3 min).** [Cuestionario SUS](cuestionario_sus.md), justo después de usar la aplicación
   por última vez, sin ayuda del evaluador.
6. **Cierre (5 min).** Preguntas de la [guía de observación](guia_observacion.md).

### Cómo se mide cada tarea

- **El tiempo arranca** cuando el participante termina de leer la tarjeta y **se detiene** cuando
  dice en voz alta la opción que compraría (tienda y precio). No se compra nada.
- **Tiempo máximo por tarea:** **[PENDIENTE: definirlo con el director tras la prueba piloto]**.
  Si se agota, la tarea queda como no completada.
- **Condición con la aplicación:** el participante usa la app en el navegador; puede corregir
  los criterios, cambiar el criterio de decisión y abrir el historial. Al elegir, pulsa «Ir a la
  tienda».
- **Condición manual:** navegador en ventana privada, con las tres tiendas en pestañas vacías.
  Puede usar los buscadores de las tiendas como quiera, sin iniciar sesión. Para el envío, usar
  Medellín como destino.
- **Costo de la opción elegida (en las dos condiciones):** en la página de la tienda, el
  evaluador anota el precio y el envío que la tienda muestra **antes de pagar**, en ese momento.
  Si la tienda no muestra el envío sin iniciar el pago, la casilla de envío queda vacía (no se
  adivina). Así se compara lo que el usuario realmente pagaría, no lo que dice la app.
- El evaluador no ayuda durante las tareas. Si el participante pregunta, responde «haz lo que
  harías en tu casa». Las dudas se anotan en la guía de observación.

## Hoja de registro

Una fila por participante, tarea y condición en `backend/evaluacion/usuarios/registro_tareas.csv`
(se puede llenar en Excel y guardar como CSV UTF-8):

| Columna | Qué va | Ejemplo |
|---|---|---|
| participante | Código | P01 |
| tarea | T1, T2 o T3 | T2 |
| categoria | tecnologia, hogar o belleza | hogar |
| condicion | `app` o `manual` | app |
| orden | `app_primero` o `manual_primero` | app_primero |
| tiempo_s | Segundos del cronómetro | 95 |
| completada | `si` o `no` | si |
| tienda | Tienda elegida | Falabella |
| precio_cop | Precio en la página, en pesos | 789000 |
| envio_cop | Envío antes de pagar; 0 si es gratis; vacío si no se muestra | 0 |
| observaciones | Libre (sin datos personales) | Corrigió la marca en P2 |

Las respuestas del SUS van en `backend/evaluacion/usuarios/sus.csv`: participante y p1 a p10
(números de 1 a 5, tal como los marcó).

## Análisis

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m app.herramientas.analizar_pruebas_usuarios
```

Reglas fijadas antes de recoger datos (detalle en `backend/app/validacion/usuarios.py`):

- **H1:** se cumple si la mediana de la reducción de tiempo por par (misma tarea y participante)
  es de al menos 50 % y la diferencia es significativa (p < 0,05).
- **H5:** se cumple si en al menos el 80 % de los pares el costo total con la app es menor o igual
  al manual. Los pares en los que algún envío no era visible se excluyen y se reportan.
- **H4:** se cumple si la media del SUS es de al menos 68.
- Prueba pareada: t pareada si las diferencias pasan Shapiro-Wilk (p ≥ 0,05); si no, Wilcoxon
  de rangos con signo. Se reporta el tamaño del efecto y el intervalo de confianza.
- Pares con alguna tarea no completada: fuera de H1 y H5, y se reportan.
