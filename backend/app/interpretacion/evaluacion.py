"""Evaluación del intérprete contra consultas anotadas a mano (H2, RNF-02).

H2: el módulo interpreta correctamente "en todos sus campos relevantes" al menos el 80 % de
las consultas. Convención adoptada el 2 de noviembre de 2026:

Campos relevantes = los que usa la búsqueda y la recomendación:
  producto, marca, modelo, precio_max_cop, prioridad y requiere_aclaracion.

- producto y modelo: equivalentes si las palabras de uno contienen las del otro, sin importar
  mayúsculas, tildes ni plural ("monitor gamer" = "monitor"; "15 Pro Max" = "iPhone 15 Pro Max";
  "audífono" = "audífonos"). Así no se castiga que el modelo diga lo mismo con más o menos
  palabras.
- marca: el mismo texto, sin importar mayúsculas ni tildes ("IMUSA" = "Imusa").
- precio_max_cop, prioridad y requiere_aclaracion: exactamente iguales.

Los atributos no entran en H2: sus claves dependen de cómo redacta quien anota ("tipo",
"conectividad"...) y no los usa el cálculo del costo. Se reportan aparte, comparando solo sus
valores. También se reporta la medida estricta (todos los campos idénticos, incluidos los
atributos con sus claves) para que se vea la diferencia.

El resultado se reporta con su intervalo de confianza del 95 % (método de Wilson), como pide
la metodología del proyecto.
"""

import math
import re
import unicodedata
from dataclasses import dataclass, field

from app.interpretacion.esquema import CriteriosConsulta

CAMPOS_H2 = ("producto", "marca", "modelo", "precio_max_cop", "prioridad", "requiere_aclaracion")
CAMPOS = (*CAMPOS_H2, "atributos")


def _normalizar(valor: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", valor.lower())
    return "".join(c for c in sin_tildes if not unicodedata.combining(c))


def _texto(valor: object) -> object:
    """Texto sin mayúsculas, tildes ni espacios; otros tipos quedan igual."""
    if not isinstance(valor, str):
        return valor
    return "".join(c for c in _normalizar(valor) if not c.isspace())


def _palabras(valor: str) -> set[str]:
    """Palabras normalizadas y en singular simple ("audífonos" -> "audifono")."""
    palabras = re.findall(r"[a-z0-9]+", _normalizar(valor))
    return {p[:-1] if len(p) > 3 and p.endswith("s") else p for p in palabras}


def _contenido(a: str | None, b: str | None) -> bool:
    if a is None or b is None:
        return a is None and b is None
    pa, pb = _palabras(a), _palabras(b)
    return bool(pa and pb) and (pa <= pb or pb <= pa)


def _valores_atributos(atributos: dict[str, str]) -> set[object]:
    return {_texto(v) for v in atributos.values()}


def campos_distintos(obtenido: CriteriosConsulta, esperado: CriteriosConsulta) -> list[str]:
    """Campos relevantes para H2 en los que la interpretación no coincide con la anotación."""
    distintos = []
    for campo in CAMPOS_H2:
        a, b = getattr(obtenido, campo), getattr(esperado, campo)
        iguales = _contenido(a, b) if campo in ("producto", "modelo") else _texto(a) == _texto(b)
        if not iguales:
            distintos.append(campo)
    return distintos


def atributos_coinciden(obtenido: CriteriosConsulta, esperado: CriteriosConsulta) -> bool:
    """Compara solo los valores de los atributos, sin sus claves."""
    return _valores_atributos(obtenido.atributos) == _valores_atributos(esperado.atributos)


def identicos(obtenido: CriteriosConsulta, esperado: CriteriosConsulta) -> bool:
    """Medida estricta: todos los campos iguales, incluidos los atributos con sus claves."""
    claves = lambda d: {_texto(k): _texto(v) for k, v in d.items()}  # noqa: E731
    return all(_texto(getattr(obtenido, c)) == _texto(getattr(esperado, c)) for c in CAMPOS_H2) and claves(
        obtenido.atributos
    ) == claves(esperado.atributos)


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
    obtenido: CriteriosConsulta
    esperado: CriteriosConsulta
    campos_distintos: list[str] = field(init=False)
    atributos_coinciden: bool = field(init=False)
    identica: bool = field(init=False)

    def __post_init__(self) -> None:
        self.campos_distintos = campos_distintos(self.obtenido, self.esperado)
        self.atributos_coinciden = atributos_coinciden(self.obtenido, self.esperado)
        self.identica = identicos(self.obtenido, self.esperado)

    @property
    def correcta(self) -> bool:
        """Correcta para H2: todos los campos relevantes coinciden."""
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
    def identicas(self) -> int:
        return sum(r.identica for r in self.resultados)

    @property
    def exactitud(self) -> float:
        return self.correctas / self.total if self.total else 0.0

    def aciertos_por_campo(self) -> dict[str, int]:
        aciertos = {c: sum(c not in r.campos_distintos for r in self.resultados) for c in CAMPOS_H2}
        aciertos["atributos (solo valores)"] = sum(r.atributos_coinciden for r in self.resultados)
        return aciertos
