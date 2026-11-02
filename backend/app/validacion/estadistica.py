"""Estadística del plan de análisis (proyecto de grado, sección de análisis).

- Descriptivas: mediana y rango intercuartílico.
- Comparación pareada entre condiciones (app vs. manual): prueba t pareada si las diferencias
  son compatibles con una distribución normal (Shapiro-Wilk, p >= 0,05); si no, Wilcoxon de
  rangos con signo. Nivel de significancia 0,05, con tamaño del efecto.
- Proporciones con intervalo de Wilson (el mismo que se usa para H2).
"""

from dataclasses import dataclass
from statistics import mean, median, stdev

import numpy as np
from scipy import stats

from app.interpretacion.evaluacion import intervalo_wilson

ALFA = 0.05

__all__ = ["ALFA", "Comparacion", "comparar_pareadas", "intervalo_wilson", "rango_intercuartilico", "resumen"]


def rango_intercuartilico(valores: list[float]) -> tuple[float, float]:
    """Cuartiles 1 y 3 (método lineal, el mismo de Excel CUARTIL.INC)."""
    q1, q3 = np.percentile(valores, [25, 75])
    return float(q1), float(q3)


def resumen(valores: list[float]) -> dict[str, float]:
    q1, q3 = rango_intercuartilico(valores)
    return {"n": len(valores), "mediana": float(median(valores)), "q1": q1, "q3": q3}


@dataclass(frozen=True)
class Comparacion:
    prueba: str  # "t pareada" o "Wilcoxon"
    n: int
    p_normalidad: float | None  # Shapiro-Wilk sobre las diferencias
    estadistico: float
    p_valor: float
    efecto: float  # d_z (t pareada) o correlación biserial de rangos (Wilcoxon)
    nombre_efecto: str

    @property
    def significativa(self) -> bool:
        return self.p_valor < ALFA


def comparar_pareadas(a: list[float], b: list[float]) -> Comparacion:
    """Compara dos mediciones del mismo participante y tarea (a = con la app, b = manual).

    Un efecto negativo indica que `a` es menor que `b` (p. ej., la app tarda menos).
    """
    if len(a) != len(b):
        raise ValueError("Las dos condiciones deben tener el mismo número de mediciones")
    if len(a) < 3:
        raise ValueError("Se necesitan al menos 3 pares para comparar")
    diferencias = [x - y for x, y in zip(a, b, strict=True)]
    if all(d == 0 for d in diferencias):
        raise ValueError("Todas las diferencias son cero: no hay nada que comparar")

    p_normalidad = float(stats.shapiro(diferencias).pvalue)
    if p_normalidad >= ALFA:
        resultado = stats.ttest_rel(a, b)
        d_z = mean(diferencias) / stdev(diferencias)
        return Comparacion("t pareada", len(a), p_normalidad, float(resultado.statistic),
                           float(resultado.pvalue), d_z, "d de Cohen (d_z)")

    resultado = stats.wilcoxon(a, b)
    return Comparacion("Wilcoxon", len(a), p_normalidad, float(resultado.statistic),
                       float(resultado.pvalue), biserial_de_rangos(diferencias),
                       "correlación biserial de rangos")


def biserial_de_rangos(diferencias: list[float]) -> float:
    """Tamaño del efecto de Wilcoxon: (suma de rangos positivos − negativos) / suma total.

    Va de −1 (todas las diferencias negativas) a 1 (todas positivas). Se ignoran los ceros,
    igual que en la prueba.
    """
    sin_ceros = [d for d in diferencias if d != 0]
    rangos = stats.rankdata([abs(d) for d in sin_ceros])
    positivos = sum(r for r, d in zip(rangos, sin_ceros, strict=True) if d > 0)
    negativos = sum(r for r, d in zip(rangos, sin_ceros, strict=True) if d < 0)
    return float((positivos - negativos) / (positivos + negativos))
