"""Puntaje SUS (System Usability Scale; Brooke, 1996) para la hipótesis H4.

Procedimiento estándar: 10 afirmaciones con respuestas de 1 (totalmente en desacuerdo) a 5
(totalmente de acuerdo). Las impares suman (respuesta − 1); las pares suman (5 − respuesta).
La suma (0 a 40) se multiplica por 2,5 para obtener un puntaje de 0 a 100.
"""

from statistics import mean, stdev

from scipy import stats

META_H4 = 68.0  # valor de referencia (Sauro & Lewis, 2016)


def puntaje_sus(respuestas: list[int]) -> float:
    if len(respuestas) != 10:
        raise ValueError(f"El SUS tiene 10 respuestas; llegaron {len(respuestas)}")
    if any(r not in (1, 2, 3, 4, 5) for r in respuestas):
        raise ValueError("Cada respuesta del SUS va de 1 a 5")
    suma = sum((r - 1) if numero % 2 == 1 else (5 - r) for numero, r in enumerate(respuestas, start=1))
    return suma * 2.5


def intervalo_media(valores: list[float], confianza: float = 0.95) -> tuple[float, float]:
    """Intervalo de confianza de la media con la distribución t."""
    if len(valores) < 2:
        raise ValueError("Se necesitan al menos 2 puntajes para el intervalo")
    margen = stats.t.ppf((1 + confianza) / 2, len(valores) - 1) * stdev(valores) / len(valores) ** 0.5
    return mean(valores) - margen, mean(valores) + margen
