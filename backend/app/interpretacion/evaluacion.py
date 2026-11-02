"""Evaluación del intérprete contra consultas anotadas a mano (H2, RNF-02).

H2: el módulo interpreta correctamente "en todos sus campos relevantes" al menos el 80 % de
las consultas. Aquí se define qué cuenta como correcto:

- Campos evaluados: producto, marca, modelo, atributos, precio_max_cop, prioridad y
  requiere_aclaracion. La confianza no se evalúa: es una estimación del propio modelo.
- Los textos se comparan sin importar mayúsculas, tildes ni espacios ("Portátil" = "portatil",
  "128 GB" = "128gb").
- atributos: deben coincidir exactamente las claves y los valores (sin atributos de más ni de
  menos).
- precio_max_cop: el mismo número entero.
- Una consulta es correcta solo si TODOS sus campos coinciden.

El resultado se reporta con su intervalo de confianza del 95 % (método de Wilson), como pide
la metodología del proyecto.
"""

import math
import unicodedata
from dataclasses import dataclass, field

from app.interpretacion.esquema import CriteriosConsulta

CAMPOS = ("producto", "marca", "modelo", "atributos", "precio_max_cop", "prioridad", "requiere_aclaracion")


def _texto(valor: object) -> object:
    if not isinstance(valor, str):
        return valor
    sin_tildes = unicodedata.normalize("NFKD", valor.lower())
    return "".join(c for c in sin_tildes if not unicodedata.combining(c) and not c.isspace())


def _atributos(valor: dict[str, str]) -> dict[object, object]:
    return {_texto(clave): _texto(dato) for clave, dato in valor.items()}


def campos_distintos(obtenido: CriteriosConsulta, esperado: CriteriosConsulta) -> list[str]:
    """Nombres de los campos en los que la interpretación no coincide con la anotación."""
    distintos = []
    for campo in CAMPOS:
        a, b = getattr(obtenido, campo), getattr(esperado, campo)
        if campo == "atributos":
            iguales = _atributos(a) == _atributos(b)
        else:
            iguales = _texto(a) == _texto(b)
        if not iguales:
            distintos.append(campo)
    return distintos


def intervalo_wilson(aciertos: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalo de confianza de una proporción (95 % por defecto)."""
    if total == 0:
        return (0.0, 0.0)
    p = aciertos / total
    denominador = 1 + z**2 / total
    centro = (p + z**2 / (2 * total)) / denominador
    margen = z * math.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denominador
    return (max(0.0, centro - margen), min(1.0, centro + margen))


@dataclass
class ResultadoConsulta:
    id: str
    consulta: str
    campos_distintos: list[str]
    obtenido: CriteriosConsulta
    esperado: CriteriosConsulta

    @property
    def correcta(self) -> bool:
        return not self.campos_distintos


@dataclass
class Reporte:
    resultados: list[ResultadoConsulta] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.resultados)

    @property
    def correctas(self) -> int:
        return sum(r.correcta for r in self.resultados)

    @property
    def exactitud(self) -> float:
        return self.correctas / self.total if self.total else 0.0

    def aciertos_por_campo(self) -> dict[str, int]:
        return {c: sum(c not in r.campos_distintos for r in self.resultados) for c in CAMPOS}
