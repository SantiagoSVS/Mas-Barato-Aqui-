# Cuestionario de usabilidad (SUS)

Escala SUS (System Usability Scale; Brooke, 1996), en español. Se responde después de usar la
aplicación, sin ayuda del evaluador. Pedir al participante que responda rápido, con su primera
impresión, y que no deje ninguna afirmación sin marcar (si no sabe, marcar 3).

Código del participante: P__

Marca un número del **1 (totalmente en desacuerdo)** al **5 (totalmente de acuerdo)**:

| # | Afirmación | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| 1 | Creo que me gustaría usar esta aplicación con frecuencia. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 2 | Encontré la aplicación innecesariamente compleja. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 3 | Pensé que la aplicación era fácil de usar. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 4 | Creo que necesitaría la ayuda de una persona con conocimientos técnicos para usar esta aplicación. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 5 | Encontré que las distintas funciones de la aplicación estaban bien integradas. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 6 | Pensé que había demasiada inconsistencia en la aplicación. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 7 | Imagino que la mayoría de las personas aprendería a usar esta aplicación muy rápido. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 8 | Encontré la aplicación muy engorrosa de usar. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 9 | Me sentí muy seguro(a) usando la aplicación. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 10 | Necesité aprender muchas cosas antes de poder usar la aplicación. | ☐ | ☐ | ☐ | ☐ | ☐ |

## Cálculo (lo hace el script)

Impares: respuesta − 1. Pares: 5 − respuesta. La suma (0 a 40) × 2,5 = puntaje de 0 a 100.
Referencia: 68 (Sauro & Lewis, 2016). Las respuestas se pasan tal cual a
`backend/evaluacion/usuarios/sus.csv` (p1 a p10); no se invierten a mano.
